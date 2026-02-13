# Metric Calculation Guide (Short)

This file summarizes how each analyzed metric is computed in the reducer quality evaluation.

Core metrics:
- `unknown_id_qname_rate`: For each invocation, collects IDs and qualified names from contract evidence or required fields. Tokens are classified into buckets: `out_of_scope` (outside indexed tree by design), `out_of_sample` (resolves in DB but not in sampled population), `unresolved_in_scope` (should be resolvable but is not), or `resolution_failure` (malformed or resolver error). The reported `unknown_id_qname_rate` only counts categories enabled by `unknown_policy` (default: `unresolved_in_scope` + `resolution_failure`). `out_of_scope` and `out_of_sample` are reported but not penalized unless policy enables them. Source reducers and reducers with `unknown_policy.enabled: false` are excluded from this check.
- `omission_rate`: For each invocation, counts missing required fields (or, for source reducers, missing target file/source). The report uses missing-count per invocation as a rate proxy.
- `structural_accuracy`: Extracts 40-hex ID pairs from reducer output and compares each to known edges in SCIONA DB or artifacts DB. Accuracy = 1 - (invalid_pairs / total_pairs). Defaults to 1.0 when no pairs are found. This metric can be disabled via `structural_accuracy_policy`.
- `identifier_overlap` (evidence-term overlap): For each invocation, extracts identifier terms from direct code (tree-sitter preferred, AST fallback). For structured reducers, compares to identifier tokens found in contract evidence/required fields (echo and content-hash fields excluded). Overlap = matched_terms / total_terms. Source reducers match terms in raw output text. This metric is gated by `overlap_policy` or reducer type; summary/aggregation reducers should typically disable overlap because they do not echo identifier terms.
- `length_stability`: 1 / (1 + token_length_variation_cv), where CV is the coefficient of variation of token counts across repeated runs.
- `determinism_score`: For each invocation, hashes outputs from repeated runs and computes the share of the most common hash; averaged across invocations.
- `schema_compliance_score`: Proportion of required fields/paths, type checks, and invariants satisfied (as defined by reducer contracts). This includes list policies (`allow_empty`, `min_items`) and invariant rules.
- `coverage_score`: Fraction of invocations where required fields are present (or, if no required fields, a non-empty payload is returned).
- `error_rate`: Invocation errors / total invocations for the reducer.
- `cross_run_structural_diff`: Average structural variance across runs (based on unique output hashes).
- `ordering_instability_rate`: Fraction of invocations where outputs differ only by list/map ordering (order-invariant canonicalization matches).
- `latency_ms_avg`, `latency_ms_p95`, `latency_ms_max`: Reducer invocation latency statistics (milliseconds).
- `db_consistency_score` (run-level): Intersection-over-union of core DB IDs and artifact DB IDs (artifact DB is expected to exist).

Contract-driven rules:
- `unknown_policy`: Controls which unknown categories count toward `unknown_id_qname_rate` and whether the check runs at all.
- `overlap_policy`: Enables or disables evidence-term overlap per reducer. Use this to suppress overlap for summary/aggregation reducers.
- `structural_accuracy_policy`: Enables or disables structural accuracy per reducer.
- `allow_empty`: Marks list fields that may be empty (schema compliance will fail if the field is missing or not a list).
- `min_items`: Minimum list lengths enforced as part of schema compliance.
- Invariant DSL supports: `equals_len`, `min_items`, `unique`, `non_negative`, `subset_of`.

Blind validation sub-metrics:
- `id_resolution_rate`: Fraction of IDs in payload that exist in SCIONA DB.
- `file_span_valid_rate`: Fraction of file spans that map to valid files and line ranges.
- `count_consistency_rate`: Fraction of `*_count` fields that match the length of their sibling list.
- `line_span_hash_match_rate`: Fraction of line-span hashes that match the extracted snippet (with normalization).
- `content_hash_match_rate`: Fraction of content hashes that match the extracted snippet (with normalization). Mismatches can reflect normalization differences or snapshot-vs-working-tree drift. Hash diagnostics (span, snippet preview, candidate hashes) are always collected.
- Coherence check note: `call_neighbors` vs `callsite_index` should be compared after normalizing callsite edges (flatten caller/callee and exclude the focal callable id).
- `blind_error_rate`: 1 - average of the five blind rates above.

Additional reporting:
- Baseline comparison (optional): when `--baseline-json` is provided, the report includes delta summaries and regression flags based on configurable thresholds (`--regression-thresholds`).
- Blind summaries by language/kind: blind metrics are aggregated per language and per entity kind for easier cross-language drift detection.
- Toolchain metadata: SCIONA version and evaluator SHA1 are recorded in the report header.
