Task: Algorithm and Logic Audit — `code_analysis` Module

Perform a systematic review of the `code_analysis` module, covering its tree-sitter parsers, analysis pipeline, and structural extraction and analysis logic. 

---

**Phase 1: Structural orientation**

Establish the module's structure before any semantic review:

- What are the major components and their responsibilities?
- How is the parsing pipeline organized — what calls what, in what order?
- Are there per-language analyzer variants? How do they relate to each other?
- Are there shared abstractions versus language-specific implementations?
- Are there components with unexpectedly high coupling that would make a defect here amplify broadly?

Record structural findings before proceeding. Do not begin phase 2 until phase 1 is complete.

---

**Phase 2: Algorithm and logic review**

Review source directly for the following. For each finding, cite the file and location.

**Parsing correctness**
- Are tree-sitter grammar bindings used correctly for each supported language?
- Are there assumptions about node types or field names that could break across grammar versions?
- Are error nodes (`ERROR`, `MISSING`) handled explicitly, or silently ignored?
- Are there language-specific edge cases that appear unhandled?

**Structural extraction logic**
- Are the extraction rules for callables, classifiers, imports, and inheritance consistent across languages?
- Are there extraction patterns that could produce duplicate or phantom structural nodes?
- Are there cases where containment relationships could be inferred incorrectly?

**Call resolution logic**
- What is the resolution strategy? Is it documented or implicit?
- Are there cases where resolution could silently produce false edges rather than drop candidates?
- Are drop reasons correctly classified and exhaustive?

**Analysis pipeline integrity**
- Are there ordering dependencies in the pipeline that are assumed but not enforced?
- Are there failure modes that could produce a partially-populated index without surfacing an error?
- Are there any global or shared mutable state patterns that could cause non-determinism across builds?

---

**Phase 3: Test coverage audit**

- Which components from phase 1 have direct test coverage?
- Are tree-sitter parsing edge cases covered — empty files, syntax errors, deeply nested structures, unicode?
- Are cross-language behaviors tested, or only per-language in isolation?
- Are call resolution drop reasons tested explicitly?
- Are there critical paths identified in phase 2 that have no test coverage?

List untested or undertested critical paths explicitly. These are release candidates for targeted `pytest` runs.

---

**Output format:**

```
Phase 1: Structural orientation
- Module shape: <summary>
- Major components: <list with brief role description>
- Coupling observations: <any high-fan-in or amplification risks>

Phase 2: Algorithm and logic findings
- Parsing correctness: <findings or: none identified>
- Structural extraction: <findings or: none identified>
- Call resolution: <findings or: none identified>
- Pipeline integrity: <findings or: none identified>

Phase 3: Test coverage gaps
- Covered: <components or paths with adequate coverage>
- Gaps: <untested or undertested critical paths>
- Recommended targeted tests: <specific scenarios to add or run>

Risk summary
- <finding> → <severity: low/medium/high> → <recommended action>
```