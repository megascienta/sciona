# Language Adapter Template

Use this folder as a starter when adding a new SCIONA language adapter package.

Required adapter contract (`AdapterSpecV1`):

- `language_id`
- `extensions`
- `grammar_name`
- `query_set_version`
- `callable_types`
- `module_namer`
- `extractor_factory`
- `capability_manifest_key`

Suggested workflow:

1. Copy this template into `languages/builtin/<lang>/` or an external package.
2. Implement `extractor_factory` and `module_namer`.
3. Add query surfaces and walker capability declarations.
4. Validate onboarding via `validate_language_onboarding(...)`.
5. Add parity fixture tests before enabling by default.
