Task: Pre-Release Audit

Perform a full audit of the codebase under `src/`. The audit has three levels: per-module structure, cross-module relationships, and compliance with documented contracts in `docs/`.

---

**Level 1: Per-module structural review**

For each module in `src/`, evaluate:

**1. Responsibility boundaries**
- Does the module appear to contain multiple unrelated responsibilities?
- Do responsibilities overlap with neighbouring modules?
- Are there files that logically belong to another module?

**2. File organization**
- Does the number of files suggest the module should be split into subfolders?
- Are there subfolders that contain only one file and therefore add unnecessary depth?
- Are there folders with too many heterogeneous files?

**3. Structural cohesion**
- Do files in the module strongly reference each other?
- Or do they mostly interact with external modules?

**4. Naming and discoverability**
- Are file and folder names consistent with their responsibilities?
- Could a developer locate functionality quickly from the structure alone?

---

**Level 2: Cross-module audit**

**5. Coupling and boundary integrity**
- Are there unexpected high-fan-in modules whose failure would propagate broadly?
- Are there import patterns that violate expected module boundaries?
- Are there circular or surprising dependency chains?

**6. Structural risk signals**
- Are there resolution anomalies or structural integrity issues detectable from available tooling?
- Are there boundary violations suggesting fragile coupling?
- Mark any finding here as a candidate for deeper source inspection or targeted testing before release.

---

**Level 3: Contract and documentation compliance**

**7. Compliance with `docs/`**
- Are the module boundaries, public APIs, and structural relationships consistent with what is described in `docs/CONTRACT.md` and `docs/DEVELOPERGUIDE.md`?
- Are there structural facts that contradict documented contracts?
- Mark any discrepancy explicitly; do not resolve it — escalate it.

---

**Important constraints:**

- If an observation cannot be supported by evidence, mark it as uncertain.
- Any finding in level 2 or 3 MUST be explicitly handed off: mark it for source inspection, `rg`, or targeted `pytest` as appropriate. Do not treat a risk signal as resolved without follow-up.
- Follow `AGENTS.md` for all tooling decisions.

---

**Output format:**

Per-module findings:

```
Module: <module_name>

Current structure summary
- file count
- subfolders
- major symbols or components

Findings
- Responsibility issues
- File organization issues
- Cohesion observations

Improvement proposals
- structural quality: <specific changes and expected benefit>
```

Cross-module findings:

```
Coupling anomalies
- <finding>: <evidence> → <recommended follow-up>

Structural risk signals
- <finding>: <evidence> → <recommended follow-up>
```

Contract compliance findings:

```
Discrepancies
- <finding>: <structural fact> vs <documented claim> → escalate
```

Aggregate risk surface:

```
- List all findings from levels 2 and 3 requiring follow-up
- For each: recommended action and tooling
```