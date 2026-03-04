# Code Analysis Capability Matrix

This matrix tracks language-parity expectations for `src/sciona/code_analysis/`.
It is scoped to static tree-sitter-driven extraction and contract-compatible
normalization.

Executable source of truth:
- `src/sciona/code_analysis/core/extract/languages/parity_contract.py`

Legend:
- `yes`: implemented and test-covered
- `partial`: implemented with scoped limitations documented below
- `n/a`: intentionally not applicable

| Capability | Python | TypeScript | Java | Notes / Coverage |
|---|---|---|---|---|
| Module node emission | yes | yes | yes | Contract baseline |
| Type node emission | yes | yes | yes | Includes nested/local named classes |
| Callable node emission (declared/nested/bound/constructor) | yes | yes | yes | Java has no module-level callable declarations outside types |
| `LEXICALLY_CONTAINS` edges | yes | yes | yes | Deterministic lexical tree |
| `EXTENDS` edges | yes | yes | yes | Direct syntax-level inheritance only |
| `IMPLEMENTS` edges | n/a | yes | yes | Direct syntax-level interface implementation only |
| `IMPORTS_DECLARED` extraction | yes | yes | yes | Syntax-only, internal targets only |
| Import aliases / member aliases | yes | yes | yes | Language-local alias/member alias parity |
| Normalized import model convergence | yes | yes | yes | Shared import model across language import collectors |
| Call-site extraction query-driven | yes | yes | yes | Query API required |
| Call attribution to enclosing callable | yes | yes | yes | Scope resolver parity assertions |
| Shared call-resolution stage contract | yes | yes | yes | Enforced via kernel stage-order validator |
| Strict call-gate materialization | yes | yes | yes | `strict_call_contract` in assembler |
| Deterministic edge ordering | yes | yes | yes | Contract + tests |
| Partial-parse fail-closed metadata | yes | yes | yes | No heuristic traversal fallback |
| Walker construct capability declarations | yes | yes | yes | Explicit language construct->structural emission map |
| Profile function extras via tree-sitter | yes | yes | yes | Python/TS/Java profile reducers |
| Profile class extras via tree-sitter | yes | yes | yes | Python/TS/Java profile reducers |
| Capability manifest generated from query surfaces | yes | yes | yes | `docs/CAPABILITY_MANIFEST.json` gate |
| Parity quality threshold gate (nodes+calls) | yes | yes | yes | `test_language_parity_score_gate.py` |
| Triplet parity fixture coverage | yes | yes | yes | `test_language_parity_triplets.py` |
| Service-call parity benchmark | yes | yes | yes | `test_language_parity_bench.py` |

## Declared Language-Specific Differences

- Nested named callables are structural and emitted as callable nodes.
- Inline anonymous callbacks remain non-structural; calls inside them are
  attributed to nearest enclosing structural callable.
- TypeScript import parsing supports the grammar surface available via
  `import_statement`, `export_statement`, and require-style lexical declarations.
- Java import parsing supports class aliases, static member aliases, and static wildcard owners.
- Python and TypeScript use different instance-map strategies:
  Python resolves module/class/callable scopes eagerly; TypeScript resolves pending
  instance/alias assignments in a deferred pass before call resolution.
- Python does not emit `IMPLEMENTS` edges because there is no dedicated
  interface-implementation syntax token; this is tracked as `n/a` parity, not a defect.

## Gate Criteria

Changes are expected to:

1. preserve all `yes` capabilities;
2. preserve `yes` parity with tests in `tests/code_analysis/`;
3. keep parity contract and kernel stage contract synchronized;
4. never violate `docs/CONTRACT.md` or `docs/COMPLIANCE_CHECKLIST.md`.
