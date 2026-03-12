<p align="left">
    <img src="assets/logo.jpg" alt="SCIONA logo" width="240">
</p>

### Deterministic structural context for LLM code assistants

In large, long-lived codebases we repeatedly observe the same pattern: LLM assistance initially improves productivity but gradually becomes inconsistent. Earlier assumptions drift and structural constraints are lost, and the model continues generating plausible responses that no longer reflect the actual code. **This is not primarily an LLM failure. It is a context stability problem.**

Many LLM tools address this using embeddings, semantic retrieval, dynamically assembled context, or extensive prompt and agent configuration. These approaches are powerful but difficult to reproduce and hard to constrain across long sessions or refactors. **SCIONA takes a deliberately different path: it provides a stable structural snapshot that downstream tools can rely on.**

SCIONA builds a **deterministic structural index (SCI)** for a *git* repository. The index is derived from the last committed source snapshot using [tree-sitter](https://tree-sitter.github.io/tree-sitter/) to extract structural relationships between code entities. The analysis is **static and source-only**, covering Python, Java, TypeScript, and JavaScript.

Rather than reconstructing repository structure heuristically, tools can query the SCI through **reducers**. A reducer is a deterministic query over the structural index that returns a reproducible payload for a given scope. Conceptually, SCIONA **compresses repository structure into deterministic facts** that tools can query directly instead of repeatedly reconstructing structure from raw source code. **SCIONA exposes repository structure as deterministic queries over a structural index.**

**SCIONA is intentionally limited in scope: it provides structure — not interpretation.** This deterministic representation is designed to anchor and stabilize LLM-assisted development workflows.

Although motivated by LLM-assisted workflows, SCIONA itself is **LLM-agnostic infrastructure**. Any tool that needs deterministic structural information about a repository can use it.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active%20development-orange)

## How SCIONA can be used

SCIONA is designed for workflows where tools must reliably reason about repository structure: grounding LLM code assistants, deterministic refactoring analysis, repository auditing and inspection, building code intelligence tools, stabilizing long-running agent workflows.

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows. **During initialization, SCIONA can auto-generate an `AGENTS.md` file in the repository root.** This file acts as a control surface for LLM copilots, specifying how SCIONA should be used during code reasoning. **In this mode, the copilot is instructed to use reducer outputs for structural reasoning within SCIONA’s scope, rather than reconstructing repository structure heuristically from source text.** Initialization can also install a post-commit hook that runs sciona build after each commit so SCIONA stays aligned with the latest committed repository state.

The `AGENTS.md` template is designed around several guiding principles:

- Structural grounding is mandatory where SCIONA applies.
- SCIONA insufficiency must be explicit.
- Other tools remain fully available for non-structural or out-of-scope questions.
- Fallback use is allowed after applicable SCIONA analysis is exhausted.
- Mixed evidence must be labeled.

This structure encourages deterministic structural reasoning while preserving flexibility for broader repository analysis.

## Quick start

```bash
# Install
pip install git+https://github.com/megascienta/sciona@vX.Y.Z

# Initialize in a repository
cd /path/to/repo
sciona init

# Build the structural index
sciona build

# Explore available structural queries
sciona reducer list

# SCIONA generates AGENTS.md so LLM assistants can reason over reducer outputs
```

## Sample output

```bash
sciona reducer --id module_overview --module-id sciona.src.sciona.cli
```

```json
{
    "reducer_id": "module_overview",
    "snapshot_id": "70f4e37607f082d0734d8fc56c1cf0c955fdfda8d26e5d57b989d3d6ef2ca0e3",
    "args": {
        "module_id": "163b1ca1dbdaaf4fe0520e532452ecf86c78d16b",
        "diff_mode": "full"
    },
    "payload": {
        "projection": "module_overview",
        "projection_version": "1.0",
        "payload_kind": "summary",
        "module_structural_id": "163b1ca1dbdaaf4fe0520e532452ecf86c78d16b",
        "module_qualified_name": "sciona.src.sciona.cli",
        "language": "python",
        "file_path": "src/sciona/cli/__init__.py",
        "line_span": [
            1,
            6
        ],
        "start_byte": 0,
        "end_byte": 122,
        "content_hash": "1a99edf7eba8b25dae1e89bb413c3160f5222d9c",
        "line_span_hash": "1a99edf7eba8b25dae1e89bb413c3160f5222d9c",
        "files": [
            "src/sciona/cli/__init__.py",
            "src/sciona/cli/commands/__init__.py",
            "src/sciona/cli/commands/register.py",
            "src/sciona/cli/commands/register_agents.py",
            "src/sciona/cli/commands/register_build.py",
            "src/sciona/cli/commands/register_hooks.py",
            "src/sciona/cli/commands/register_init.py",
            "src/sciona/cli/commands/register_status.py",
            "src/sciona/cli/commands/registry.py",
            "src/sciona/cli/errors.py",
            "src/sciona/cli/main.py",
            "src/sciona/cli/reducer.py",
            "src/sciona/cli/render.py",
            "src/sciona/cli/resolve.py",
            "src/sciona/cli/search.py",
            "src/sciona/cli/utils.py"
        ],
        "file_count": 16,
        "classifiers": [],
        "callables": [
            {
                "structural_id": "f9e42f13f8d5973ee061734d474f9d36240b210b",
                "qualified_name": "sciona.src.sciona.cli.commands.register.register"
            },
            {
                "structural_id": "aaa479c9bfbca4474abb90a5c467dcc1c9f3c9c9",
                "qualified_name": "sciona.src.sciona.cli.commands.register_agents.register_agents"
            },
...
```

## Supported languages

Built-in analyzers currently include **Python**, **Java**, **TypeScript** and **JavaScript**.  Indexed languages can be enabled during initialization or added later in `.sciona/config.yaml`.

## SCIONA workflow

```
Tracked source at committed snapshot
     ↓
Tree-sitter parsing
     ↓
Deterministic structural extraction
     ↓
Structural snapshot (SCI)
nodes • containment • imports • inheritance • implementation
     ↓
Derived artifact relations
call-sites • graph rollups • diagnostics
     ↓
Reducer
     ↓
CLI / LLM workflows / Agents
```

## Snapshot model

SCIONA indexes the **last committed snapshot**. Reducers are evaluated against that committed snapshot, not against uncommitted working tree state. If you change tracked source files, commit and run `sciona build` to refresh the snapshot before relying on reducer output. If your worktree is dirty, reducer output includes a _diff advisory payload describing affected scope. Treat this as a signal, not a structural fact. For authoritative results, commit and `sciona build` first.

## Documentation

- Contract: [`docs/CONTRACT.md`](docs/CONTRACT.md)
- Developer guide: [`docs/DEVELOPERGUIDE.md`](docs/DEVELOPERGUIDE.md)
- Generated capability manifest: [`docs/CAPABILITY_MANIFEST.json`](docs/CAPABILITY_MANIFEST.json)

## Structural Resolution and Build Performance

SCIONA has been validated on several large open-source repositories including **[VSCode](https://github.com/microsoft/vscode), [SymPy](https://github.com/sympy/sympy), [Guava](https://github.com/google/guava), [Webpack](https://github.com/webpack/webpack), [Airbyte](https://github.com/airbytehq/airbyte), and [NestJS](https://github.com/nestjs/nest)**. Validation reports and methodology details are available in [`validations/build_status_reports/`](validations/build_status_reports/).

The current published validation set covers **10 repositories** and should be
read as a snapshot-local callsite funnel plus pair-centric materialization:

- **297,596 observed syntactic callsites**
- **40,409 filtered before persistence**
- **257,187 persisted callsite observations**
- **251,493 persisted accepted**
- **5,694 persisted dropped**

That yields a **97.79% persisted acceptance rate** inside the persisted working
set, with an **86.42% observed-to-persisted retention rate** across the dataset.
Language-level persisted acceptance remains high: **98.46% for Java**,
**97.65% for JavaScript**, **98.21% for Python**, and **97.41% for
TypeScript**.

Pre-persist filtering is reported separately from persisted graph
materialization. Current published reports still reflect an earlier validation
snapshot, but current SCIONA status output reports:

- observed syntactic callsites
- filtered pre-persist out-of-scope buckets
- persisted `callsite_pairs`
- finalized `node_calls` edges

Wall-clock build times in this validation set range from **2.93 seconds**
(`axios`) to **645.94 seconds** (`vscode`), with a mean of **2.73 seconds per
1K structural nodes**.

These reports support claims about the observed-to-persisted funnel and current
pair/edge materialization. They do **not** claim theoretical callsite
completeness, runtime correctness, or recovery of dynamic dispatch. The
consolidated validation summary is in
[`validations/build_status_reports/summary.md`](validations/build_status_reports/summary.md).

## Project Status

SCIONA was developed as an internal tool at MegaScienta to support LLM-assisted development in large scientific and engineering repositories. It has been used in day-to-day workflows and validated on several large open-source codebases. The project is now released publicly to encourage broader experimentation and community feedback. While the core architecture is stable and actively used, additional validation across diverse repositories and workflows is ongoing. *Issues, discussions, and field experience reports are very welcome.*

## Project Governance

SCIONA is developed and maintained by Dmitry Chigrin as part of independent research and engineering under the MegaScienta brand. Development combined conventional tooling with LLM-assisted programming; as the project matured, SCIONA was routinely used to anchor LLM reasoning over its own repository.

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

## Reducers usage

Reducers are the primary interface for structural queries. Each reducer takes a scope (callable, classifier, module, or global) and returns a deterministic structured payload.

### Discovery

Explore available reducers:

```bash
sciona reducer list
```

```bash
sciona reducer --id module_overview --module-id pkg.mod
```

If node (module, classifier, callable) identifier is unknown:

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
```

```bash
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Available reducers:

The authoritative live catalog is:

```bash
sciona reducer list
```

```bash
sciona reducer info --id REDUCER_ID
```

Reducers are grouped by workflow category.

Reducers that advertise `Compact: yes` should usually be tried in compact mode first for orientation, ownership, coupling, and triage workflows.

#### Category: orientation

`hotspot_summary` - Compressed summary of structurally significant or highly connected entities. Use for architectural orientation or complexity inspection.

```bash
sciona reducer --id hotspot_summary
```

`module_overview` - Structural summary of a module, including contained classifiers and callables. Use for architectural inspection.

```bash
sciona reducer --id module_overview [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--include-file-map INCLUDE_FILE_MAP] [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K]

`snapshot_provenance` - Snapshot provenance and reproducibility metadata for the committed SCI state. Use to verify snapshot freshness/identity before structural reasoning.

```bash
sciona reducer --id snapshot_provenance
```

`structural_index` - Canonical structural index of the codebase. Use for global structural reasoning or validation.

```bash
sciona reducer --id structural_index [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K]

#### Category: navigation

`file_outline` - Structural outline of a file, including modules, classifiers, and callables. Use for navigation and symbol discovery.

```bash
sciona reducer --id file_outline [--module-id MODULE_ID] [--file-path FILE_PATH] [--compact COMPACT] [--depth DEPTH]
```

Compact: `--compact` [`--depth` DEPTH]

`symbol_lookup` - Ranked structural symbol matches for a query. Use when resolving unknown identifiers.

```bash
sciona reducer --id symbol_lookup [--query QUERY] [--kind KIND] [--limit LIMIT]
```

#### Category: coupling

`classifier_call_graph_summary` - Summarize classifier-level artifact call relationships for the committed snapshot, with optional narrowing by caller or callee classifier.

```bash
sciona reducer --id classifier_call_graph_summary [--classifier-id CLASSIFIER_ID] [--caller-id CALLER_ID] [--callee-id CALLEE_ID] [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K]

`dependency_edges` - Explicit module import dependencies. Use for analysing module coupling or dependency graphs. `direction='in'` or `direction='out'` scopes `module_id` filters.

```bash
sciona reducer --id dependency_edges [--module-id MODULE_ID] [--from-module-id FROM_MODULE_ID] [--to-module-id TO_MODULE_ID] [--query QUERY] [--edge-type EDGE_TYPE] [--direction DIRECTION] [--limit LIMIT] [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K] [`--limit` LIMIT]

`fan_summary` - Summarize fan-in and fan-out over reducer-facing graph edges, with optional narrowing by edge kind, node kind, and minimum fan threshold.

```bash
sciona reducer --id fan_summary [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--module-id MODULE_ID] [--edge-kind EDGE_KIND] [--min-fan MIN_FAN] [--node-kind NODE_KIND] [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K]

`import_migration_impact` - Migration-oriented import impact summary for a module or package. Highlights importers, dependencies, and wrapper pressure.

```bash
sciona reducer --id import_migration_impact [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--top-k TOP_K]
```

`module_call_graph_summary` - Summarize module-to-module artifact call relationships for the committed snapshot, with optional narrowing by caller or callee module.

```bash
sciona reducer --id module_call_graph_summary [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--from-module-id FROM_MODULE_ID] [--to-module-id TO_MODULE_ID] [--compact COMPACT] [--top-k TOP_K]
```

Compact: `--compact` [`--top-k` TOP_K]

`ownership_summary` - Compact ownership summary for a module or package. Returns top submodules plus top internal/external dependencies and dependents.

```bash
sciona reducer --id ownership_summary [--module-id MODULE_ID] [--callable-id CALLABLE_ID] [--classifier-id CLASSIFIER_ID] [--top-k TOP_K]
```

#### Category: symbol

`callable_overview` - Structural summary of a callable, including signature, location, and metadata. Use for quick callable inspection without retrieving full source.

```bash
sciona reducer --id callable_overview [--callable-id CALLABLE_ID]
```

`callsite_pairs_index` - List persisted artifact-layer callsite candidate pairs for a callable, with optional narrowing by identifier. `detail_level='neighbors'` returns caller/callee sets.

```bash
sciona reducer --id callsite_pairs_index [--callable-id CALLABLE_ID] [--direction DIRECTION] [--detail-level DETAIL_LEVEL] [--include-callsite-diagnostics INCLUDE_CALLSITE_DIAGNOSTICS] [--identifier IDENTIFIER] [--compact COMPACT]
```

Compact: `--compact`

`classifier_inheritance` - Parsed base classifiers and inheritance relations. Use when reasoning about classifier hierarchy or polymorphic structure.

```bash
sciona reducer --id classifier_inheritance [--classifier-id CLASSIFIER_ID]
```

`classifier_overview` - Structural summary of a classifier, including methods and metadata. Use for quick classifier inspection.

```bash
sciona reducer --id classifier_overview [--classifier-id CLASSIFIER_ID]
```

`symbol_references` - Summarize structural symbol references in the committed snapshot, with optional narrowing by symbol kind or module.

```bash
sciona reducer --id symbol_references [--query QUERY] [--kind KIND] [--module-id MODULE_ID] [--limit LIMIT]
```

#### Category: diagnostic

`call_resolution_drop_summary` - Summarize artifact-layer dropped callsite outcomes by reason, language, and scope for fast call-resolution triage.

```bash
sciona reducer --id call_resolution_drop_summary [--limit LIMIT]
```

`call_resolution_quality` - Aggregated call-resolution quality diagnostics derived from callsite telemetry. Use to understand accepted vs dropped callsite distribution and dominant drop reasons.

```bash
sciona reducer --id call_resolution_quality [--module-id MODULE_ID] [--language LANGUAGE] [--limit LIMIT] [--compact COMPACT]
```

Compact: `--compact` [`--limit` LIMIT]

`resolution_trace` - Call-resolution diagnostics and sampled traces for one callable. Use to understand why callsites were accepted or dropped without changing `CALLS` truth.

```bash
sciona reducer --id resolution_trace [--callable-id CALLABLE_ID] [--identifier IDENTIFIER] [--limit LIMIT]
```

`structural_integrity_summary` - Structural integrity diagnostics over committed SCI facts. Use to detect duplicates, lexical orphans, and inheritance-cycle anomalies before downstream reasoning.

```bash
sciona reducer --id structural_integrity_summary [--top-k TOP_K]
```

#### Category: overlay

`overlay_impact_summary` - Advisory summary of dirty-worktree diff overlay impact for the committed snapshot. Use when triaging uncommitted changes; output is non-authoritative.

```bash
sciona reducer --id overlay_impact_summary
```

`overlay_projection_status_summary` - Summarize dirty-worktree overlay support by reducer projection, including patchable versus metadata-only behavior.

```bash
sciona reducer --id overlay_projection_status_summary
```

#### Category: source

`callable_source` - Full source code of a callable. Use only when implementation details are required.

```bash
sciona reducer --id callable_source [--callable-id CALLABLE_ID]
```

`concatenated_source` - Concatenated source code for a selected scope (codebase/module/classifier). Use for large-context reasoning or cross-entity inspection.

```bash
sciona reducer --id concatenated_source [--scope SCOPE] [--module-id MODULE_ID] [--classifier-id CLASSIFIER_ID]
```
