# Reducer Validation Workflow

## Purpose
This workflow produces one focused report answering exactly three questions:
1. Reducers vs DB correctness (must be exact).
2. Reducers vs independent parser output within static contract (target near-100% with zero FP/FN).
3. Out-of-contract envelope (descriptive uplift and breakdown only).

## Pipeline
1. Load entities from artifacts/DB (`module`, `class`, `function`, `method`).
2. Stratified sampling by language/kind.
3. Parse sampled files with independent parsers.
4. Build normalization/resolution context under shared static contract.
5. Evaluate entities to produce per-node metrics and out-of-contract metadata.
: Q2 compares only contract-filtered edges on both sides (independent truth and core/reducer edges).
6. Emit one JSON report and one markdown summary (Q1/Q2/Q3 only).

## Report Surface
Top-level JSON keys used by current report path:
- `report_schema_version`
- `summary`
- `invariants`
- `quality_gates`
- `per_node`
- `questions` (`q1`, `q2`, `q3`)

Markdown sections:
- `Q1. Reducers vs DB Correctness`
- `Q2. Reducers vs Independent Within Static Contract`
- `Q3. Beyond Static Contract Envelope`

## Run
```bash
conda run -n multiphysics \
python validations/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221
```
