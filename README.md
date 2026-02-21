<p align="left">
    <img src="assets/logo.jpg" alt="SCIONA logo" width="240">
</p>


SCIONA builds a **deterministic structural index (SCI)** for a *git* repository. It captures what exists in the code (modules, classes, functions, methods) and how entities are structurally connected. SCIONA is **snapshot-based, reducer-driven, and LLM-agnostic**. It does not execute code or perform semantic inference. Instead, SCIONA produces  explicit structural representations derived from tree-sitter parsing. Analysis is static and source-only across supported languages. Reducers serve as the source of structural evidence, rendering reproducible  facts from a committed snapshot. **This deterministic representation can be used to stabilize tooling workflows, including LLM-assisted development.**

## Why SCIONA exists

When working with large, long-lived codebases, we repeatedly observed the same pattern: LLM assistance initially improves productivity, but gradually becomes inconsistent.  Earlier assumptions drift. Structural constraints are forgotten. The model continues to generate plausible responses that no longer reflect the actual code. **This is not primarily an LLM failure. It is a context stability problem**.

In real software systems, correctness often depends on structural relationships. Most LLM tooling relies on embeddings, semantic retrieval, or dynamically assembled  context. While powerful, these approaches can be difficult to reproduce and hard to constrain across long sessions or refactors.

SCIONA takes a deliberately different path: it provides a stable structural snapshot that downstream tools can rely on. Rather than reconstructing structure heuristically, tools may reason over deterministic reducer outputs. **SCIONA is intentionally limited in scope. It provides structure - not interpretation.**

## Disclaimer

SCIONA was originally developed as an internal tool at MegaScienta to address limitations observed in LLM-assisted workflows. It has been tested in day-to-day development across several active projects and has demonstrated practical utility in internal workflows.

The tool is functional and actively used, but should currently be considered an early public release. Broader real-world validation across diverse repositories is still ongoing. Feedback, issue reports, and field experience are highly appreciated. Thank you and happy coding.

## How SCIONA can be used

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows. During initialization, SCIONA optionally auto-generates an `AGENTS.md` file in the repository root. This file serves as a control surface for LLM copilots by explicitly specifying how SCIONA should be used during code reasoning. In this mode, the copilot is instructed to reason over reducer outputs rather than reconstructing structure heuristically from source text.

## Installation

Requirements:
- Python 3.11 or 3.12
- Git (for cloning and for snapshot metadata)
- `pip` (or another PEP 517 installer)
- Note: Python 3.13 is not supported because `tree_sitter_languages` does not publish wheels yet.

Default install (from GitHub release tag):

```bash
pip install git+https://github.com/megascienta/sciona@vX.Y.Z
```

Install development version with dependencies and run tests:

```bash
git clone https://github.com/megascienta/sciona
cd sciona
pip install -e ".[dev]"
pytest -q
```

## Quick start

```bash
cd /path/to/repo
sciona init
$EDITOR .sciona/config.yaml   # enable languages
sciona build
sciona status
```

## Supported languages

Built-in analyzers currently include Python, TypeScript, and Java. Enable languages in `.sciona/config.yaml` after `sciona init`.

## Snapshot model

SCIONA indexes the **last committed snapshot**. Reducers are evaluated against that committed snapshot, not against uncommitted working tree state. If you change tracked source files, commit and run `sciona build` to refresh the snapshot before relying on reducer output.

If your worktree is dirty, reducer outputs include an `_diff` payload describing a best‑effort overlay of uncommitted changes. `_diff` payload should be treated as advisory. The current `_diff` schema is minimal: it reports scope plus `affected`/`affected_by` signals rather than full change lists. Please use a clean commit and `sciona build` for authoritative results.

## Reducer Contract Validation

SCIONA includes a repository-independent reducer validation workflow in `experiments/reducers/`.
It validates reducer behavior against:
- direct SCIONA DB queries (internal consistency),
- independent language parsers (external reference),
- an explicit structural contract (`experiments/reducers/validation/structural_contract.yaml`).

Usage:

```bash
python experiments/reducers/reducer_validation.py \
  --repo-root /path/to/repo \
  --nodes 500 \
  --seed 20260221 \
  --stability-runs 3
```

Workflow (current implementation):
1. Sample a balanced set of module/class/function/method nodes from SCIONA DB.
2. Parse corresponding files with independent parsers (Python, TypeScript, Java).
3. Normalize independent outputs to SCIONA-comparable edge shape.
4. Build two channels per node:
   - `contract_truth`: parser edges that satisfy SCIONA contract and resolve in-repo,
   - `enrichment`: dynamic/unresolved/external/standard-call diagnostics.
5. Collect reducer edges and direct DB edges for the same node.
6. Compute per-node and micro metrics for:
   - reducer vs DB,
   - reducer vs contract truth,
   - DB vs contract truth.
7. Enforce hard invariants (run-gating).
8. Emit JSON + Markdown reports to `experiments/reducers/reports/`.

Hard invariants (all must pass):
- `gate_reducer_db_exact`
- `gate_aligned_scoring`
- `gate_parse_coverage`
- `gate_contract_truth_pure`
- `gate_contract_truth_resolved`
- `gate_parser_deterministic`
- `gate_no_duplicate_contract_edges`
- `gate_typescript_relative_index_contract`
- `gate_class_truth_nonempty_rate`
- `gate_scoped_call_normalization`
- `gate_equal_contract_metrics_when_exact`

Core metrics:
- `contract_recall`: reducer coverage of independent contract truth.
- `overreach_rate`: reducer edges not present in independent contract truth.
- `quality_gates.class_truth_nonempty_rate`: evaluator quality gate for class truth completeness.
- `micro_metrics_by_kind`: module/class/function/method decomposition.

Validation implementation constraints:
- Independent validation logic does not import SCIONA core language semantic normalizers.
- Artifact rollups are rebuilt fully each run (correctness-first; incremental disabled by default).

Current report snapshot (N=500 each, from `experiments/reducers/reports/`):

| Repository | Language | Sampled Nodes | Invariants Passed | Reducer vs DB | Contract Recall | Overreach Rate |
| ---------- | -------- | ------------- | ----------------- | ------------- | --------------- | -------------- |
| [Apache Commons Lang](https://github.com/apache/commons-lang) | Java | 500 | **True** | **1.0 / 1.0** | **0.7918** | **0.0142** |
| [FastAPI](https://github.com/fastapi/fastapi) | Python | 500 | **False** | **1.0 / 1.0** | **0.9783** | **0.0167** |
| [Nest](https://github.com/nestjs/nest) | TypeScript | 500 | **False** | **1.0 / 1.0** | **0.9289** | **0.2249** |

Interpretation:
- Reducer vs DB exact overlap (`1.0 / 1.0`) means reducer projection is internally consistent with DB for sampled nodes.
- If invariants fail (for example `gate_class_truth_nonempty_rate`), treat comparison metrics as diagnostic only until evaluator quality is restored.
- `contract_recall` is the primary SCIONA contract-coverage signal.
- Higher `overreach_rate` indicates mismatch pressure between reducer output and independent contract truth representation; investigate with per-node report details and `out_of_contract_breakdown`.

## Reducers usage

### Discovery

Explore available reducers:

```bash
sciona reducer list
sciona reducer --id module_overview --module-id pkg.mod
```

If node (module, classes, function, method) identifier is unknown:

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Available reducers:

#### Category: core

Ranked structural symbol matches for a query. Use when resolving unknown identifiers. Scope: query → symbols.

```bash
sciona reducer --id symbol_lookup [--query QUERY] [--kind KIND] [--limit LIMIT]
```

Structural relationships (calls/imports) for matched symbols. Use for impact analysis or dependency tracing. Scope: symbol → relations.

```bash
sciona reducer --id symbol_references [--query QUERY] [--kind KIND] [--limit LIMIT]
```

Structural outline of a file, including modules, classes, and callables. Use for navigation and symbol discovery. Scope: file-level structure.

```bash
sciona reducer --id file_outline [--module-id MODULE_ID] [--file-path FILE_PATH]
```

Structural summary of a callable, including signature, location, and metadata. Use for quick callable inspection without retrieving full source. Scope: single function or method.

```bash
sciona reducer --id callable_overview [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID]
```

Structural summary of a class, including methods and metadata. Use for quick class inspection. Scope: class-level structure.

```bash
sciona reducer --id class_overview [--class-id CLASS_ID] [--method-id METHOD_ID]
```

Structural summary of a module, including contained classes and callables. Use for architectural inspection. Scope: module-level.

```bash
sciona reducer --id module_overview [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID] [--class-id CLASS_ID] [--include-file-map]
```

Canonical structural index of the codebase. Use for global structural reasoning or validation. Scope: entire SCI snapshot.

```bash
sciona reducer --id structural_index
```

Explicit module import dependencies. Use for analysing module coupling or dependency graphs. Scope: module-level import edges.

```bash
sciona reducer --id dependency_edges [--module-id MODULE_ID] [--from-module-id FROM_MODULE_ID] [--to-module-id TO_MODULE_ID] [--query QUERY] [--edge-type EDGE_TYPE] [--direction DIRECTION] [--limit LIMIT]
```

Parsed base classes and inheritance relations. Use when reasoning about type hierarchy or polymorphic structure. Scope: class hierarchy.

```bash
sciona reducer --id class_inheritance [--class-id CLASS_ID]
```

#### Category: grounding

Full source code of a callable. Use only when implementation details are required. Scope: single function or method.

```bash
sciona reducer --id callable_source [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID]
```

Concatenated source code for a selected scope (codebase/module/class). Use for large-context reasoning or cross-entity inspection. Scope: configurable.

```bash
sciona reducer --id concatenated_source [--scope SCOPE] [--module-id MODULE_ID] [--class-id CLASS_ID]
```

#### Category: analytics

Indexed caller/callee edges for a callable, including callsite details. Use when reasoning about call directionality or callsite-level analysis. detail_level='neighbors' returns caller/callee sets. Scope: callable-level call edges.

```bash
sciona reducer --id callsite_index [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID] [--direction DIRECTION] [--detail-level DETAIL_LEVEL]
```

Summary of call relationships within a class. Use for analysing method interaction patterns or internal coupling. Scope: class-level call graph.

```bash
sciona reducer --id class_call_graph_summary [--class-id CLASS_ID] [--method-id METHOD_ID] [--top-k TOP_K]
```

Summary of call relationships within a module. Use for module-level flow or coupling analysis. Scope: module call graph.

```bash
sciona reducer --id module_call_graph_summary [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID] [--class-id CLASS_ID] [--top-k TOP_K]
```

Fan-in/fan-out metrics for calls and imports. Use to identify highly connected entities or hotspots. Scope: callable/class/module.

```bash
sciona reducer --id fan_summary [--callable-id CALLABLE_ID] [--function-id FUNCTION_ID] [--method-id METHOD_ID] [--class-id CLASS_ID] [--module-id MODULE_ID] [--top-k TOP_K]
```

Compressed summary of structurally significant or highly connected entities. Use for architectural orientation or complexity inspection. Scope: codebase-level.

```bash
sciona reducer --id hotspot_summary
```

## Project Governance

Sciona is developed and maintained by Dmitry Chigrin. This work is part of my independent research & engineering activities under the MetaScienta brand.

## Support Sciona

If Sciona contributes to your development workflow, you can support its maintenance:

GitHub Sponsors  
buymecoffee.com/sciona
