<p align="left">
    <img src="assets/logo.jpg" alt="SCIONA logo" width="240">
</p>

### Deterministic structural grounding for LLM-assisted development in medium-to-large codebases

SCIONA builds a **deterministic structural index (SCI)** for a *git* repository. It captures what exists in the code and how entities are structurally connected. SCIONA is **snapshot-based, reducer-driven, and LLM-agnostic**. It does not execute code or perform semantic inference. Instead, SCIONA produces explicit structural representations derived from [tree-sitter](https://tree-sitter.github.io/tree-sitter/) parsing. Analysis is static and source-only across the supported languages. Reducers serve as the source of structural evidence, rendering reproducible  facts from a committed snapshot. **This deterministic representation can be used to stabilize tooling workflows, including LLM-assisted development.**

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active%20development-orange)

## Why SCIONA exists

When working with large, long-lived codebases, we repeatedly observed the same pattern: LLM assistance initially improves productivity, but gradually becomes inconsistent. Earlier assumptions drift and structural constraints are gradually forgotten. The model continues to generate plausible responses that no longer reflect the actual code. **This is not primarily an LLM failure. It is a context stability problem**.

In real software systems, correctness often depends on structural relationships. Most LLM tooling relies on embeddings, semantic retrieval, or dynamically assembled  context. While powerful, these approaches can be difficult to reproduce and hard to constrain across long sessions or refactors.

SCIONA takes a deliberately different path: it provides a stable structural snapshot that downstream tools can rely on. Rather than reconstructing structure heuristically, tools can reason over deterministic reducer outputs. **SCIONA is intentionally limited in scope. It provides structure - not interpretation.**

## How SCIONA can be used

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows. **During initialization, SCIONA optionally auto-generates an `AGENTS.md` file in the repository root.** This file acts as a control surface for LLM copilots by explicitly specifying how SCIONA should be used during code reasoning. In this mode, the copilot is instructed to reason over reducer outputs instead of reconstructing repository structure heuristically from source text. Initialization can also optionally install a post-commit hook to keep the SCIONA snapshot metadata up to date.

## Supported languages

Built-in analyzers currently include **Python**, **TypeScript**, **JavaScript**, and **Java**. Enable languages in `.sciona/config.yaml` after `sciona init`.

## Snapshot model

SCIONA indexes the **last committed snapshot**. Reducers are evaluated against that committed snapshot, not against uncommitted working tree state. If you change tracked source files, commit and run `sciona build` to refresh the snapshot before relying on reducer output. If your worktree is dirty, reducer output includes a _diff advisory payload describing affected scope. Treat this as a signal, not a structural fact. For authoritative results, commit and `sciona build` first.

## Documentation

- Contract: [`docs/CONTRACT.md`](docs/CONTRACT.md)
- Developer guide: [`docs/DEVELOPERGUIDE.md`](docs/DEVELOPERGUIDE.md)
- Generated capability manifest: [`docs/CAPABILITY_MANIFEST.json`](docs/CAPABILITY_MANIFEST.json)

## Structural Resolution Performance

SCIONA has been tested on several large open-source repositories including **[VSCode](https://github.com/microsoft/vscode), [SymPy](https://github.com/sympy/sympy), [Guava](https://github.com/google/guava), [Webpack](https://github.com/webpack/webpack), [Airbyte](https://github.com/airbytehq/airbyte), and [NestJS](https://github.com/nestjs/nest)**. Validation reports, methodology description, and the full dataset are available in [`validations/build_status_reports/`](validations/build_status_reports/). That directory currently contains 11 JSON payloads; the aggregate figures in [`status_report.md`](validations/build_status_reports/status_report.md) are computed over 10 unique repositories because `vccode.json` is a legacy VSCode-named artifact and `vscode.json` is the canonical VSCode entry.

Across these repositories SCIONA processed **27,700 files**, extracted **304,824 structural nodes**, and analyzed **265,110 call sites**, producing **255,904 deterministic call edges**. This corresponds to an overall **~96.5% in-repository call resolution rate**. Resolution rates remain consistently high across supported languages, with **~98% for Python**, **~97.6% for TypeScript**, **~97.3% for JavaScript**, and **~90.6% for Java**.

Examples from large repositories include:
* **VSCode:** 149,573 call sites resolved at **97.6%**
* **SymPy:** 47,285 call sites resolved at **99.6%**
* **Guava:** 38,315 call sites resolved at **89.8%**

## Project Status

SCIONA was developed as an internal tool at MegaScienta to support LLM-assisted development in large repositories. It has been used in day-to-day engineering workflows and validated on several large open-source codebases. The project is now released publicly to encourage broader experimentation and community feedback. While the core architecture is stable and actively used, additional validation across diverse repositories and workflows is ongoing. *Issues, discussions, and field experience reports are very welcome.*

## Project Governance

SCIONA is developed and maintained by Dmitry Chigrin as part of independent research and engineering under the MegaScienta brand. Development combined conventional tooling with LLM-assisted programming; as the project matured, SCIONA was routinely used to ground LLM reasoning over its own repository. Final design decisions, integration, and validation remain the responsibility of the maintainer.

## Installation

Requirements:
- Python 3.11 or 3.12 (Python 3.13 is not supported yet)
- Git (for cloning and for snapshot metadata)
- `pip` (or another PEP 517 installer)

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
# machine-readable status payload
sciona status --json
# write full status payload to file
sciona status --output .sciona/status-report.json
```

## Reducers usage

Reducers are the primary interface for structural queries. Each reducer takes a scope (callable, classifier, module, or global) and returns a deterministic structural payload. Start with `sciona reducer list` to see what's available.

When the investigation already has a target module, caller, callee, identifier,
status, or provenance class, prefer reducer narrowing arguments before pulling
full broad payloads. For common diagnostics workflows, prefer compact summary
reducers such as `call_resolution_drop_summary` and
`overlay_projection_status_summary` before escalating to raw detailed outputs.

### Discovery

Explore available reducers:

```bash
sciona reducer list
sciona reducer --id module_overview --module-id pkg.mod
```

If node (module, classifier, callable) identifier is unknown:

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Available reducers:

The authoritative live catalog is:

```bash
sciona reducer list
sciona reducer info --id REDUCER_ID
```

Reducers are grouped by workflow category.

#### Category: structure

- `callable_overview` — Structural summary of a callable, including signature, location, and metadata. Use for quick callable inspection without retrieving full source.
- `classifier_inheritance` — Parsed base classifiers and inheritance relations. Use when reasoning about classifier hierarchy or polymorphic structure.
- `classifier_overview` — Structural summary of a classifier, including methods and metadata. Use for quick classifier inspection.
- `file_outline` — Structural outline of a file, including modules, classifiers, and callables. Use for navigation and symbol discovery.
- `module_overview` — Structural summary of a module, including contained classifiers and callables. Use for architectural inspection.
- `snapshot_provenance` — Snapshot provenance and reproducibility metadata for the committed SCI state. Use to verify snapshot freshness or identity before structural reasoning.
- `structural_index` — Canonical structural index of the codebase. Use for global structural reasoning or validation.
- `symbol_lookup` — Ranked structural symbol matches for a query. Use when resolving unknown identifiers.

```bash
sciona reducer --id callable_overview [--callable-id CALLABLE_ID]
sciona reducer --id classifier_inheritance [--classifier-id CLASSIFIER_ID]
sciona reducer --id classifier_overview [--classifier-id CLASSIFIER_ID]
sciona reducer --id file_outline [--module-id MODULE_ID] [--file-path FILE_PATH]
sciona reducer --id module_overview [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--include-file-map INCLUDE_FILE_MAP]
sciona reducer --id snapshot_provenance
sciona reducer --id structural_index
sciona reducer --id symbol_lookup [--query QUERY] [--kind KIND] [--limit LIMIT]
```

#### Category: relations

- `callsite_index` — Indexed caller/callee edges for a callable, including callsite details. Supports narrowing by identifier, status, provenance, and drop reason for targeted callsite analysis.
- `classifier_call_graph_summary` — Summary of call relationships within a classifier. Supports narrowing by caller or callee classifier for focused coupling analysis.
- `dependency_edges` — Explicit module import dependencies. Use for analysing module coupling or dependency graphs.
- `module_call_graph_summary` — Summary of call relationships within a module. Supports narrowing by source or target module for focused module-level flow analysis.
- `symbol_references` — Structural relationships (calls/imports) for matched symbols. Supports narrowing by symbol kind and module for impact analysis or dependency tracing.

```bash
sciona reducer --id callsite_index [--callable-id CALLABLE_ID] [--direction DIRECTION] [--detail-level DETAIL_LEVEL] [--include-callsite-diagnostics INCLUDE_CALLSITE_DIAGNOSTICS] [--identifier IDENTIFIER] [--status STATUS] [--provenance PROVENANCE] [--drop-reason DROP_REASON]
sciona reducer --id classifier_call_graph_summary [--classifier-id CLASSIFIER_ID] [--caller-id CALLER_ID] [--callee-id CALLEE_ID] [--top-k TOP_K]
sciona reducer --id dependency_edges [--module-id MODULE_ID] [--from-module-id FROM_MODULE_ID] [--to-module-id TO_MODULE_ID] [--query QUERY] [--edge-type EDGE_TYPE] [--direction DIRECTION] [--limit LIMIT]
sciona reducer --id module_call_graph_summary [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--from-module-id FROM_MODULE_ID] [--to-module-id TO_MODULE_ID] [--top-k TOP_K]
sciona reducer --id symbol_references [--query QUERY] [--kind KIND] [--module-id MODULE_ID] [--limit LIMIT]
```

#### Category: metrics

- `call_resolution_drop_summary` — Compact dropped-callsite triage summary grouped by reason, language, and scope. Use before raw `callsite_index` when the question is why calls are dropping.
- `call_resolution_quality` — Aggregated call-resolution quality diagnostics derived from callsite telemetry. Use to understand accepted vs dropped callsite distribution and dominant drop reasons.
- `fan_summary` — Fan-in/fan-out metrics for calls and imports. Supports narrowing by edge kind, node kind, and minimum fan threshold.
- `hotspot_summary` — Compressed summary of structurally significant or highly connected entities. Use for architectural orientation or complexity inspection.
- `overlay_impact_summary` — Advisory summary of dirty-worktree diff overlay impact for the committed snapshot. Use when triaging uncommitted changes; output is non-authoritative.
- `overlay_projection_status_summary` — Compact overlay trust surface showing which projections are patchable versus metadata-only under dirty worktree state.
- `resolution_trace` — Call-resolution diagnostics and sampled traces for one callable. Use to understand why callsites were accepted or dropped without changing `CALLS` truth.
- `structural_integrity_summary` — Structural integrity diagnostics over committed SCI facts. Use to detect duplicates, lexical orphans, and inheritance-cycle anomalies before downstream reasoning.

```bash
sciona reducer --id call_resolution_drop_summary [--limit LIMIT]
sciona reducer --id call_resolution_quality [--module-id MODULE_ID] [--language LANGUAGE] [--limit LIMIT]
sciona reducer --id fan_summary [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--module-id MODULE_ID] [--edge-kind EDGE_KIND] [--node-kind NODE_KIND] [--min-fan MIN_FAN] [--top-k TOP_K]
sciona reducer --id hotspot_summary
sciona reducer --id overlay_impact_summary
sciona reducer --id overlay_projection_status_summary
sciona reducer --id resolution_trace [--callable-id CALLABLE_ID] [--identifier IDENTIFIER] [--limit LIMIT]
sciona reducer --id structural_integrity_summary [--top-k TOP_K]
```

#### Category: source

- `callable_source` — Full source code of a callable. Use only when implementation details are required.
- `concatenated_source` — Concatenated source code for a selected scope (codebase, module, or classifier). Use for large-context reasoning or cross-entity inspection.

```bash
sciona reducer --id callable_source [--callable-id CALLABLE_ID]
sciona reducer --id concatenated_source [--scope SCOPE] [--module-id MODULE_ID] [--classifier-id CLASSIFIER_ID]
```
