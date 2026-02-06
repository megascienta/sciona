# SCIONA module impact briefing

## Task
Produce a concise, evidence-first briefing for a target module.
Use only the structural evidence provided. Do not infer runtime behavior.

## Output format
- Target module: 2-4 bullets (id, qualified name, file path, language)
- Public surface & key symbols: 3-6 bullets (classes/functions, top-level APIs)
- Outbound dependencies: 3-6 bullets (imports the module makes)
- Inbound dependents: 3-6 bullets (modules that import this module)
- Risk notes: 2-4 bullets (fan-in/out concentration, brittle dependencies)

## Evidence
{MODULE_OVERVIEW}
{DEPENDENCY_EDGES}
{IMPORTERS_INDEX}
