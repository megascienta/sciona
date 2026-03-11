# SCIONA Structural Contract

This contract defines the language-agnostic structural model SCIONA MUST emit.
It is authoritative for analysis and validation.

## Scope

- Applies to all supported languages.
- Applies to the single committed snapshot retained in CoreDB and the
  immediately rebuilt reducer-facing ArtifactDB state derived from that
  snapshot.
- `node_instances` and structural `edges` facts in CoreDB are snapshot-bound by
  `snapshot_id`.
- `structural_nodes` identities are global and carry deterministic
  `created_snapshot_id` provenance.
- CoreDB does not store call edges.
- `CALL_SITES` and reducer-facing `CALLS` are artifact-layer constructs derived
  after structural snapshot creation.
- Reducer-facing query semantics are defined against ArtifactDB latest-state
  derived surfaces for the committed snapshot.
- Reducers MAY use CoreDB in the same request for committed structural identity
  resolution, naming, file metadata, and other structural context.
- CoreDB remains the committed structural source; ArtifactDB remains the
  reducer-facing derived projection layer.
- Static, syntax-only analysis; no execution, no runtime inference.
- Extraction is tree-sitter query/field driven.
- Tree-sitter parser setup MUST be deterministic and use
  `tree_sitter.Parser` + `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper is allowed for multi-language growth.
- Allowed bootstrap scope is strictly:
  parser construction, language binding, and parser/grammar diagnostics.
- Bootstrap helper location is
  `src/sciona/code_analysis/core/extract/parsing/parser_bootstrap.py`.
- Query/extraction helpers MUST be separate from bootstrap helper code
  (for example `core/extract/parsing/query_helpers.py`).
- Bootstrap helper MUST NOT perform parsing fallback, extraction logic,
  language routing, or semantic behavior changes.
- General parser wrapper/factory abstractions remain out-of-contract.
- Structural extraction MUST fail closed for unsupported query node types.
- No heuristic traversal fallback is allowed for structural extraction.

## Structural Nodes

SCIONA MUST emit these structural node types:

- `module`
- `classifier`
- `callable`

`classifier` is the language-agnostic structural node category for named,
nominal, class-family declarations. It covers entities such as classes and
other class-family declarations with stable structural identity. It does not
include modules or callables.

`callable` role metadata MUST classify each callable as one of:

- `declared`
- `nested`
- `bound`
- `constructor`

Callable role definitions:

- `declared` is the default role for a named structural callable declaration
  that is neither nested, nor promoted from a stable binding, nor a
  constructor.
- `nested` is a named structural callable declaration whose lexical parent is a
  structural callable.
- `bound` is a callable body promoted to a structural callable because it has a
  stable lexical binding in the current lexical parent.
- `constructor` is a constructor-form callable attached to a structural
  classifier.

Promotion rule for `callable`:

- A callable is structural if it introduces a callable body with a stable
  lexical binding in the current lexical parent.
- Inline anonymous callbacks without stable lexical binding MUST NOT be
  structural nodes.

Synthetic nodes:

- Implementations MAY emit synthetic navigation nodes (for example `entry_point`).
- Synthetic nodes are out-of-contract for language compliance.
- Synthetic nodes MUST NOT be treated as language structural entities.
- Synthetic node identities and qualified names MUST be collision-safe with
  language structural node identities.
- Synthetic nodes MUST NOT shadow, reuse, or alias the canonical identity of a
  real structural `module`, `classifier`, or `callable`.

## Structural Edges

SCIONA structural extraction in CoreDB MUST emit these edge types:

- `LEXICALLY_CONTAINS` (lexical parent -> lexical child)
- `IMPORTS_DECLARED` (module -> module)
- `EXTENDS` (classifier -> classifier, local syntactic inheritance)
- `IMPLEMENTS` (classifier -> classifier, local syntactic implementation)

SCIONA reducer-facing ArtifactDB graph projections MAY also expose:

- `CALLS` (callable -> callable, in-repo only, artifact-finalized)

## Edge Semantics

`LEXICALLY_CONTAINS`:

- Structural hierarchy is a lexical tree per module.
- `module` is the only lexical root.
- Every non-`module` structural node MUST have exactly one lexical parent.
- Parent and child MUST be from the same module/file lexical tree.
- Parent source span MUST contain child source span when both spans are present.
- Identical parent/child source spans are allowed only for `module -> child`.
- Non-`module` parent and child source spans MUST NOT be identical.
- Graph MUST be acyclic.
- Allowed pairs:
  - `module -> classifier`
  - `module -> callable`
  - `classifier -> classifier`
  - `classifier -> callable`
  - `callable -> classifier`
  - `callable -> callable`

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

CoreDB structural build:

- CoreDB structural build MUST NOT resolve, accept, reject, or materialize
  calls as structural facts.
- CoreDB MAY observe or carry transient raw callsite observations during
  extraction/build execution.
- CoreDB MUST NOT persist reducer-facing `CALLS`.
- CoreDB MUST NOT persist `CALL_SITES`.

Artifact-finalized call projection:

- Reducer-facing `CALLS` is finalized in ArtifactDB immediately after the
  committed CoreDB snapshot is built.
- Artifact processing MAY start from the full observed syntactic callsite set
  emitted by analyzers/build execution.
- Artifact processing owns all pre-persistence callsite filtering.
- Promotion from observed callsites to persisted ArtifactDB `CALL_SITES`, and
  from persisted `CALL_SITES` to reducer-facing `CALLS`, MUST occur only in the
  artifact pipeline.
- Artifact finalization re-analyzes callsites against the committed snapshot and
  persists deterministic reducer-facing call artifacts.
- Artifact finalization MAY accept artifact-only rescue provenance, including
  `export_chain_narrowed`, that is not part of any CoreDB structural fact.
- Reducer-facing `CALLS` MUST represent syntactic call expressions only.
- Reducer-facing `CALLS` MUST NOT represent attribute reads/writes or other
  non-call expressions.
- Reducer-facing `CALLS` MUST target in-repo callable IDs only.

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

## Artifact Semantics

ArtifactDB is the reducer-facing query store and is rebuilt immediately after
each committed CoreDB snapshot.

ArtifactDB tables and rollups are latest-state derived surfaces for the current
committed snapshot rather than independently snapshot-keyed structural facts.

Dirty-worktree overlay metadata is advisory. `overlay_available=true` means
overlay state exists for the reducer request, but it does not guarantee that the
payload itself was transformed to reflect the dirty worktree.

Some reducer projections are intentionally overlay-aware but not
payload-patchable. For those projections, `_diff` metadata MAY be attached while
the payload remains committed-snapshot only.

Overlay contract note:

- `overlay_available=true` MAY correspond to either a patchable projection or a
  metadata-only projection.
- Metadata-only projections MUST continue to describe committed-snapshot payload
  facts even when `_diff` metadata is attached.
- Overlay metadata MUST NOT be interpreted as committed CoreDB or ArtifactDB
  structural truth for the dirty worktree.

`CALL_SITES`:

- is an artifact-layer callsite table, not a structural entity table.
- MUST NOT define structural nodes or CoreDB structural edges.
- is the filtered persisted artifact working set for call analysis, reporting,
  and final call derivation; it is not required to contain the raw full
  observed callsite superset.
- MAY exclude standard-library, clearly external, or otherwise out-of-scope
  observed callsites before persistence.
- MAY store accepted and dropped callsite outcomes used for diagnostics,
  reporting, and artifact call finalization.
- MAY persist dropped rows whose downstream reporting classification is
  artifact-only metadata such as `external_likely`.
- MAY include derived artifact-layer acceptance provenance not present in the
  raw observed callsite stream.

ArtifactDB `CALLS`:

- is the reducer-facing finalized call graph.
- is derived after CoreDB snapshot creation from persisted ArtifactDB
  `CALL_SITES` plus committed structural context.
- MUST remain deterministic with respect to the committed CoreDB snapshot and
  repository worktree state at artifact build time.
- MUST include only in-repo callable targets.

Reporting classifications on dropped callsites (for example `external_likely`)
are artifact metadata only and MUST NOT be restated as CoreDB structural facts.
- `external_likely` is a reporting/quality classification over persisted dropped
  artifact callsite rows; it is not evidence that all external callsites are
  stored.

Reducer read model:

- Reducers MAY combine CoreDB and ArtifactDB reads in one request.
- CoreDB reads are used for committed structural identity, structural context,
  and authoritative node/module metadata.
- ArtifactDB reads are used for latest-state derived relationship projections,
  call graphs, rollups, and callsite diagnostics.

## Determinism

Outputs MUST be deterministic and stably ordered.

CoreDB structural outputs are snapshot-bound.

ArtifactDB reducer-facing outputs are defined for the latest-state derived
surfaces corresponding to the committed snapshot.

Stable ordering MUST be:

1. module path lexical order
2. qualified name lexical order
3. edges sorted by `(source, target, edge_type)`

## Compliance Criteria

Language implementations MUST satisfy all criteria below.

Global criteria:

- CoreDB retains exactly one authoritative committed snapshot.
- ArtifactDB is rebuilt immediately after the committed CoreDB snapshot in the
  normal build flow and serves as the reducer-facing query store.
- Emits core node types: `module`, `classifier`, `callable`.
- Callable role metadata is present and in `{declared,nested,bound,constructor}`.
- Optional synthetic nodes are allowed but excluded from language compliance.
- CoreDB emits structural edge types:
  `LEXICALLY_CONTAINS`, `IMPORTS_DECLARED`, `EXTENDS`, `IMPLEMENTS`.
- `module` is lexical root; each non-`module` structural node has exactly one
  lexical parent.
- Parent span contains child span for `LEXICALLY_CONTAINS` when both spans are
  present.
- Module parents may share an identical span with an immediate lexical child;
  non-module parents may not.
- Lexical structural graph is acyclic.
- Constructors are represented as `callable` with role `constructor`.
- Canonical module identity is path-derived (not alias-derived).
- Calls are attributed to nearest enclosing structural callable.
- Inline anonymous non-structural callables do not become structural nodes.
- Optional enrichment metadata may be present on nodes/modules
  (for example role/modifier/base/module-binding diagnostics).
- Extraction is tree-sitter query/field driven.
- Parser setup is deterministic and uses `tree_sitter.Parser` +
  `tree_sitter_languages.get_language`.
- A narrow parser bootstrap helper may be used only for:
  parser construction, language binding, and parser/grammar diagnostics.
- General parser wrappers/factories are not used.
- Structural extraction fallback traversal is not allowed.
- Unsupported query node types fail closed for the affected extraction surface;
  implementations MAY preserve deterministic structural facts that remain
  directly supported by the parsed tree and record degraded diagnostics, but no
  heuristic fallback is allowed.
- Artifact-finalized reducer-facing `CALLS` targets are in-repo callable IDs
  only.
- CoreDB strict candidate selection drops non-accepted candidates before any
  structural call normalization is reused downstream.
- Artifact finalization MAY add reducer-facing rescue provenance such as
  `export_chain_narrowed`.
- Reducers read reducer-facing projections from ArtifactDB when present and MAY
  combine them with CoreDB structural lookups in the same request.
- `CALL_SITES` remains artifact-layer data and MUST NOT be restated as CoreDB
  structural truth.
- `CALL_SITES` MAY include dropped rows that later contribute to artifact-only
  reporting classifications such as `external_likely`.

Python criteria:

- `class_definition` maps to `classifier`.
- `function_definition` and `async_function_definition` map to `callable`.
- Nested named defs map to `callable` with role `nested`.
- Named lambda assignment bindings map to `callable` with role `bound`.
- `decorated_definition` contributes wrapped class/function node.
- `__init__.py` is treated as package module identity.
- Imports come from `import_statement` and `import_from_statement`.
- Direct Python class inheritance maps to `EXTENDS`.
- Python does not emit `IMPLEMENTS` as a distinct contract edge type.
- Calls are collected from `call` nodes and attributed by enclosing callable
  scope.
- Python `classifier` currently means named class declarations.

JavaScript criteria:

- `class_declaration` and `class_expression` map to `classifier`.
- `function_declaration` and `method_definition` map to `callable`.
- Bound callable expressions with stable lexical bindings from
  `variable_declarator`, `assignment_expression`, and `field_definition` map to
  `callable` with role `bound`.
- Constructors map to `callable` with role `constructor`.
- Inline anonymous callbacks are non-structural.
- Imports are extracted from:
  - `import_statement`,
  - `export_statement`,
  - `lexical_declaration` require-assignment patterns,
  - `call_expression` dynamic `import()` with string literal targets.
- Calls are collected from `call_expression` and `new_expression` and
  attributed by enclosing callable scope.
- JavaScript `classifier` currently means class-family declarations captured by
  the extractor query surface above.

TypeScript criteria:

- Class-like declarations map to `classifier`.
- Named function/method declarations map to `callable`.
- Nested named function declarations map to `callable` with role `nested`.
- Bound callable expressions (arrow/function expressions with stable bindings)
  map to `callable` with role `bound`.
- Object-literal methods bound to stable identifiers map to `callable` with
  role `bound`.
- Anonymous `export default` callables map to deterministic module callable
  bindings.
- Inline anonymous callbacks are non-structural.
- Imports are extracted from:
  - `import_statement`,
  - `export_statement`,
  - `lexical_declaration` require-assignment patterns,
  - `call_expression` dynamic `import()` with string literal targets.
- `import ... = require(...)` is represented under `import_statement` with
  `import_require_clause` in the current grammar build.
- Calls are collected from `call_expression`/`new_expression` and attributed by
  enclosing callable scope.
- Profiling/introspection classifier query surface includes
  `class_declaration`, `abstract_class_declaration`, `class_expression`.
- TypeScript `classifier` currently means class-family declarations captured by
  the extractor query surface above.

Java criteria:

- Class-family declarations include class/interface/enum/record forms and map to
  `classifier`.
- Methods and constructors map to `callable`.
- Methods on named local classes declared inside callable scopes map to
  `callable` role `nested` (constructors remain `constructor`).
- Named local classes are structural `classifier` nodes.
- Lambda expressions are non-structural callables.
- Imports are extracted from `import_declaration`.
- Package-derived alias may assist resolution, but canonical module identity
  remains path-based.
- Calls are collected from:
  - `method_invocation`,
  - `object_creation_expression`,
  - `explicit_constructor_invocation`.
- Profiling/introspection classifier query surface includes
  `class_declaration`, `interface_declaration`, `enum_declaration`,
  `record_declaration`.
- Java `classifier` currently means classes, interfaces, enums, and records.
