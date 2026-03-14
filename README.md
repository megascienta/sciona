<p align="left">
    <img src="assets/logo.jpg" alt="SCIONA logo" width="275">
</p>

### Deterministic structural context for code assistants

In large, long-lived codebases we repeatedly observe the same pattern: LLM assistance initially improves productivity but gradually becomes inconsistent. Earlier assumptions drift, structural constraints are lost, and the model continues generating plausible responses that no longer reflect the actual code. **This is not primarily an LLM failure. It is a context stability problem.**

Many LLM tools address this using embeddings, semantic retrieval, dynamically assembled context, or extensive prompt and agent configuration. These approaches are powerful but difficult to reproduce and hard to constrain across long sessions or refactors. **SCIONA takes a deliberately different path: it provides a stable structural code snapshot that downstream tools can rely on.**

SCIONA builds a **deterministic structural index (SCI)** for a *git* repository. The index is derived from the last committed source snapshot using [tree-sitter](https://tree-sitter.github.io/tree-sitter/) to extract structural relationships between code entities. The analysis is **static and source-only**, covering Python, Java, TypeScript, and JavaScript.

Rather than reconstructing repository structure heuristically, tools can query the SCI through **reducers**. A reducer is a deterministic query over the structural index that returns a reproducible payload for a given scope. Conceptually, SCIONA **compresses repository structure into deterministic facts** that tools can query directly instead of repeatedly reconstructing structure from raw source code. **SCIONA exposes repository structure as deterministic queries over a structural index.**

**SCIONA is intentionally limited in scope: it provides structure — not interpretation.** This deterministic representation is designed to anchor and stabilize LLM-assisted development workflows.

Although motivated by LLM-assisted workflows, SCIONA itself is **LLM-agnostic infrastructure**. Any tool that needs deterministic structural information about a repository can use it.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active%20development-orange)

## How SCIONA can be used

SCIONA is designed for workflows where tools must reliably reason about repository structure: grounding LLM code assistants, deterministic refactoring analysis, repository auditing and inspection, building code intelligence tools, stabilizing long-running agent workflows.

SCIONA can be used directly via its CLI or integrated into LLM-assisted workflows. **During initialization, SCIONA can auto-generate an `AGENTS.md` file in the repository root.** This file acts as a control surface for LLM copilots, specifying how SCIONA should be used during code reasoning. Initialization can also install a post-commit hook that runs `sciona build` after each commit so SCIONA stays aligned with the latest committed repository state.

The generated `AGENTS.md` is not just a high-level recommendation. It defines an operational protocol for agent reasoning:

- Mixed questions must be decomposed into structural and non-structural sub-questions.
- Structural questions within SCIONA scope must use reducers first; agents must not reconstruct structure heuristically from source text while relevant reducer categories remain untried.
- Non-structural and out-of-scope questions may use normal repository inspection directly.
- If SCIONA is insufficient for part of a structural question, the missing structural fact must be stated explicitly before falling back.
- Fallback evidence and mixed evidence should be labeled explicitly, separating SCIONA-grounded claims from non-SCIONA reasoning.
- Once structural boundaries are established, agents are expected to switch to source inspection, tests, docs, or other tools for semantic, runtime, and validation work.

This protocol is designed to keep structural reasoning deterministic without preventing broader repository analysis where SCIONA does not apply.

## Quick start

```bash
# Install
pip install git+https://github.com/megascienta/sciona@v1.0.0

# Initialize in a repository
cd /path/to/repo
sciona init

# Build the structural index
sciona build

# Explore available structural queries
sciona reducer list

# SCIONA generates AGENTS.md so LLM assistants can reason over reducer outputs
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

SCIONA has been validated against 10 open-source repositories spanning a wide range of sizes, languages, and structures: [Airbyte](https://github.com/airbytehq/airbyte), [Axios](https://github.com/axios/axios), [Commons Lang](https://github.com/apache/commons-lang), [FastAPI](https://github.com/fastapi/fastapi), [Guava](https://github.com/google/guava), [NestJS](https://github.com/nestjs/nest), [Pydantic](https://github.com/pydantic/pydantic), [SymPy](https://github.com/sympy/sympy), [VSCode](https://github.com/microsoft/vscode), and [Webpack](https://github.com/webpack/webpack).

Takeaway: build cost scales with structural size, and call resolution remains high-accountability even on large or test-heavy repositories.

- **Scale.** The corpus ranges from 576 nodes and a 3-second build (Axios) to 108k nodes and 11 minutes (VSCode), covering roughly three orders of magnitude in codebase size. Build time scales predictably with structural complexity; the dominant cost is parsing and indexing source structure
followed by resolving call relationships.
- **Callsite resolution.** Using accepted in-repo callees as a share of observed syntactic callsites, repos where most calls stay in-repo land at 91–95% (Commons Lang, Guava, Airbyte, Webpack, VSCode). Lower overall values in FastAPI (31%), SymPy (65%), and Pydantic (70%) are driven by test suites that call heavily into external or unindexed code. Non-test accepted-call yield in those three repos remains materially higher, at 61–82% when measured against observed callsites and 98–100% when measured against persisted in-scope callsites. This is expected for test-heavy external-call patterns, not signal loss.
- **Determinism.** FastAPI, Pydantic, and SymPy resolve every persisted callsite to exactly one callee. In the remaining repos, multi-callee resolution exists but is usually rare and bounded: Airbyte, Axios, Commons Lang, and Webpack show only small pockets of multi-pair expansion, while Guava and NestJS reach bounded maxima of 34 and 16 candidates respectively due to overloads and interface dispatch. VSCode's TypeScript codebase has a single extreme outlier callsite with 1,253 candidates, a known pattern in large generated interface hierarchies, but multi-callee callsites still affect under 2% of persisted callsites overall. Callsite conservation holds throughout the pipeline in all published reports.
- **Inflation detection.** Webpack's test corpus (8,700+ files, 84% with ≤1 node) triggers SCIONA's inflation warning, correctly identifying that file count is dominated by minimal fixture files rather than substantial source. The warning exists to surface that structural characteristic; it does not invalidate the indexed source figures.

Validation reports and methodology are in [`validations/build_status_reports/`](validations/build_status_reports/).

## Copilot Evaluation Session

A 40-task evaluation session was conducted using Codex (GPT-5.4) as the copilotagent on SCIONA's own codebase, covering architecture reviews, semantic investigations, implementation tasks, and repository maintenance. The session was structured as a realistic development workflow: audits, follow-ups, planning, implementation, and re-audits rather than isolated test prompts. This was an internal evaluation on SCIONA's own repository, so the results are informative rather than blinded.

Takeaway: SCIONA helped most with structural triage and scope control, and much less with semantic or runtime questions that required direct source inspection.

- **Where it helped most.** In the 31 task blocks with active SCIONA queries, average usefulness was 7.9/10, versus 5.9/10 in task blocks without active querying. Architecture review was the highest-value category: SCIONA reduced search space early and surfaced ownership, coupling concentration, and integrity anomalies before source reading. Semantic investigations also scored well, with scope reduction averaging 6.8/10. The most frequently used reducers were `ownership_summary`, `fan_summary`, and `structural_integrity_summary`.
- **Where it reached its limit.** Semantic correctness, algorithm logic, and parser behavior still required direct source inspection. Implementation tasks scored lower on scope reduction (5.7) and time saved (4.6) than reviews, not because SCIONA was absent, but because many later edits reused structural context established earlier instead of requiring fresh queries. In those blocks, SCIONA mainly provided confidence in scope boundaries.
- **Friction.** Query friction stayed low across the session at 2.9/10 on a scale where 1 is frictionless, and it decreased between the first and second audit cycles as the copilot became more familiar with the reducer surface.
- **Overall.** Average net usefulness versus a baseline workflow was 7.0/10 across all 40 tasks. The session included one confirmed bug fix (call-resolution stats overcounting), one behavioral change (fail-closed engine semantics), multiple structural refactors informed by SCIONA evidence, and two full pre-release audits where SCIONA materially reduced required source reading.

The copilot experiment prompts, full report of the session and memo are in [`validations/copilot_evaluation/`](validations/copilot_evaluation/).

## Installation

Requirements:
- Python 3.11 or 3.12 (Python 3.13 is not supported yet)
- Git (for cloning and for snapshot metadata)
- `pip` (or another PEP 517 installer)

Default install (from GitHub release tag):

```bash
pip install git+https://github.com/megascienta/sciona@v1.0.0
```
or for a given relase tag:

```bash
pip install git+https://github.com/megascienta/sciona@v<release-tag>
```

```bash
pip install git+https://github.com/megascienta/sciona@v<release-tag>
```

Install development version with dependencies and run tests:

```bash
git clone https://github.com/megascienta/sciona
cd sciona
pip install -e ".[dev]"
pytest -q
```

## Reducers usage

Reducers are the primary interface for structural queries and returns a deterministic structured payload.

### Reducers discovery

```bash
sciona reducer list
```

```bash
sciona reducer info --id REDUCER_ID
```

### Nodes discovery

```bash
sciona search QUERY [--kind KIND] [--limit LIMIT] [--json]
```

```bash
sciona resolve IDENTIFIER [--kind KIND] [--limit LIMIT] [--json]
```

### Example of reducer output

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
        ...
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

## Project Governance

SCIONA is developed and maintained by Dmitry Chigrin as part of independent research and engineering under the MegaScienta brand. Development combined conventional tooling with LLM-assisted programming; as the project matured, SCIONA was routinely used to anchor LLM reasoning over its own repository.