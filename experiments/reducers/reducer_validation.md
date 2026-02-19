# SCIONA Reducer Validation Protocol

## 1. Objective
Evaluate SCIONA’s structural index, reducers, and DB-derived evidence as a deterministic, static structural evidence system for real repositories. The experiment must measure correctness within contract and quantify out-of-contract gaps without marketing claims.

### Success criteria (default thresholds)
Validation is considered successful only if all conditions below hold:
- Mean in-contract precision ≥ **0.95**
- Mean in-contract recall ≥ **0.90**
- No language or node-kind subgroup precision < **0.85**
- No language or node-kind subgroup recall < **0.80**

Thresholds are intentionally conservative for initial runs and may be tightened after stability is demonstrated.

## 2. Hypotheses
H1: For static structure (imports, defs, call expressions), SCIONA’s outputs are consistent and accurate relative to an independent parser pipeline.

H2 (quantified): At least **80%** of SCIONA misses correspond to edges classified as out-of-contract by the ground-truth parser.

## 3. Scope
Languages: Python, TypeScript, Java.

Evidence types:
- Node definitions: module, class, function, method
- Import edges (module-level)
- Call edges (file-local call expressions)

No runtime resolution, no type inference, no dynamic execution.

### Edge definition (exact patterns)
Include:
- Direct call expressions
- Method calls (e.g., `obj.method()`)
- Constructor calls (`ClassName()` in Python; `new ClassName()` in TS/Java)

Exclude (out-of-contract):
- Dynamic dispatch via reflection or string-based invocation
- `eval`/`exec` (Python)
- Dynamic `import()`/`require()` with non-literals (TS)
- Java reflection (`Class.forName`, `Method.invoke`, etc.)

Calls inside strings/templates are excluded.

## 4. Ground Truth (Independent Parsing)
Independent parser stack, minimal scope:
- Python: stdlib `ast`
- TypeScript: TypeScript compiler API (Node)
- Java: JavaParser (JVM)

Extraction is file-local:
- Imports
- Call expressions
- Defs + spans

Dynamic or semantic edges are flagged, not counted as errors.

### Ground-truth reliability
Parsers are not infallible. The evaluator MUST log:
- parse success/failure per file
- skipped files and reasons

Any file flagged as `ground_truth_unreliable` is excluded from scoring.

## 5. Sampling
Balanced sampling over:
- Language (Python/TS/Java)
- Node kind (module/class/function/method)

Stratify by:
- File size (LOC): small / medium / large
- Call density: sparse / moderate / dense
- Node depth: top-level / nested

Sampling is sourced from the `structural_index` reducer (canonical SCI projection), then expanded using module overviews to enumerate functions and methods.

N nodes total (default 100–300).
Only sampled nodes are fully re-parsed by independent tools.

## 6. Evidence Sources (Per Node)
For each sampled node, collect evidence from three sources and keep full payloads:

### A) Reducer evidence (SCIONA)
- `callsite_index` reducer for call edges (detail level: callsites, direction: out)
- `dependency_edges` reducer for module import edges
- `class_overview` / `module_overview` reducers for identity and structure

### B) DB evidence (SCIONA API + direct queries)
- CoreDB import edges (`IMPORTS_DECLARED`)
- ArtifactDB call edges (`CALLS`)
- Node identity (structural_id, file_path, spans)

### C) Independent parser evidence
- File-local calls and imports from independent parsers

Comparisons are performed between:
- Reducer vs Independent
- DB vs Independent
- Reducer vs DB

SCIONA is evaluated only through reducers (tests reducer, DB, and analysis layers together).

### Reducer vs index separation
Diagnostics MUST distinguish:
- Index consistency failures (node exists in SCI but missing from reducer output)
- Reducer output mismatches (node present but edges differ)

## 7. Metrics
Per node:
- `in_contract_expected_edges`
- `out_of_contract_edges`
- `in_contract_precision`
- `in_contract_recall`
- `in_contract_false_positive_count`
- `out_of_contract_missing_count`

Aggregate:
- Mean precision/recall by language and node type
- Distribution of out-of-contract edges
- Edge type breakdown: imports vs calls
 - Reducer vs DB agreement (precision/recall treating DB as reference)

### Additional stability and coverage
- `stability_score`: hash stability of reducer outputs for identical snapshot
- `coverage_node_rate`: % of sampled nodes present in SCI
- `coverage_file_rate`: % of sampled files indexed

## 8. Interpretation Rules
- Errors in `in_contract_*` are SCIONA failures.
- `out_of_contract_*` gaps are not failures; they quantify known limits.
- Validation passes only if success criteria hold globally and in subgroups.

## 9. Outputs
- JSON report (per-node + aggregate)
- Markdown summary (tables + key findings)
- Confusion breakdown (TP/FP/FN by edge type) for reducer and DB
- Representative failure examples (5–10)

## 10. Setup & Running

### Prerequisites
- SCIONA indexed repository (`sciona build` must have been run in that repo).
- Python 3.11+
- Node.js (for TypeScript parser)
- Java JDK (for JavaParser)

### Node/TypeScript setup
Install TypeScript in the reducer experiment folder:
```bash
cd experiments/reducers
npm install
```

### JavaParser setup
Place `javaparser-core-<version>.jar` in `experiments/reducers/jar/`, then set:
`experiments/reducers/validation/local_config.py`
```python
JAVAPARSER_JAR = "experiments/reducers/jar/javaparser-core-3.25.9.jar"
```
This path is resolved relative to repo root.

### Run validation on any repo
```bash
python experiments/reducers/reducer_validation.py --repo-root /path/to/repo --nodes 200 --seed 20260219
```
Outputs:
- `experiments/reducers/reports/<repo>_reducer_validation.json`
- `experiments/reducers/reports/<repo>_reducer_validation.md`

## 11. Contract definition mismatch risk
The primary risk is mismatch between SCIONA contract and ground-truth extraction.

Mitigations:
- Publish a formal contract spec
- Encode as machine-readable rules
- Use identical definitions in both pipelines
