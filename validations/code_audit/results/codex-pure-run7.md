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

- worked for 5m 35s
- explored 39 files, 23 searches, 2 lists

**Critical Misalignments With Documented Principles/Contracts**

1. Python nested functions inside class methods are misclassified as class methods, violating the contract’s “nested named defs map to callable with role `nested`” rule and lexical containment semantics. In `walk_python_nodes` the function-definition branch checks `state.class_stack` before `state.callable_stack`, so a function declared inside a method is attached to the class (role `declared`) instead of the enclosing callable (role `nested`). This also affects bound-lambda assignments inside methods for the same reason.  
File: `src/sciona/code_analysis/languages/builtin/python/python_nodes.py` (function `walk_python_nodes`).

2. Calls inside bound Python lambdas are misattributed to the outer callable because `ScopeResolver` never recognizes `lambda` nodes as structural callables. `scope_resolver_from_pending_calls` stores spans for lambda nodes (parent of lambda bodies), but `STRUCTURAL_CALLABLE_NODE_TYPES` omits `lambda`, so the resolver skips them and walks to the next enclosing callable. This violates the contract’s “calls attributed to nearest enclosing structural callable” rule for bound lambdas (which are structural callables).  
Files: `src/sciona/code_analysis/languages/common/scope_resolver.py` (constant `STRUCTURAL_CALLABLE_NODE_TYPES`) and `src/sciona/code_analysis/languages/builtin/python/python_nodes.py` (lambda-bound callable emission in `walk_python_nodes`).

**Structural Design Problems**

1. Local inheritance edge emission is name-based and ignores qualification, so `pkg.Base` can incorrectly resolve to a local `Base` type and emit `EXTENDS/IMPLEMENTS` edges that do not reflect the direct syntax-level declaration. This risks false edges and contradicts the intent of “direct syntax-level base declarations only” by applying a simplistic local name resolution step.  
File: `src/sciona/code_analysis/languages/common/analyzer_support.py` (function `emit_local_inheritance_edges`).

**Potential Security-Relevant Issues**

1. Profile introspection reads files via `Path(root_key) / relative_path` without validating that the path is repo-relative and contained within the repo root. If `relative_path` is absolute or contains traversal (e.g., `../`), this can read arbitrary files. Even if today the DB is trusted, this is a latent file-read primitive if the DB or inputs are compromised.  
Files: `src/sciona/code_analysis/tools/profile_introspection_cache.py` (`_python_inspector_cached`, `_typescript_inspector_cached`, `_javascript_inspector_cached`, `_java_inspector_cached`).

**Tests**
- Not run (audit only).

If you want, I can propose fixes or implement corrections for the Python misclassifications and the lambda scope attribution first.