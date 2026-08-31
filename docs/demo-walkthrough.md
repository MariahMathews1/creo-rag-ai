# V1 Demo Walkthrough

Use **R&D FANUC Lathe Demo** and **RL-200 FANUC 0i-TF Demo Post**. Begin: “This is a pre-Azure R&D workflow. It organizes post-development evidence; it does not compile a native post.”

| Stop | What to say | What to click | What the audience should notice | Ask the NC programmer |
|---|---|---|---|---|
| Machines | The machine is the authoritative context. | Machines → R&D FANUC Lathe Demo | Controller, type, readiness, and Demo badge. | Does this match how you identify a machine/controller today? |
| Machine Overview | Review starts from one obvious next action. | Review Machine Knowledge | Knowledge status without internal IDs. | Who normally owns this review? |
| Machine Knowledge | Extracted values stay proposed until a person confirms them. | Maximum Feed Rate → Review | Source, status, reviewer actions, and Used By traceability. | Does this match how you gather machine information today? |
| Documents | Evidence stays machine-scoped. | Documents → RL-200 Machine Manual | Extraction status and contextual actions. | Which manuals are authoritative at your site? |
| Post Builder | A Post Record pins the reviewed machine context. | Open RL-200 FANUC 0i-TF Demo Post | Status is Building; uncertainty is not hidden. | What else must be selected before development starts? |
| Overview | This is the development control point. | Overview | Completion, blockers, and one next action. | Are these the right readiness categories? |
| OFG | The app builds a checklist, not a native Option File. | OFG Configuration → a spindle setting | Manual → fact → setting traceability, notes, unverified menu labels. | Are these the values you enter into Option File Generator? |
| Site Standards | Local behavior is applied explicitly. | Expand Site Standards | Tool Change Safe Retract and conflict handling. | Which local rules supplement manuals? |
| Custom Logic | Non-standard behavior is tracked cautiously. | Custom Logic → open G74 item | Reason, evidence, review state; FIL/CIMFIL remains potential. | What normally forces you to use FIL? |
| Review & Export | Outstanding work and handoff share one finish line. | Review & Export | Exact G74 question, manual validation, exports, disclaimer. | What must be resolved before accepting this package? |
| History & Sources | Checkpoints and evidence remain traceable. | History & Sources | Version lineage and selected documents. | What audit evidence do you need? |
| Machine Assistant | Retrieval is advisory and cited. | Ask a spindle-limit question | Citations and explicit insufficient-evidence behavior. | Would this save time checking manuals? |

Close with:

- Does this match how you gather machine information today?
- Are these the types of values you actually enter into Option File Generator?
- What important OFG settings are missing?
- What normally forces you to use FIL?
- Would an OFG checklist like this save useful setup time?
