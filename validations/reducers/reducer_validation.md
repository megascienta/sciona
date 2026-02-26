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
- `missing_rate_i = |S1_i \ S2_i| / |S1_i|`
- `spillover_rate_i = |S2_i \ S1_i| / |S1_i|`
- `mutual_accuracy_i = |S1_i ∩ S2_i| / |S1_i ∪ S2_i|`
- `q3_rate_i = |S3_i| / |S1_i|`

## Questions
### Q1
Exactness check between reducer edges and DB edges.
Pass requires:
- `missing_count == 0`
- `spillover_count == 0`

### Q2
Overlap quality inside static contract.
Primary metrics:
- `avg_mutual_accuracy` (target close to `1.0`)
- `avg_missing_rate` (target close to `0.0`)
- `avg_spillover_rate` (target close to `0.0`)

Default gate:
- `avg_mutual_accuracy >= 0.99`
- `avg_missing_rate <= 0.01`
- `avg_spillover_rate <= 0.01`

### Q3
Descriptive only.
Report only:
- `avg_out_of_contract_rate_percent` (mean of per-node `|S3_i|/|S1_i| * 100`)
- `by_semantic_type_avg_percent` (mean per-node type-specific out-of-contract rate)

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
