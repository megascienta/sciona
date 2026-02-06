# SCIONA usage (managed)

Goal: always use SCIONA CLI first when installed, before manual inspection or ad-hoc scripts.

1) Invocation (confirm once per thread)
- Ask which command to use: `sciona …` or `conda run -n <env> sciona …` (only the first time in a thread).
- After the first answer, reuse that invocation without asking again.

2) Always start with ids
- Find candidates:
  `sciona search <query> --kind module|class|function|method|callable --limit 10`
- Resolve a specific id:
  `sciona resolve <identifier> --kind module|class|function|method|callable`

Note: if the worktree is dirty, outputs reflect the latest committed snapshot only.
If a reducer payload includes `_diff`, use the overlay as the primary evidence
for dirty-worktree changes and clearly separate it from committed snapshot data.

3) Dirty worktree strategy (recommended)
- SCIONA reflects the last committed snapshot only.
- When `_diff` is present, use it as the primary evidence for dirty-worktree changes.
- Use SCIONA for structure/calls/deps, then manually verify files you changed when needed.
- For accurate SCIONA results on new/modified files, make small WIP commits and amend/squash later.
- Dirty worktrees may include `_diff` overlays in reducer/prompt payloads; overlays are best-effort only.
- Reducers are JSON-only; prompts may include JSON payloads but remain human-oriented text.
- `_diff` overlays include nodes/edges and may include call-edge diffs and summary stats.
- `sciona build` clears any diff overlay tables on clean head before rebuilding artifacts.

4) Common tasks (copy/paste templates)
{COMMON_TASKS}

5) Reducer discovery
- `sciona reducer list`
- `sciona reducer info --id <reducer_id>`

6) Reporting (required)
- Prefer a compressed SCIONA evidence summary over raw dumps.
- After evidence, you may add a clearly labeled interpretation note.
- If worktree is dirty, say outputs reflect the latest committed snapshot only.
- If `_diff` is present, call it out explicitly as overlay data and use it as the primary evidence for dirty changes.

7) If SCIONA cannot answer
- State which command failed and why, then open files manually.

8) Troubleshooting
- "No committed snapshots" → run `sciona build`.
- "Unknown reducer" → run `sciona reducer list`.
