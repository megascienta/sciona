"""Git hook helpers (pipeline-owned)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..runtime import paths as runtime_paths

_BEGIN = "# sciona:begin"
_END = "# sciona:end"


@dataclass(frozen=True)
class HookStatus:
    installed: bool
    command: str | None
    hook_path: Path


def install_post_commit_hook(repo_root: Path, command: str) -> HookStatus:
    hook_path = _hook_path(repo_root)
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    existing = hook_path.read_text(encoding="utf-8") if hook_path.exists() else ""
    updated = _upsert_block(existing, command)
    hook_path.write_text(updated, encoding="utf-8")
    hook_path.chmod(0o755)
    return HookStatus(installed=True, command=command, hook_path=hook_path)


def remove_post_commit_hook(repo_root: Path) -> HookStatus:
    hook_path = _hook_path(repo_root)
    if not hook_path.exists():
        return HookStatus(installed=False, command=None, hook_path=hook_path)
    text = hook_path.read_text(encoding="utf-8")
    updated = _remove_block(text)
    if not updated.strip():
        hook_path.unlink()
        return HookStatus(installed=False, command=None, hook_path=hook_path)
    hook_path.write_text(updated, encoding="utf-8")
    command = _extract_command(updated)
    return HookStatus(installed=command is not None, command=command, hook_path=hook_path)


def post_commit_hook_status(repo_root: Path) -> HookStatus:
    hook_path = _hook_path(repo_root)
    if not hook_path.exists():
        return HookStatus(installed=False, command=None, hook_path=hook_path)
    text = hook_path.read_text(encoding="utf-8")
    command = _extract_command(text)
    return HookStatus(installed=command is not None, command=command, hook_path=hook_path)


def _hook_path(repo_root: Path) -> Path:
    return runtime_paths.validate_repo_root(repo_root) / ".git" / "hooks" / "post-commit"


def _upsert_block(text: str, command: str) -> str:
    block = _render_block(command)
    start = text.find(_BEGIN)
    end = text.find(_END)
    if start != -1 and end != -1 and end > start:
        before = text[:start].rstrip()
        after = text[end + len(_END) :].lstrip("\n")
        merged = "\n".join(part for part in [before, block, after] if part)
        return merged.strip() + "\n"
    merged = text.rstrip()
    if merged:
        merged += "\n\n"
    merged += block
    return merged.strip() + "\n"


def _remove_block(text: str) -> str:
    start = text.find(_BEGIN)
    end = text.find(_END)
    if start == -1 or end == -1 or end < start:
        return text
    before = text[:start].rstrip()
    after = text[end + len(_END) :].lstrip("\n")
    merged = "\n".join(part for part in [before, after] if part)
    return merged.strip() + "\n" if merged.strip() else ""


def _extract_command(text: str) -> str | None:
    start = text.find(_BEGIN)
    end = text.find(_END)
    if start == -1 or end == -1 or end < start:
        return None
    content = text[start + len(_BEGIN) : end].strip().splitlines()
    for line in content:
        if not line.strip() or line.strip().startswith("#"):
            continue
        return line.strip()
    return None


def _render_block(command: str) -> str:
    return "\n".join(
        [
            _BEGIN,
            "# Run SCIONA build after commit (managed).",
            command.strip(),
            _END,
        ]
    )


__all__ = [
    "HookStatus",
    "install_post_commit_hook",
    "post_commit_hook_status",
    "remove_post_commit_hook",
]
