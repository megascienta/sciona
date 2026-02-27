# Parser Bootstrap Policy

This note records the parser initialization policy adopted for multi-language growth.

## Scope

- Applies to `src/sciona/code_analysis`.
- Defines what parser setup abstraction is allowed.

## Allowed Abstraction

- A single narrow helper is allowed for parser bootstrap.
- Allowed responsibilities:
  - instantiate `tree_sitter.Parser`,
  - bind grammar via `tree_sitter_languages.get_language`,
  - return diagnostics metadata about parser/grammar setup.

## Disallowed Abstraction

- General parser factories or wrappers that:
  - perform parse fallback,
  - route behavior by policy mode,
  - alter extraction semantics,
  - add caching/routing side effects outside parser setup.

## Rationale

- Keep extraction semantics explicit and language analyzers deterministic.
- Reduce duplicated setup code as languages increase.
- Preserve fail-closed and contract-compliance guarantees.
