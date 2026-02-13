Run the SCIONA reducer quality evaluation and return a consolidated report.

Steps:
1. Use contracts from `experiments/reducers/reducer_contracts.yaml`.
2. Metric definitions are in `experiments/reducers/reducer_quality-howto.dm`.
3. Run the helper script and write reports to `experiments/reports/`.
4. Fill in the `Copilot Overall Summary` section in the Markdown report.
5. Summarize contract-aware results, blind validation results, and contract consistency/scope mismatches in your response.

Execution:
- Run with python (system, venv, or conda).

Script:
- `experiments/reducers/reducer_quality.py`

Args:
- `--nodes 100`
- `--runs 10`
- `--seed 20260212`
- `--repo-root /path/to/other/repo`
