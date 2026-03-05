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

- worked for 6m 1s
- explored 35 files, 21 searches, 2 lists

**Critical Misalignments**
1. **Lexical span rule violation** in `src/sciona/code_analysis/core/structural_assembler.py` (`_validate_lexical_containment`). The code explicitly allows identical parent/child spans when the parent is a module (`module_parent_identical_span`). The contract forbids identical spans for *any* parent/child pair. This is a direct contract breach and can admit invalid lexical containment.
2. **Heuristic traversal fallback in Python extraction** in `src/sciona/code_analysis/languages/builtin/python/python_nodes.py` (`_python_structural_children_from_body`, `walk_python_nodes`). The logic unwraps non-structural statements and recursively traverses into them, which is a heuristic fallback. The contract states “no heuristic traversal fallback” and “fail closed for unsupported query node types.” This behavior contradicts that requirement.

**Structural Design Problems**
1. **Core `CALLS` resolution is file-local** in `src/sciona/code_analysis/core/structural_assembler.py` (`_normalize_call_records`). The symbol index and import targets are built from `analysis.nodes`/`analysis.edges` for a single file, so cross-file call targets cannot be resolved in CoreDB. This undermines the contract’s in-repo `CALLS` expectation and the documented resolution stages. Recommend a snapshot-wide symbol index or a second pass after all files are ingested.
2. **Inheritance edge inference can misattribute bases** in `src/sciona/code_analysis/languages/common/analyzer_support.py` (`emit_local_inheritance_edges`). It uses simple-name matching within the same file and does not preserve `extends` vs `implements` clause semantics from the source AST. This can create incorrect `EXTENDS`/`IMPLEMENTS` edges when a local class shares a name with an imported base or when heritage clauses mix extends/implements. Consider emitting clause-typed edges directly in language adapters or storing clause metadata for later resolution.

**Potential Security-Relevant Issues**
1. **SQLite URI path injection surface** in `src/sciona/data_storage/connections.py` (`_base_connect`). The URI is built by concatenating `db_path.as_posix()` into `file:{path}?mode=...` with `uri=True`. If the repo path contains `?` or `#`, SQLite treats it as part of the URI query/fragment, which can alter the DB path or options. Mitigation: avoid URI mode for normal paths or percent-encode the path before URI construction.
2. **`git hash-object --stdin-paths` path trust** in `src/sciona/runtime/git/ops.py` (`blob_sha_batch`). Paths are taken from git output and only checked for newline/null, not for `..` segments or absolute paths. If a malformed index entry is present, it could hash files outside the repo. Mitigation: normalize and reject paths that are not strictly within the repo root.

I didn’t run tests as this is an audit-only pass. If you want, I can propose concrete fixes or add contract-alignment tests next.