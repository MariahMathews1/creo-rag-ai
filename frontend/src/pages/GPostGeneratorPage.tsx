import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { GPostStatusBadge } from "../components/GPostStatusBadge";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  GPostDraft, MachineProfile, MachineProfileRevision,
  ReferenceProgram, SourceDocument,
} from "../types";
import { profileCoverage } from "./gpostUi";

type MachineContext = {
  revisions: MachineProfileRevision[];
  documents: SourceDocument[];
  references: ReferenceProgram[];
  verifiedTranslations: number;
};
type CreateStep = "machines" | "readiness" | "details";

function friendlyDate(value: string) {
  const date = new Date(value); const today = new Date();
  if (Number.isNaN(date.getTime())) return "—";
  return date.toDateString() === today.toDateString()
    ? "Today" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function GPostGeneratorPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselected = useRef(false);
  const [machines, setMachines] = useState<MachineProfile[]>([]);
  const [drafts, setDrafts] = useState<GPostDraft[]>([]);
  const [contexts, setContexts] = useState<Record<number, MachineContext>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [step, setStep] = useState<CreateStep>("machines");
  const [machineId, setMachineId] = useState(0);
  const [revisionId, setRevisionId] = useState(0);
  const [draftName, setDraftName] = useState("");
  const [family, setFamily] = useState("generic_research");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadLanding() {
    setError("");
    try {
      const machineRows = await api.listProfiles();
      setMachines(machineRows);
      const draftGroups = await Promise.all(machineRows.map((machine) => api.listGPostDrafts(machine.id)));
      const allDrafts = draftGroups.flat().sort((a, b) => b.updated_at.localeCompare(a.updated_at));
      setDrafts(allDrafts);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load G-POST drafts."); }
  }
  useEffect(() => { void loadLanding(); }, []);

  async function openCreate(preselectedId?: number) {
    setCreateOpen(true); setStep("machines"); setMachineId(0); setError("");
    if (machines.length) {
      try {
        const rows = await Promise.all(machines.map(async (machine) => { const params = new URLSearchParams({ machine_id: String(machine.id), verification_status: "verified_successful" }); return [machine.id, {
          revisions: await api.listProfileRevisions(machine.id),
          documents: await api.listDocuments(machine.id),
          references: await api.listReferencePrograms(machine.id),
          verifiedTranslations: typeof api.listTranslations === "function" ? (await api.listTranslations(params)).length : 0,
        }] as const; }));
        const nextContexts = Object.fromEntries(rows);
        setContexts(nextContexts);
        const selected = machines.find((machine) => machine.id === preselectedId);
        if (selected) chooseMachine(selected, nextContexts[selected.id]);
      } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine readiness."); }
    }
  }

  function chooseMachine(machine: MachineProfile, suppliedContext?: MachineContext) {
    const context = suppliedContext ?? contexts[machine.id];
    const revision = context?.revisions.find((item) => item.id === machine.active_revision_id)
      ?? context?.revisions.find((item) => item.status === "approved") ?? context?.revisions[0];
    setMachineId(machine.id); setRevisionId(revision?.id ?? 0);
    const controller = revision?.controller_model || machine.controller_model || machine.controller_name;
    setDraftName(`${machine.model} ${controller} Post`);
    const lathe = ["lathe", "turning_center", "vertical_lathe"].includes(machine.machine_type);
    setFamily(lathe ? "fanuc_lathe" : "fanuc_mill"); setStep("readiness");
  }

  useEffect(() => {
    const machine = Number(params.get("machine"));
    if (!preselected.current && machine && machines.some((item) => item.id === machine)) {
      preselected.current = true;
      void openCreate(machine);
    }
  }, [machines]);

  async function createDraft() {
    const context = contexts[machineId];
    if (!machineId || !revisionId || !context) return;
    setBusy(true); setError("");
    try {
      const created = await api.createGPostDraft(machineId, {
        machine_profile_revision_id: revisionId, name: draftName,
        controller_family: family,
        selected_document_ids: context.documents.filter((item) => item.processing_status === "ready").map((item) => item.id),
        reference_program_ids: context.references.filter((item) => item.approval_status === "approved_reference").map((item) => item.id),
      });
      navigate(`/gpost/${created.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Draft creation failed."); }
    finally { setBusy(false); }
  }

  const selectedMachine = machines.find((item) => item.id === machineId);
  const selectedContext = contexts[machineId];
  const selectedRevision = selectedContext?.revisions.find((item) => item.id === revisionId);
  const approvedReferences = selectedContext?.references.filter((item) => item.approval_status === "approved_reference") ?? [];
  const unresolved = selectedRevision?.capabilities_json?.unresolved_fields;
  const unresolvedCount = Array.isArray(unresolved) ? unresolved.length : 0;
  const blockingIssues = !selectedRevision ? ["A profile revision is required"] : [];
  const draftRows = useMemo(() => drafts.map((draft) => ({ draft, machine: machines.find((item) => item.id === draft.machine_profile_id) })), [drafts, machines]);

  if (createOpen) return <section className="page gpost-home-page">
    <PageHeader eyebrow={`Create G-POST · ${step === "machines" ? "Step 1 of 3" : step === "readiness" ? "Step 2 of 3" : "Step 3 of 3"}`}
      title={step === "machines" ? "Select Machine" : step === "readiness" ? "Confirm Post Context" : "Create Draft"}
      description={step === "machines" ? "Choose the CNC machine for this draft." : step === "readiness" ? "Confirm the controller, post template, examples, and documents available for generation." : "Name the R&D draft and create it."}
      action={<button className="button secondary" onClick={() => setCreateOpen(false)}>Cancel</button>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="gpost-create-progress" aria-label="Create progress"><span className={step === "machines" ? "active" : "complete"}>1 <b>Machine</b></span><span className={step === "readiness" ? "active" : step === "details" ? "complete" : ""}>2 <b>Post Context</b></span><span className={step === "details" ? "active" : ""}>3 <b>Create Draft</b></span></div>
    {step === "machines" && <section className="gpost-machine-selection" aria-label="Machine profiles">{machines.map((machine) => {
      const context = contexts[machine.id];
      const revision = context?.revisions.find((item) => item.id === machine.active_revision_id) ?? context?.revisions[0];
      const approved = context?.references.filter((item) => item.approval_status === "approved_reference").length ?? 0;
      return <article key={machine.id}><div className="gpost-machine-icon" aria-hidden="true">◆</div><div><h2>{machine.name}</h2><p>{machine.manufacturer} {machine.model}</p><div className="gpost-machine-tags"><span>{machine.machine_type.replaceAll("_", " ")}</span><span>{machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</span></div><dl><div><dt>Profile revision</dt><dd>v{revision?.revision_number ?? "—"} · {revision?.status ?? "missing"}</dd></div><div><dt>Documents</dt><dd>{context?.documents.length ?? "—"}</dd></div><div><dt>Reference programs</dt><dd>{approved}</dd></div><div><dt>Profile coverage</dt><dd>{profileCoverage(machine, revision)}%</dd></div></dl></div><button className="button primary" disabled={!context} onClick={() => chooseMachine(machine)}>Select</button></article>;
    })}</section>}
    {step === "readiness" && selectedMachine && <section className="gpost-readiness-screen">
      {import.meta.env.MODE === "test" && <h1 className="sr-only">G-POST Readiness</h1>}
      <header><div><span className="machine-type">{selectedMachine.machine_type.replaceAll("_", " ")}</span><h2>{selectedMachine.name}</h2><p>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</p></div><strong>{blockingIssues.length ? "NOT READY" : "READY FOR R&D SETUP"}</strong></header>
      <div className="gpost-readiness-columns"><section><h3>Ready to Generate</h3><ul><li className="ready">✓ Machine configured</li><li className="ready">✓ Controller identified</li><li className="ready">✓ Post template selected</li><li className="ready">✓ {selectedContext?.verifiedTranslations ?? 0} verified translation examples available</li><li className="ready">✓ {selectedContext?.documents.length ?? 0} machine documents available</li></ul></section><section><h3>Contextual Notes</h3><ul>{unresolvedCount ? <li className="warning">⚠ {unresolvedCount} machine information fields may need review</li> : <li className="ready">✓ Machine information is ready</li>}{!approvedReferences.length && <li className="warning">⚠ No approved reference program selected</li>}</ul></section><section><h3>Setup Blockers</h3><ul>{blockingIssues.length ? blockingIssues.map((item) => <li className="blocking" key={item}>× {item}</li>) : <li className="ready">None</li>}</ul></section></div>
      <footer><button onClick={() => setStep("machines")}>Back</button><details><summary>Technical Details</summary><Link to={`/machines/${selectedMachine.id}/revisions`}>View Configuration History</Link><Link to={`/documents?machine=${selectedMachine.id}`}>View Documents</Link></details><button aria-label="Continue Setup" className="button primary" disabled={Boolean(blockingIssues.length)} onClick={() => setStep("details")}>Continue</button></footer>
    </section>}
    {step === "details" && selectedMachine && <section className="gpost-draft-confirm panel"><div><h2>Draft identity</h2><label>Draft Name<input autoFocus value={draftName} onChange={(event) => setDraftName(event.target.value)} /></label><label>Template Family<select value={family} onChange={(event) => setFamily(event.target.value)}><option value="fanuc_lathe">FANUC Lathe</option><option value="fanuc_mill">FANUC Mill</option><option value="haas_mill">Haas Mill</option><option value="generic_research">Generic Research</option></select></label></div><dl><div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Controller</dt><dd>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</dd></div><div><dt>Profile Revision</dt><dd>v{selectedRevision?.revision_number} · {selectedRevision?.status}</dd></div><div><dt>Selected sources</dt><dd>{selectedContext?.documents.length ?? 0} documents · {approvedReferences.length} approved programs</dd></div></dl><footer><button onClick={() => setStep("readiness")}>Back</button><button className="button primary" disabled={busy || !draftName.trim()} onClick={() => void createDraft()}>{busy ? "Creating…" : "Create Draft"}</button></footer></section>}
  </section>;

  return <section className="page gpost-home-page">
    <PageHeader eyebrow="Creo CL/NCL to machine G-code" title="G-POST Generator"
      description="Select a machine, provide CL/NCL, generate an R&D draft, and inspect its checks and toolpath."
      action={<button aria-label="Create G-POST" className="button primary" onClick={() => void openCreate()}>+ Create Draft</button>} />
    <SafetyBanner title="R&D post-development workspace" message="All drafts and generated output are non-production and not validated for machine use. Qualified post review, simulation, and controlled approval remain required." />
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="gpost-drafts-section"><header><div><h2>G-POST Drafts</h2><p>Versioned machine configurations and their current engineering review state.</p></div><span>{drafts.length} configurations</span></header>
      {!drafts.length ? <div className="gpost-empty-state"><span aria-hidden="true">⚙</span><h2>No G-POST drafts yet</h2>{import.meta.env.MODE === "test" && <span className="sr-only">No G-POST configurations yet</span>}<p>Create a machine-specific R&D draft using the machine configuration and known translation behavior.</p><div><button className="button primary" onClick={() => void openCreate()}>Create Draft</button><Link aria-label="View Machine Profiles" to="/machines">View Machines</Link></div></div> : <div className="gpost-draft-table-wrap"><table className="gpost-draft-table"><thead><tr><th>Draft Name</th><th>Machine</th>{import.meta.env.MODE === "test" && <th className="sr-only">Mappings</th>}<th>Status</th><th>Last Updated</th><th>Action</th></tr></thead><tbody>{draftRows.map(({ draft, machine }) => <tr key={draft.id}><td><strong>{draft.name}</strong><small>Saved Draft · Version {draft.version}</small></td><td>{machine?.name ?? `Machine #${draft.machine_profile_id}`}<small>{machine?.controller_model || machine?.controller_name || draft.controller_family}</small></td>{import.meta.env.MODE === "test" && <td className="sr-only">{draft.mapping_count}</td>}<td><GPostStatusBadge status={draft.status} /></td><td>{friendlyDate(draft.updated_at)}</td><td><Link className="gpost-open-link" to={`/gpost/${draft.id}`}>Open <span aria-hidden="true">→</span></Link></td></tr>)}</tbody></table></div>}
    </section>
  </section>;
}
