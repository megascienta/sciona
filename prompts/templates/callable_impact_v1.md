# SCIONA callable impact briefing

## Task
Produce a concise, evidence-first briefing for a target callable.
Use only the structural evidence provided. Do not infer runtime behavior.

## Output format
- Target callable: 2-4 bullets (id, qualified name, file path, language)
- Signature & context: 2-5 bullets (parent class/module, signature shape, decorators)
- Callers: 3-6 bullets (who calls this callable)
- Callees: 3-6 bullets (what this callable calls)
- Risk notes: 2-4 bullets (high fan-in/out, central dependency)

## Evidence
{CALLABLE_OVERVIEW}
{CALL_GRAPH}
