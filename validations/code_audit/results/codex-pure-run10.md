## Model

- GPT-5.2-Codex Copilot / VS Code

## Prompt

This is a clean thread. No prior knowledge is allowed.

You are performing a pre-release code audit.

Documentation is located in docs/.

Analyze the codebase and report:

– Critical misalignments with documented principles or contracts
– Structural design problems
– Potential security-relevant issues

Reference specific files and methods where applicable.

## Results

- worked for 3m 16s
- explored 25 files, 9 searches, 2 lists

Here’s a pre‑release audit focused on contract alignment, structural design risks, and security‑relevant issues. I didn’t run tests.

**Critical Misalignments With Documented Principles/Contracts**
- Contract forbids identical parent/child spans for `LEXICALLY_CONTAINS`, but `_validate_lexical_containment` explicitly allows identical spans when the parent is `module`. This contradicts “Parent and child source spans MUST NOT be identical” in `docs/CONTRACT.md`. File: `src/sciona/code_analysis/core/structural_assembler.py#L107` (see `module_parent_identical_span` handling at `src/sciona/code_analysis/core/structural_assembler.py#L147`).
- Contract requires “Structural extraction MUST fail closed for unsupported query node types” and forbids heuristic traversal fallbacks. Current walkers traverse *all* direct named children and even unwrap non‑structural wrapper nodes, which is a fail‑open/heuristic approach. Files: `src/sciona/code_analysis/core/extract/parsing/query_helpers.py#L85` (returns all named children), `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py#L622`, and `src/sciona/code_analysis/languages/builtin/python/python_nodes.py#L65`.
- Contract mandates stable ordering by module path then qualified name. Ingestion sorts nodes by `(node_type, qualified_name)` instead, which is deterministic but not per contract‑specified order. File: `src/sciona/code_analysis/core/structural_assembler.py#L84`.

**Structural Design Problems**
- Tree traversal is largely unbounded by query surfaces: `find_direct_children_query(...)` ignores `language_name` and returns all named children, then walkers recurse into them. This design makes extraction behavior sensitive to tree‑sitter grammar changes and violates the “query/field driven” intent by effectively walking the full AST (no explicit enforcement that only supported structural node types are reachable). Files: `src/sciona/code_analysis/core/extract/parsing/query_helpers.py#L85`, `src/sciona/code_analysis/languages/builtin/typescript/typescript_node_walk.py#L622`.
- Python extraction explicitly unwraps one level of wrapper statements to find structural nodes (`_python_structural_children_from_body`). This is a heuristic traversal that bypasses the “fail closed” contract and makes extraction results depend on incidental wrapper node shapes. File: `src/sciona/code_analysis/languages/builtin/python/python_nodes.py#L65`.

**Potential Security‑Relevant Issues**
- SQLite connections use a URI built from `db_path.as_posix()` without escaping. If a repository path contains `?` or `#`, SQLite will interpret it as a URI query/fragment, potentially altering connection parameters (e.g., mode) or truncating the path. This is a classic URI‑injection risk for path‑derived database locations. File: `src/sciona/data_storage/connections.py#L40`.

If you want, I can propose concrete fixes for each finding or run `pytest -q` in the `multiphysics` conda env.