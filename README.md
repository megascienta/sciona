<p align="left">
    <img src="assets/logo.jpg" alt="SCIONA logo" width="275">
</p>

## Deterministic structural context for code assistants

In large, long-lived repositories, LLM assistance often follows the same pattern: it starts useful, then gradually becomes inconsistent. Earlier assumptions drift, structural constraints disappear, and the model continues producing plausible answers that no longer reflect the actual code.

**This is usually not an LLM failure. It is a context stability problem.**

Most tooling addresses this through embeddings, semantic retrieval, or dynamically assembled prompts. These approaches are powerful, but they can be difficult to reproduce and hard to constrain over long sessions or large refactors.

**SCIONA takes a different approach.**

SCIONA builds a **deterministic structural index (SCI)** for a Git repository. The index is derived from the last committed snapshot using [tree-sitter](https://tree-sitter.github.io/tree-sitter/) to extract structural relationships between code entities. The analysis is static and source-only, currently supporting **Python**, **Java**, **TypeScript**, and **JavaScript**.

Instead of repeatedly reconstructing repository structure from source files or prompt context, tools can query the SCI through reducers. A **reducer** is a deterministic structural query that returns a reproducible payload for a given scope. In effect, SCIONA converts repository structure into **stable structural evidence** that tools can query directly.

**SCIONA intentionally provides structure — not interpretation.**

It is designed to answer structural questions: where symbols live, how code is organized, what imports what, which call relationships are observed, and which parts of the repository are structurally in scope.

It does not try to prove runtime behavior, infer semantic intent, validate business logic, or replace tests. Those remain the responsibility of normal source inspection, execution, and validation.

Although motivated by LLM workflows, SCIONA itself is LLM-agnostic infrastructure. Any system that needs deterministic structural information about a repository can use it.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Quick start

Requirements:
- Python 3.11, 3.12, or 3.13
- Git

Install SCIONA from the GitHub release:
```bash
pip install git+https://github.com/megascienta/sciona@v1.2.3
```

Initialize SCIONA in a repository:
```bash
cd /path/to/repo
sciona init
```

Initialization creates a .sciona/ folder and configuration.

During interactive setup, SCIONA can also configure coding-agent protocol files:

```bash
Generate a managed SCIONA block in AGENTS.md? [y/N]:
Configure Claude Code for SCIONA (CLAUDE.md + .claude/settings.json)? [y/N]:
```

Both configurations can also be performed independently with `sciona agents` and `sciona claude`.

Build the structural index:
```bash
sciona build
```
This parses the last committed repository snapshot and constructs the Structural Code Index (SCI).

Explore available structural queries:
```bash
sciona reducer list
```

## How SCIONA can be used

SCIONA is not a semantic code search engine, chat layer, or autonomous coding agent. It is a deterministic structural evidence layer that other tools and agents can use before making claims about repository structure. SCIONA is intended for workflows where tools must reason about **repository structure** reliably.

Typical use cases include:

- grounding LLM code assistants
- performing deterministic repository audits
- stabilizing long-running agent workflows
- supporting architecture and blast-radius analysis
- building code intelligence tooling on top of reproducible structural data

SCIONA can be used directly through its CLI, but it becomes most powerful when integrated into LLM-assisted development workflows.

During initialization, SCIONA can generate agent setup files in the repository root:

- `AGENTS.md` for Codex and compatible agent frameworks
- `CLAUDE.md` for Claude Code
- `.claude/settings.json` permission rules for Claude Code command execution

These files instruct coding agents to use SCIONA reducers for structural questions: symbol lookup, ownership, dependency edges, call relationships, source slices, reducer summaries, and blast-radius analysis.

Semantic, runtime, documentation, and validation questions remain outside SCIONA’s scope and should be handled with normal source inspection, execution, tests, and conventional tooling.

## Structural model

### SCIONA workflow

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
Derived structural relations
call-sites • graph rollups • diagnostics
     ↓
Reducer
     ↓
CLI / LLM workflows / Agents
```

### Snapshot model

SCIONA indexes the **last committed snapshot**. Reducers are evaluated against that committed snapshot, not against uncommitted working tree state. If you change tracked source files, commit and run `sciona build` to refresh the snapshot before relying on reducer output. If your worktree is dirty, reducer output includes a `_diff_overlay` advisory payload describing affected scope. Treat this as an advisory, not structural evidence. For authoritative results, commit and `sciona build` first.

### Supported languages
Python, Java, TypeScript, JavaScript. Indexed languages can be enabled or disabled in `.sciona/config.yaml`.

## Querying the structural index

Reducers are the primary interface for structural queries.

### Discover available reducers

```bash
sciona reducer list
```

```bash
sciona reducer info --id REDUCER_ID
```

### Search for identifiers

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
```

```bash
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Example reducer output

```bash
sciona reducer --id module_overview --module-id sciona.src.sciona.cli
```

Reducers return deterministic JSON payloads describing structural scope.

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
            "..."
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
        "...": "output truncated"
```

## Validation

The following sections summarize validation results across open-source repositories and real development workflows.

### Structural Resolution and Build Performance

SCIONA has been validated against a diverse set of open-source repositories spanning multiple languages, sizes, and architectural styles, including [Airbyte](https://github.com/airbytehq/airbyte), [Commons Lang](https://github.com/apache/commons-lang), [ESLint](https://github.com/eslint/eslint), [Guava](https://github.com/google/guava), [NodeBB](https://github.com/nodebb/nodebb), [npm/cli](https://github.com/npm/cli), [Pydantic](https://github.com/pydantic/pydantic), [Rollup](https://github.com/rollup), [SymPy](https://github.com/sympy/sympy), [VSCode](https://github.com/microsoft/vscode), and [Webpack](https://github.com/webpack/webpack).

**Takeaway:** Nodes and calls resolution remains robust across repositories and languages with very different structural characteristics, while build cost scales with structural size.

Observed patterns:

- **Predictable structural scaling.** Build time grows with structural size measured as nodes plus edges. Across the evaluated repositories, build times range from a few seconds for small projects to several minutes for very large codebases. Normalizing by structural size shows that build cost remains stable across repositories with a mean of 1.5 seconds per 1K nodes+edges.

- **Stable pipeline composition.** For most repositories, the majority of build time is spent in structural extraction and call observation stages and remains consistent across projects.

- **High callsite accountability.** In repositories where most calls remain within repository scope, accepted callees typically cover more than 90% of observed syntactic callsites. Lower acceptance rates arise primarily when many calls target external or otherwise out-of-scope code, which is filtered before persistence rather than silently misresolved.

- **Clear language-level differences.** Static languages show the highest acceptance rates: Java resolves about 95.0% of 44,010 observed callsites, and TypeScript about 95.5% of 157,699. JavaScript resolves about 74.5% of 25,016 callsites, while Python resolves about 85.6% of 82,203. The lower acceptance rates for dynamic languages are driven primarily by higher filtering due to dynamic dispatch patterns and calls to external or stdlib code.

- **Code vs. test behavior.** Filtering rates are consistently higher in test code than in production code. Test suites frequently rely on dynamic fixtures, mocking frameworks, and calls into external libraries, which naturally fall outside the repository's structural scope.

Validation reports, plots, and methodology are available in [`validations/build_status_reports/`](validations/build_status_reports/).

### Copilot evaluation

A 40-task development session was conducted using Codex (GPT-5.4) as the copilot on SCIONA’s own repository. Tasks included architecture reviews, semantic investigations, implementation, and repository maintenance. The session followed a realistic development workflow: audits, follow-up analysis, planning, implementation, and post-change verification rather than isolated prompts.

**Takeaway:** SCIONA proved most useful for structural triage and scope control, and much less for semantic or runtime questions that required direct source inspection. Across the 40 tasks, SCIONA primarily increased **confidence and scope clarity**, while pure time savings were smaller. This matches the intended role of the tool: deterministic structural grounding rather than semantic interpretation.

Observed patterns:

- **Structural orientation:** Reducers were most valuable during architecture audits and early investigation, surfacing ownership, coupling hubs, and integrity anomalies before source inspection. The most-used reducers were ownership_summary, fan_summary, and structural_integrity_summary, consistent with a workflow centered on architecture triage and scope control.
- **Scope reduction:** Structural evidence narrowed edit scope and helped identify high-impact modules and helper chokepoints.
- **Post-change verification:** Re-running reducers after implementation provided quick confirmation that structural issues were resolved.
- **Limits:** Algorithm logic, parser behavior, runtime semantics, documentation correctness, and test validation still required direct source inspection and conventional tooling, outside SCIONA’s structural scope.

Detailed task notes, prompts, and session reports are available in [`validations/copilot_evaluation/`](validations/copilot_evaluation/).

## Project documentation

- Contract: [`docs/CONTRACT.md`](docs/CONTRACT.md)
- Developer guide: [`docs/DEVELOPERGUIDE.md`](docs/DEVELOPERGUIDE.md)
- Generated capability manifest: [`docs/CAPABILITY_MANIFEST.json`](docs/CAPABILITY_MANIFEST.json)

## Governance

SCIONA is developed and maintained by [PD Dr. Dmitry Chigrin](https://www.linkedin.com/in/pd-dr-dmitry-chigrin-4350891/) as part of independent research and engineering under the [MegaScienta](https://www.megascienta.com) brand. Development combined conventional tooling with LLM-assisted programming. As the project matured, SCIONA was routinely used to anchor LLM reasoning over its own repository.
