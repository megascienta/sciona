"""Prompt compilation pipeline."""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import Optional

from ..prompts import compile_prompt, get_prompts
from .errors import WorkflowError
from ..data_storage.connections import core
from ..runtime.paths import get_db_path
from ..runtime.config import load_llm_settings
from ..runtime.llm import Adapter
from .policy import prompt as prompt_policy
from .resolve import require_identifier

_SECTION_PREFIX = "## "


def prompt_allows_answer(prompt_name: str, *, repo_root: Optional[Path] = None) -> bool:
    prompts = get_prompts(repo_root)
    entry = prompts.get(prompt_name)
    if not entry:
        return False
    allow_answer = entry.get("allow_answer")
    if allow_answer is None:
        return True
    return bool(allow_answer)

def compile_prompt_by_name(
    prompt_name: str,
    *,
    repo_root: Optional[Path] = None,
    arg_map: Optional[dict[str, str]] = None,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
) -> tuple[str, str]:
    prompt_text, snapshot_id, _ = _compile_prompt_with_resolution(
        prompt_name,
        repo_root=repo_root,
        arg_map=arg_map,
        node_id=node_id,
        node_name=node_name,
    )
    return prompt_text, snapshot_id


def compile_prompt_payload(
    prompt_name: str,
    *,
    repo_root: Optional[Path] = None,
    arg_map: Optional[dict[str, str]] = None,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
) -> tuple[str, str, dict[str, str]]:
    """Compile a prompt and return the resolved argument map."""
    prompt_text, snapshot_id, resolved_args = _compile_prompt_with_resolution(
        prompt_name,
        repo_root=repo_root,
        arg_map=arg_map,
        node_id=node_id,
        node_name=node_name,
    )
    return prompt_text, snapshot_id, resolved_args


def _compile_prompt_with_resolution(
    prompt_name: str,
    *,
    repo_root: Optional[Path] = None,
    arg_map: Optional[dict[str, str]] = None,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
) -> tuple[str, str, dict[str, str]]:
    repo_root = prompt_policy.ensure_prompt_preconditions(repo_root)
    entry = get_prompts(repo_root).get(prompt_name)
    if not entry:
        raise WorkflowError(f"Unknown prompt '{prompt_name}'.", code="unknown_prompt")
    required = entry.get("required_args") or []
    arg_map = dict(arg_map or {})
    db_path = get_db_path(repo_root)
    conn_ctx = (
        core(db_path, repo_root=repo_root)
        if db_path.exists()
        else nullcontext(None)
    )
    with conn_ctx as conn:
        if conn is None:
            raise WorkflowError(
                "No committed snapshots available. Run 'sciona build' first.",
                code="missing_snapshot",
            )
        snapshot_id = prompt_policy.resolve_latest_snapshot(conn)
        _apply_prompt_node_resolution(
            conn,
            snapshot_id,
            required_args=required,
            node_id=node_id,
            node_name=node_name,
            arg_map=arg_map,
        )
        missing = [key for key in required if not arg_map.get(key)]
        if missing:
            raise WorkflowError(
                f"Missing required parameters: {', '.join(missing)}.",
                code="missing_parameters",
            )
        try:
            prompt_text = compile_prompt(
                prompt_name,
                snapshot_id,
                conn,
                repo_root,
                **arg_map,
            )
        except ValueError as exc:
            raise WorkflowError(str(exc), code="prompt_error") from exc
    return prompt_text, snapshot_id, dict(arg_map)


def answer_prompt_text_by_name(
    prompt_name: str,
    *,
    arg_map: dict[str, str],
    node_id: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> str:
    repo_root = prompt_policy.ensure_prompt_preconditions(repo_root)
    prompt_text, _, _ = _compile_prompt_with_resolution(
        prompt_name,
        repo_root=repo_root,
        arg_map=arg_map,
        node_id=node_id,
    )
    llm_cfg = load_llm_settings(repo_root)
    adapter = Adapter(
        llm_cfg.provider,
        api_key=llm_cfg.api_key,
        api_endpoint=llm_cfg.api_endpoint,
        timeout=llm_cfg.timeout,
        max_retries=llm_cfg.max_retries,
    )
    response = adapter.complete(
        prompt_text,
        model=llm_cfg.model,
        temperature=llm_cfg.temperature,
    )
    return response.text.strip()


def extract_prompt_sections(prompt_text: str) -> dict[str, Optional[str]]:
    """Split compiled prompt text into instructions and evidence blocks."""
    header, body = _split_prompt_header(prompt_text)
    sections = _split_markdown_sections(body)
    evidence = sections.get("Evidence")
    if sections:
        instruction_parts = []
        for title, content in sections.items():
            if title == "Evidence":
                continue
            if content:
                instruction_parts.append(f"{_SECTION_PREFIX}{title}\n{content}".strip())
            else:
                instruction_parts.append(f"{_SECTION_PREFIX}{title}")
        instructions = "\n\n".join(instruction_parts).strip() or None
    else:
        instructions = body.strip() or None
    return {
        "prompt_header": header,
        "prompt_body": body,
        "instructions": instructions,
        "evidence": evidence,
    }


def _split_prompt_header(prompt_text: str) -> tuple[str, str]:
    parts = prompt_text.split("\n\n", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return prompt_text.strip(), ""


def _split_markdown_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_title: Optional[str] = None
    current_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith(_SECTION_PREFIX):
            if current_title is not None:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[len(_SECTION_PREFIX) :].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None:
        sections[current_title] = "\n".join(current_lines).strip()
    return sections


def _apply_prompt_node_resolution(
    conn,
    snapshot_id: str,
    *,
    required_args: list[str],
    node_id: Optional[str],
    node_name: Optional[str],
    arg_map: dict[str, str],
) -> None:
    if not required_args:
        if node_id or node_name:
            raise WorkflowError("This prompt does not accept node identifiers.", code="invalid_prompt")
        return
    id_arg = _prompt_id_arg(required_args)
    if id_arg is None:
        return
    if id_arg in arg_map and (node_id or node_name):
        raise WorkflowError("Provide either a qualified name or --id, not both.", code="invalid_prompt")
    if node_id:
        arg_map[id_arg] = node_id
        return
    if node_name:
        kind = _id_arg_kind(id_arg)
        resolved = require_identifier(
            conn,
            snapshot_id,
            kind=kind,
            identifier=node_name,
        )
        arg_map[id_arg] = resolved


def _prompt_id_arg(required_args: list[str]) -> Optional[str]:
    for entry in ("callable_id", "function_id", "method_id", "class_id", "module_id"):
        if entry in required_args:
            return entry
    return None


def _id_arg_kind(id_arg: str) -> str:
    if id_arg == "callable_id":
        return "callable"
    return id_arg.replace("_id", "")
