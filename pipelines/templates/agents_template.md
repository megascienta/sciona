# SCIONA usage (managed)

Goal: maximize use of SCIONA CLI before manual inspection or ad-hoc scripts.

1) Invocation (confirm once per thread)
- Ask which command to use: `sciona …` or `conda run -n <env> sciona …` (only the first time in a thread).
- After the first answer, reuse that invocation without asking again.

2) Always start with ids
- Find candidates:
  `sciona search <query> --kind module|class|function|method|callable --limit 10`
- Resolve a specific id:
  `sciona resolve <identifier> --kind module|class|function|method|callable`

Note: if the worktree is dirty, outputs reflect the latest committed snapshot only.

3) Dirty worktree strategy (recommended)
- SCIONA reflects the last committed snapshot only.
- Use SCIONA for structure/calls/deps, then manually verify files you changed.
- For accurate SCIONA results on new/modified files, make small WIP commits and amend/squash later.

4) Common tasks (copy/paste templates)
{COMMON_TASKS}

5) Reducer discovery
- `sciona reducer list`
- `sciona reducer info --id <reducer_id>`

6) Reporting (required)
- Prefer a compressed SCIONA evidence summary over raw dumps.
- After evidence, you may add a clearly labeled interpretation note.
- If worktree is dirty, say outputs reflect the latest committed snapshot only.

7) If SCIONA cannot answer
- State which command failed and why, then open files manually.

8) Troubleshooting
- "No committed snapshots" → run `sciona build`.
- "Unknown reducer" → run `sciona reducer list`.
