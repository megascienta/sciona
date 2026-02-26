# Reducer Validation Workflow

## Scope
This workflow answers exactly three questions and nothing else:
1. Q1: reducers vs DB consistency (must be exact).
2. Q2: reducer contract set overlap with independent constrained set.
3. Q3: independent enrichment beyond contract (basket 2) composition.

No backward compatibility layer is maintained for legacy precision/recall report fields.

## Set Model
Edge sets are used (not node sets).

- `S1`: reducer contract edge set (basket 1 reference).
- `S2`: independent constrained edge set (basket 1 candidate).
- `S3`: independent out-of-contract enrichment edge set (basket 2).

Definitions:
- `intersection = |S1 ∩ S2|`
- `missing = |S1 \ S2|`
- `spillover = |S2 \ S1|`
- `coverage = |S1 ∩ S2| / |S1|`
- `spillover_ratio = |S2 \ S1| / |S1|`
- `q3_uplift = |S3| / |S1|` (reported as percent)

## Questions
### Q1
Exactness check between reducer edges and DB edges.
Pass requires:
- `missing_count == 0`
- `spillover_count == 0`

### Q2
Overlap quality inside static contract.
Primary metrics:
- `coverage` (target close to `1.0`)
- `spillover_ratio` (target close to `0.0`)

Default gate:
- `coverage >= 0.99`
- `spillover_ratio <= 0.01`

### Q3
Descriptive only.
Report only:
- `additional_vs_reducer_output` (percent; `|S3|/|S1| * 100`)
- `by_semantic_type_percent` (type distribution within `S3`)

## Pipeline
1. Load entities from artifacts/DB (`module`, `class`, `function`, `method`).
2. Sample entities by language/kind.
3. Parse files via independent parsers.
4. Normalize and impose contract using the core contract path.
5. Build sets `S1`, `S2`, `S3` per entity.
6. Aggregate Q1/Q2/Q3 set metrics.
7. Emit one JSON and one markdown report.

## Report Contract
Top-level keys:
- `report_schema_version`
- `summary`
- `invariants`
- `quality_gates`
- `per_node`
- `questions`

Per-node metric keys:
- `set_q1_reducer_vs_db`
- `set_q2_reducer_vs_independent_contract`
- `basket2_edges`

Legacy keys removed and rejected:
- `metrics_reducer_vs_db`
- `metrics_reducer_vs_contract`
- `metrics_db_vs_contract`

## Run
```bash
conda run -n multiphysics \
python validations/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221
```
