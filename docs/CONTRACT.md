# SCIONA Structural Contract

This contract defines the language-agnostic structural model SCIONA MUST emit.
It is authoritative for analysis and validation.

## Scope

- Applies to all supported languages.
- Applies to the single committed snapshot retained in CoreDB.
- `node_instances` and `edges` facts are snapshot-bound by `snapshot_id`.
- `structural_nodes` identities are global and carry deterministic
  `created_snapshot_id` provenance.
- Static, syntax-only analysis; no execution, no runtime inference.
- Extraction is tree-sitter query/field driven.
- Tree-sitter parser setup MUST be deterministic and use
  `tree_sitter.Parser` + `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper is allowed for multi-language growth.
- Allowed bootstrap scope is strictly:
  parser construction, language binding, and parser/grammar diagnostics.
- Bootstrap helper location is `src/sciona/code_analysis/core/extract/parser_bootstrap.py`.
- Query/extraction helpers MUST be separate from bootstrap helper code
  (for example `core/extract/query_helpers.py`).
- Bootstrap helper MUST NOT perform parsing fallback, extraction logic,
  language routing, or semantic behavior changes.
- General parser wrapper/factory abstractions remain out-of-contract.
- Structural extraction MUST fail closed for unsupported query node types.
- No heuristic traversal fallback is allowed for structural extraction.

## Structural Nodes

SCIONA MUST emit these structural node types:

- `module`
- `type`
- `callable`

`callable` role metadata MUST classify each callable as one of:

- `declared`
- `nested`
- `bound`
- `constructor`

Promotion rule for `callable`:

- A callable is structural iff it introduces a callable body with a stable
  lexical binding in the current lexical parent.
- Inline anonymous callbacks without stable lexical binding MUST NOT be
  structural nodes.

Synthetic nodes:

- Implementations MAY emit synthetic navigation nodes (for example `entry_point`).
- Synthetic nodes are out-of-contract for language compliance.
- Synthetic nodes MUST NOT be treated as language structural entities.

## Structural Edges

SCIONA MUST emit these edge types:

- `LEXICALLY_CONTAINS` (lexical parent -> lexical child)
- `IMPORTS_DECLARED` (module -> module)
- `CALLS` (callable -> callable, in-repo only)
- `EXTENDS` (type -> type, local syntactic inheritance)
- `IMPLEMENTS` (type -> type, local syntactic implementation)

## Edge Semantics

`LEXICALLY_CONTAINS`:

- Structural hierarchy is a lexical tree per module.
- `module` is the only lexical root.
- Every non-`module` structural node MUST have exactly one lexical parent.
- Parent and child MUST be from the same module/file lexical tree.
- Parent source span MUST contain child source span.
- Parent and child source spans MUST NOT be identical.
- Graph MUST be acyclic.
- Allowed pairs:
  - `module -> type`
  - `module -> callable`
  - `type -> type`
  - `type -> callable`
  - `callable -> type`
  - `callable -> callable`

`CALLS`:

- MUST represent syntactic call expressions only.
- MUST NOT represent attribute reads/writes or other non-call expressions.
- MUST be emitted only when the final accepted target is an in-repo callable.

`EXTENDS`:

- MUST represent direct syntax-level base declarations only.
- MUST NOT require cross-file semantic inference.

`IMPLEMENTS`:

- MUST represent direct syntax-level interface implementation declarations only.
- MUST NOT be inferred from structural similarity or method matching.

## Naming and Identity

Module identity:

- Canonical module identity is path-derived via
  `module_name_from_path(repo_root, file_path)`.
- Canonical identity MUST be used for structural node identity and storage.

Qualified names:

- Qualified names MUST encode lexical ownership.
- Identifiers MAY include deterministic disambiguators when required.

Disambiguation:

- If multiple structural siblings share the same local name in one lexical parent,
  identity MUST be disambiguated deterministically by lexical order
  (`start_byte` ascending).

Alias usage:

- Language-specific aliases MAY be used for resolution assistance.
- Aliases MUST NOT replace canonical module identity.

## Call Attribution and Materialization

Attribution:

- Calls are attributed to the nearest enclosing structural callable node.
- Inline anonymous non-structural callable bodies attribute calls to their
  nearest enclosing structural callable node.

Materialization gate:

- Candidate resolution may produce provisional outcomes.
- Required resolution stages (receiver/instance mapping, alias narrowing, class
  scoped fallback, module scoped fallback) are executed in language-specific
  resolver paths before strict materialization.
- Final CALLS emission MUST pass strict candidate selection.
- Strict candidate selection is the final acceptance/materialization gate and
  MUST NOT be interpreted as the full resolution-stage pipeline.
- Non-accepted candidates (unresolved, ambiguous, external, disallowed provenance)
  MUST be dropped.

## Import Handling

- Import extraction is syntax-only.
- Import normalization maps syntax-level targets to module identities.
- External/unresolved imports are out-of-contract.

Optional metadata:

- Implementations MAY attach import metadata (for example `import_scope`).
- Metadata MUST NOT alter structural edge types or contract semantics.
- Implementations MAY attach structural enrichment metadata, including:
  - callable role and modifiers,
  - local base/interface names,
  - module-level binding names,
  - ambiguous call candidate diagnostics.

## Artifacts Observability

`CALL_SITES` is an artifact-layer observational table.

- `CALLS` remains the only authoritative call edge truth for reducers.
- `CALL_SITES` MUST NOT define new structural entities or structural edges.
- `CALL_SITES` stores in-repo candidate-relevant callsite observations only.
- External callsites MUST NOT be persisted as rows in `CALL_SITES`.

## Determinism

Outputs MUST be deterministic, stably ordered, and snapshot-bound.

Stable ordering MUST be:

1. module path lexical order
2. qualified name lexical order
3. edges sorted by `(source, target, edge_type)`
