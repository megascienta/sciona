# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Core structural analysis + ingestion orchestration for SCIONA builds."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ...runtime import config as runtime_config
from ...runtime import git as git_ops
from ...runtime.errors import IngestionError
from ...runtime.logging import get_logger
from .routing import resolve_analyzer, select_analyzers, should_register_module
from .module_naming import module_name_from_path
from ..tools import snapshots, walker
from ..tools.discovery import compute_discovery_details
from .normalize.model import FileRecord, FileSnapshot
from .structural_assembler import StructuralAssembler
from .snapshot import Snapshot

logger = get_logger(__name__)


class BuildEngine:
    """Sequence ingest phases without interpreting structure or policy."""

    def __init__(
        self,
        workspace_root: Path,
        conn,
        store,
        languages: Optional[Dict[str, runtime_config.LanguageSettings]] = None,
        discovery: Optional[runtime_config.DiscoverySettings] = None,
        config_root: Optional[Path] = None,
        progress_factory=None,
        warning_sink: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.workspace_root = workspace_root
        # Keep legacy attribute name for helpers that still reference repo_root.
        self.repo_root = workspace_root
        self.config_root = config_root or workspace_root
        self.conn = conn
        self.languages = languages or runtime_config.load_language_settings(
            workspace_root
        )
        self.discovery = discovery
        self.discovery_counts: dict[str, int] = {}
        self.discovery_candidates: dict[str, int] = {}
        self.discovery_excluded_by_glob: dict[str, int] = {}
        self.discovery_excluded_total = 0
        self.exclude_globs: list[str] = []
        self.parse_failures = 0
        self.warnings: list[str] = []
        self.analyzers = select_analyzers(self.languages)
        self.assembler = StructuralAssembler(conn, store)
        self.call_gate_diagnostics = self.assembler.call_gate_diagnostics
        self._progress_factory = progress_factory
        self._warning_sink = warning_sink

    def run(self, snapshot: Snapshot) -> Tuple[int, int]:
        if not self.conn.in_transaction:
            raise IngestionError("BuildEngine requires an active transaction.")
        savepoint = "ingest_build"
        self.conn.execute(f"SAVEPOINT {savepoint}")
        try:
            tracked = git_ops.tracked_paths(self.workspace_root)
            ignored = git_ops.ignored_tracked_paths(self.workspace_root)
            if self.discovery is None:
                self.discovery = runtime_config.load_discovery_settings(
                    self.config_root
                )
            self.exclude_globs = list(self.discovery.exclude_globs)
            enabled_languages = [
                name for name, settings in self.languages.items() if settings.enabled
            ]
            if not enabled_languages:
                raise IngestionError("No enabled languages for discovery.")
            records = walker.collect_files(
                self.workspace_root,
                self.languages,
                discovery=self.discovery,
                tracked_paths=tracked,
                ignored_paths=ignored,
            )
            candidate_counts, discovered_counts, excluded_by_glob, excluded_total = (
                compute_discovery_details(
                    tracked,
                    enabled_languages,
                    records,
                    self.exclude_globs,
                    ignored_paths=ignored,
                )
            )
            self.discovery_candidates = candidate_counts
            self.discovery_counts = discovered_counts
            self.discovery_excluded_by_glob = excluded_by_glob
            self.discovery_excluded_total = excluded_total
            self._warn_on_empty_language_matches(candidate_counts, discovered_counts)
            if not records:
                self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
                return 0, 0

            snapshot_id = snapshot.snapshot_id
            self.assembler.prime_structural_cache(None)

            def _warn_line_count(path: Path, exc: Exception) -> None:
                self._warn(f"Could not count lines in {path}: {exc}")

            changed_snapshots = snapshots.prepare_file_snapshots(
                self.repo_root,
                records,
                on_error=_warn_line_count,
            )

            inserted_nodes = 0
            processed_files = 0
            if changed_snapshots:
                inserted_nodes += self._register_modules(snapshot_id, changed_snapshots)
            module_index: set[str] = set()
            if changed_snapshots:
                for file_snapshot in changed_snapshots:
                    analyzer = resolve_analyzer(file_snapshot, self.analyzers)
                    if not analyzer:
                        continue
                    module_index.add(
                        analyzer.module_name(self.workspace_root, file_snapshot)
                    )
            progress = None
            if changed_snapshots and self._progress_factory:
                progress = self._progress_factory("Analyzing", len(changed_snapshots))
            try:
                for file_snapshot in changed_snapshots:
                    analyzer = resolve_analyzer(file_snapshot, self.analyzers)
                    if not analyzer:
                        if progress:
                            progress.advance(1)
                        continue
                    analyzer.module_index = module_index
                    module_name = analyzer.module_name(
                        self.workspace_root, file_snapshot
                    )
                    try:
                        analysis = analyzer.analyze(file_snapshot, module_name)
                    except Exception as exc:
                        warning = f"Failed to analyze {file_snapshot.record.relative_path}: {exc}"
                        self._warn(warning)
                        self.parse_failures += 1
                        self.assembler.register_module_node(
                            snapshot_id,
                            file_snapshot,
                            module_name,
                            metadata={"status": "partial_parse", "error": str(exc)},
                        )
                        if progress:
                            progress.advance(1)
                        continue
                    node_count, node_id_map = self.assembler.persist_analysis(
                        snapshot_id, analysis, file_snapshot
                    )
                    inserted_nodes += node_count
                    processed_files += 1
                    if progress:
                        progress.advance(1)
            finally:
                if progress:
                    progress.close()

            self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            return processed_files, inserted_nodes
        except Exception as exc:
            self.conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
            self.conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            raise IngestionError(f"Ingest failed: {exc}") from exc

    def _warn_on_empty_language_matches(
        self,
        candidate_counts: dict[str, int],
        discovered_counts: dict[str, int],
    ) -> None:
        missing = [
            (language, candidate_count)
            for language, candidate_count in candidate_counts.items()
            if candidate_count > 0 and discovered_counts.get(language, 0) == 0
        ]
        if not missing:
            return
        self._warn(
            "Discovery warning: enabled languages with tracked files but zero discovered:"
        )
        for language, candidate_count in missing:
            self._warn(
                f"{language}: {candidate_count} tracked by extension, 0 discovered "
                "(check discovery.exclude_globs)"
            )

    def _warn(self, message: str) -> None:
        self.warnings.append(message)
        logger.warning(message)
        if self._warning_sink:
            self._warning_sink(message)

    def _register_modules(self, snapshot_id: str, snapshots: List[FileSnapshot]) -> int:
        inserted = 0
        module_names: set[str] = set()
        module_snapshots: List[Tuple[FileSnapshot, str]] = []
        for file_snapshot in snapshots:
            analyzer = resolve_analyzer(file_snapshot, self.analyzers)
            if not should_register_module(file_snapshot, analyzer):
                continue
            module_name = analyzer.module_name(self.workspace_root, file_snapshot)
            module_names.add(module_name)
            module_snapshots.append((file_snapshot, module_name))
        for file_snapshot, module_name in module_snapshots:
            inserted += self.assembler.register_module_node(
                snapshot_id, file_snapshot, module_name
            )
        inserted += self._register_entry_point_modules(
            snapshot_id, snapshots, module_names
        )
        return inserted

    def _register_entry_point_modules(
        self,
        snapshot_id: str,
        snapshots: List[FileSnapshot],
        existing_modules: set[str],
    ) -> int:
        directories: set[Path] = set()
        for file_snapshot in snapshots:
            for parent in file_snapshot.record.relative_path.parents:
                if parent == Path("."):
                    break
                directories.add(parent)
        inserted = 0
        for directory in sorted(directories):
            module_name = module_name_from_path(
                self.workspace_root,
                directory,
                strip_suffix=False,
                treat_init_as_package=False,
            )
            if module_name in existing_modules:
                continue
            record = FileRecord(
                path=self.workspace_root / directory,
                relative_path=directory,
                language="synthetic",
            )
            snapshot = FileSnapshot(
                record=record,
                file_id="",
                blob_sha="",
                size=0,
                line_count=1,
                content=b"",
            )
            inserted += self.assembler.register_synthetic_module_node(
                snapshot_id,
                snapshot,
                module_name,
                node_type="entry_point",
            )
        return inserted
