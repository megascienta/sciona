Run the SCIONA reducer validation experiment and return a consolidated report.

Steps:
1. Follow `experiments/reducers/reducer_validation.md` for protocol and metrics.
2. Run the helper script and write reports to `experiments/reducers/reports/`.
3. Summarize in-contract vs out-of-contract results and subgroup metrics.
4. Include representative failure examples in your response.

Execution:
- Run with python (system, venv, or conda).

Script:
- `experiments/reducers/reducer_validation.py`

Args:
- `--nodes 200`
- `--seed 20260219`
- `--repo-root /path/to/other/repo`
