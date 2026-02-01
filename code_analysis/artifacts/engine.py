"""Derived artifact analysis execution."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

from ...runtime import config as runtime_config
from ...runtime.logging import get_logger
from ..core import routing
from ..tools import git_support, snapshots, walker
from ..tools.call_extraction import CallExtractionRecord

logger = get_logger(__name__)


class ArtifactEngine:
    """Analyze derived artifacts without mutating core structures."""

    def __init__(
        self,
        workspace_root: Path,
        conn,
        languages: Optional[Dict[str, runtime_config.LanguageSettings]] = None,
        discovery: Optional[runtime_config.DiscoverySettings] = None,
        config_root: Optional[Path] = None,
        progress_factory=None,
    ) -> None:
        self.workspace_root = workspace_root
        self.repo_root = workspace_root
        self.config_root = config_root or workspace_root
        self.conn = conn
        self.languages = languages or runtime_config.load_language_settings(workspace_root)
        self.discovery = discovery
        self.analyzers = routing.select_analyzers(self.languages)
        self._progress_factory = progress_factory

    def run(self, snapshot_id: str) -> List[CallExtractionRecord]:
        tracked = git_support.tracked_paths(self.workspace_root)
        if self.discovery is None:
            self.discovery = runtime_config.load_discovery_settings(self.config_root)
        records = walker.collect_files(
            self.workspace_root,
            self.languages,
            discovery=self.discovery,
            tracked_paths=tracked,
        )
        if not records:
            return []
        def _warn_line_count(path: Path, exc: Exception) -> None:
            logger.warning("Could not count lines in %s: %s", path, exc)
            typer.secho(f"Warning: Could not count lines in {path}: {exc}", fg=typer.colors.YELLOW)

        file_snapshots = snapshots.prepare_file_snapshots(
            self.repo_root,
            records,
            on_error=_warn_line_count,
        )
        node_map = _load_node_map(self.conn, snapshot_id)
        progress = None
        if self._progress_factory:
            progress = self._progress_factory("Analyzing artifacts", len(file_snapshots))
        call_artifacts: List[CallExtractionRecord] = []
        all_call_records = []
        try:
            for file_snapshot in file_snapshots:
                analyzer = routing.resolve_analyzer(file_snapshot, self.analyzers)
                if not analyzer:
                    if progress:
                        progress.advance(1)
                    continue
                module_name = analyzer.module_name(self.workspace_root, file_snapshot)
                try:
                    analysis = analyzer.analyze(file_snapshot, module_name)
                except Exception as exc:
                    warning = (
                        f"Failed to analyze {file_snapshot.record.relative_path}: {exc}"
                    )
                    logger.warning(
                        "Failed to analyze %s: %s",
                        file_snapshot.record.relative_path,
                        exc,
                    )
                    typer.secho(warning, fg=typer.colors.YELLOW)
                    if progress:
                        progress.advance(1)
                    continue
                all_call_records.extend(
                    record for record in analysis.call_records if record.callee_identifiers
                )
                if progress:
                    progress.advance(1)
        finally:
            if progress:
                progress.close()
        for record in all_call_records:
            node_info = node_map.get((record.qualified_name, record.node_type))
            if not node_info:
                continue
            call_artifacts.append(
                CallExtractionRecord(
                    caller_structural_id=node_info,
                    caller_qualified_name=record.qualified_name,
                    caller_node_type=record.node_type,
                    callee_identifiers=tuple(dict.fromkeys(record.callee_identifiers)),
                )
            )
        return call_artifacts


def _load_node_map(conn, snapshot_id: str) -> Dict[Tuple[str, str], str]:
    rows = conn.execute(
        """
        SELECT ni.qualified_name, sn.node_type, sn.structural_id
        FROM node_instances ni
        JOIN structural_nodes sn ON sn.structural_id = ni.structural_id
        WHERE ni.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    mapping: Dict[Tuple[str, str], Optional[str]] = {}
    for row in rows:
        key = (row["qualified_name"], row["node_type"])
        structural_id = row["structural_id"]
        if key in mapping and mapping[key] != structural_id:
            mapping[key] = None
        else:
            mapping[key] = structural_id
    return {key: structural_id for key, structural_id in mapping.items() if structural_id}
