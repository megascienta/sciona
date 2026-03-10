Task: Module Architecture Review

Review the module:

<module_name>

Focus strictly on structural aspects of the repository.

Evaluate the following:

1. Responsibility boundaries
   - Does the module appear to contain multiple unrelated responsibilities?
   - Do responsibilities overlap with neighbouring modules?
   - Are there files that logically belong to another module?

2. File organization
   - Does the number of files suggest the module should be split into subfolders?
   - Are there subfolders that contain only one file and therefore add unnecessary depth?
   - Are there folders with too many heterogeneous files?

3. Structural cohesion
   - Do files in the module strongly reference each other?
   - Or do they mostly interact with external modules?

4. Naming and discoverability
   - Are file and folder names consistent with their responsibilities?
   - Could a developer locate functionality quickly from the structure alone?

5. Potential improvements
   - Suggest concrete refactorings such as:
     - splitting modules
     - introducing subfolders
     - merging folders
     - relocating files

Important constraints:

- Base conclusions only on repository structure and symbol relationships.
- If an observation cannot be supported by structural evidence, mark it as uncertain.

Output format:

Module: <name>

Current structure summary
- number of files
- subfolders
- major symbols or components

Findings
- Responsibility issues
- File organization issues
- Cohesion observations

Improvement proposals
- specific structural changes
- expected benefit

After completing the review:
1. Append a short session note to sciona_session_notes.md.
2. Include ratings for:
   - Structural clarity
   - Navigation speed
   - Confidence in conclusions
   - Overall usefulness of SCIONA