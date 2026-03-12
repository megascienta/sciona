# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Dmitry Chigrin & MegaScienta

"""Derived artifact analysis execution."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from ...runtime import config as runtime_config
from ...runtime import git as git_ops
from ...runtime.logging import get_logger
from ..core import routing
from ...data_storage.core_db import read_ops as core_read
from ..tools.workspace import snapshots, walker
from ..tools.call_extraction import CallExtractionRecord, normalize_call_identifiers

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
        warning_sink: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.workspace_root = workspace_root
        self.repo_root = workspace_root
        self.config_root = config_root or workspace_root
        self.conn = conn
        self.languages = languages or runtime_config.load_language_settings(
            workspace_root
        )
        self.discovery = discovery
        self.analyzers = routing.select_analyzers(self.languages)
        self._progress_factory = progress_factory
        self._warning_sink = warning_sink
        self.warnings: list[str] = []
        self.diagnostics: dict[str, object] = {}

    def run(self, snapshot_id: str) -> List[CallExtractionRecord]:
        self.diagnostics = {
            "artifact_analyzer_failures": 0,
            "artifact_call_records_seen": 0,
            "artifact_call_records_dropped_missing_caller": 0,
        }
        tracked = git_ops.tracked_paths(self.workspace_root)
        ignored = git_ops.ignored_tracked_paths(self.workspace_root)
        if self.discovery is None:
            self.discovery = runtime_config.load_discovery_settings(self.config_root)
        enabled_languages = [
            name for name, settings in self.languages.items() if settings.enabled
        ]
        if not enabled_languages:
            return []
        records = walker.collect_files(
            self.workspace_root,
            self.languages,
            discovery=self.discovery,
            tracked_paths=tracked,
            ignored_paths=ignored,
        )
        if not records:
            return []

        def _warn_line_count(path: Path, exc: Exception) -> None:
            self._warn(f"Could not count lines in {path}: {exc}")

        file_snapshots = snapshots.prepare_file_snapshots(
            self.repo_root,
            records,
            on_error=_warn_line_count,
        )
        node_map = _load_node_map(self.conn, snapshot_id)
        module_index = _load_module_index(self.conn, snapshot_id)
        progress = None
        if self._progress_factory:
            progress = self._progress_factory(
                "Deriving call artifacts", len(file_snapshots)
            )
        call_artifacts: List[CallExtractionRecord] = []
        all_call_records: list[tuple[str, object]] = []
        try:
            for file_snapshot in file_snapshots:
                analyzer = routing.resolve_analyzer(file_snapshot, self.analyzers)
                if not analyzer:
                    if progress:
                        progress.advance(1)
                    continue
                analyzer.module_index = module_index
                module_name = analyzer.module_name(self.workspace_root, file_snapshot)
                try:
                    analysis = analyzer.analyze(file_snapshot, module_name)
                except Exception as exc:
                    warning = (
                        f"Failed to analyze {file_snapshot.record.relative_path}: {exc}"
                    )
                    self.diagnostics["artifact_analyzer_failures"] = (
                        int(self.diagnostics["artifact_analyzer_failures"]) + 1
                    )
                    self._warn(warning)
                    if progress:
                        progress.advance(1)
                    continue
                all_call_records.extend(
                    (file_snapshot.record.language, record)
                    for record in analysis.call_records
                    if record.callee_identifiers
                )
                if progress:
                    progress.advance(1)
        finally:
            if progress:
                progress.close()
        normalized_calls = normalize_call_identifiers(
            [
                (
                    language,
                    record.qualified_name,
                    record.node_type,
                    list(record.callee_identifiers),
                )
                for language, record in all_call_records
            ]
        )
        merged_by_caller: OrderedDict[str, dict[str, object]] = OrderedDict()
        for _language, qualified_name, node_type, callee_identifiers in normalized_calls:
            self.diagnostics["artifact_call_records_seen"] = (
                int(self.diagnostics["artifact_call_records_seen"]) + 1
            )
            node_info = node_map.get((qualified_name, node_type))
            if not node_info:
                self.diagnostics["artifact_call_records_dropped_missing_caller"] = (
                    int(
                        self.diagnostics[
                            "artifact_call_records_dropped_missing_caller"
                        ]
                    )
                    + 1
                )
                continue
            merged = merged_by_caller.get(node_info)
            if merged is None:
                merged_by_caller[node_info] = {
                    "qualified_name": qualified_name,
                    "node_type": node_type,
                    "callee_identifiers": list(callee_identifiers),
                }
                continue
            if (
                merged["qualified_name"] != qualified_name
                or merged["node_type"] != node_type
            ):
                raise RuntimeError(
                    "Conflicting caller metadata for structural id "
                    f"{node_info}: "
                    f"{merged['qualified_name']}/{merged['node_type']} vs "
                    f"{qualified_name}/{node_type}"
                )
            merged["callee_identifiers"].extend(callee_identifiers)
        for caller_structural_id, merged in merged_by_caller.items():
            call_artifacts.append(
                CallExtractionRecord(
                    caller_structural_id=caller_structural_id,
                    caller_qualified_name=str(merged["qualified_name"]),
                    caller_node_type=str(merged["node_type"]),
                    callee_identifiers=tuple(
                        dict.fromkeys(merged["callee_identifiers"])
                    ),
                )
            )
        return call_artifacts

    def _warn(self, message: str) -> None:
        self.warnings.append(message)
        logger.warning(message)
        if self._warning_sink:
            self._warning_sink(message)



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
    return {
        key: structural_id for key, structural_id in mapping.items() if structural_id
    }


def _load_module_index(conn, snapshot_id: str) -> set[str]:
    rows = core_read.list_nodes_by_types(conn, snapshot_id, ["module"])
    return {qualified_name for _structural_id, _node_type, qualified_name in rows}
