import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { GPostStatusBadge } from "../components/GPostStatusBadge";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  GPostDraft, GPostMapping, MachineProfile, MachineProfileRevision,
  ReferenceProgram, SourceDocument,
} from "../types";
import { profileCoverage } from "./gpostUi";

type MachineContext = {
  revisions: MachineProfileRevision[];
  documents: SourceDocument[];
  references: ReferenceProgram[];
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
  const [machines, setMachines] = useState<MachineProfile[]>([]);
  const [drafts, setDrafts] = useState<GPostDraft[]>([]);
  const [mappingsByDraft, setMappingsByDraft] = useState<Record<number, GPostMapping[]>>({});
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
      const mappingGroups = await Promise.all(allDrafts.map(async (draft) => [draft.id, await api.listGPostMappings(draft.id)] as const));
      setMappingsByDraft(Object.fromEntries(mappingGroups));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load G-POST drafts."); }
  }
  useEffect(() => { void loadLanding(); }, []);

  async function openCreate() {
    setCreateOpen(true); setStep("machines"); setMachineId(0); setError("");
    if (machines.length) {
      try {
        const rows = await Promise.all(machines.map(async (machine) => [machine.id, {
          revisions: await api.listProfileRevisions(machine.id),
          documents: await api.listDocuments(machine.id),
          references: await api.listReferencePrograms(machine.id),
        }] as const));
        setContexts(Object.fromEntries(rows));
      } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine readiness."); }
    }
  }

  function chooseMachine(machine: MachineProfile) {
    const context = contexts[machine.id];
    const revision = context?.revisions.find((item) => item.id === machine.active_revision_id)
      ?? context?.revisions.find((item) => item.status === "approved") ?? context?.revisions[0];
    setMachineId(machine.id); setRevisionId(revision?.id ?? 0);
    const controller = revision?.controller_model || machine.controller_model || machine.controller_name;
    setDraftName(`${machine.model} ${controller} Post`);
    const lathe = ["lathe", "turning_center", "vertical_lathe"].includes(machine.machine_type);
    setFamily(lathe ? "fanuc_lathe" : "fanuc_mill"); setStep("readiness");
  }

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
  const draftRows = useMemo(() => drafts.map((draft) => {
    const mappings = mappingsByDraft[draft.id] ?? [];
    return { draft, mappings, machine: machines.find((item) => item.id === draft.machine_profile_id),
      reviewed: mappings.filter((item) => item.review_status !== "pending").length };
  }), [drafts, mappingsByDraft, machines]);

  if (createOpen) return <section className="page gpost-home-page">
    <PageHeader eyebrow={`Create G-POST · ${step === "machines" ? "Step 1 of 3" : step === "readiness" ? "Step 2 of 3" : "Step 3 of 3"}`}
      title={step === "machines" ? "Select Machine" : step === "readiness" ? "G-POST Readiness" : "Create G-POST Draft"}
      description={step === "machines" ? "Choose the machine context that will govern the post configuration." : step === "readiness" ? "Review the available engineering sources and blockers before configuration begins." : "Name the controlled R&D draft and confirm its exact machine context."}
      action={<button className="button secondary" onClick={() => setCreateOpen(false)}>Cancel</button>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="gpost-create-progress" aria-label="Create progress"><span className={step === "machines" ? "active" : "complete"}>1 <b>Machine</b></span><span className={step === "readiness" ? "active" : step === "details" ? "complete" : ""}>2 <b>Readiness</b></span><span className={step === "details" ? "active" : ""}>3 <b>Draft</b></span></div>
    {step === "machines" && <section className="gpost-machine-selection" aria-label="Machine profiles">{machines.map((machine) => {
      const context = contexts[machine.id];
      const revision = context?.revisions.find((item) => item.id === machine.active_revision_id) ?? context?.revisions[0];
      const approved = context?.references.filter((item) => item.approval_status === "approved_reference").length ?? 0;
      return <article key={machine.id}><div className="gpost-machine-icon" aria-hidden="true">◆</div><div><h2>{machine.name}</h2><p>{machine.manufacturer} {machine.model}</p><div className="gpost-machine-tags"><span>{machine.machine_type.replaceAll("_", " ")}</span><span>{machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</span></div><dl><div><dt>Profile revision</dt><dd>v{revision?.revision_number ?? "—"} · {revision?.status ?? "missing"}</dd></div><div><dt>Documents</dt><dd>{context?.documents.length ?? "—"}</dd></div><div><dt>Reference programs</dt><dd>{approved}</dd></div><div><dt>Profile coverage</dt><dd>{profileCoverage(machine, revision)}%</dd></div></dl></div><button className="button primary" disabled={!context} onClick={() => chooseMachine(machine)}>Select</button></article>;
    })}</section>}
    {step === "readiness" && selectedMachine && <section className="gpost-readiness-screen">
      <header><div><span className="machine-type">{selectedMachine.machine_type.replaceAll("_", " ")}</span><h2>{selectedMachine.name}</h2><p>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</p></div><strong>{blockingIssues.length ? "NOT READY" : "READY FOR R&D SETUP"}</strong></header>
      <div className="gpost-readiness-columns"><section><h3>Ready Sources</h3><ul><li className="ready">✓ Machine profile · v{selectedRevision?.revision_number}</li><li className="ready">✓ Controller identified</li><li className="ready">✓ {selectedContext?.documents.length ?? 0} reference documents</li><li className="ready">✓ {approvedReferences.length} approved reference programs</li><li className="ready">✓ {selectedRevision?.axis_count ?? selectedMachine.axis_count} axis configuration</li></ul></section><section><h3>Needs Review</h3><ul>{unresolvedCount ? <li className="warning">⚠ {unresolvedCount} machine profile fields unresolved</li> : <li className="ready">✓ No unresolved profile fields recorded</li>}<li className="warning">⚠ Tool-change convention requires mapping review</li>{!approvedReferences.length && <li className="warning">⚠ No approved reference program selected</li>}</ul></section><section><h3>Blocking Issues</h3><ul>{blockingIssues.length ? blockingIssues.map((item) => <li className="blocking" key={item}>× {item}</li>) : <li className="ready">None</li>}</ul></section></div>
      <footer><button onClick={() => setStep("machines")}>Back</button><Link to={`/machines/${selectedMachine.id}/revisions`}>Review Machine Profile</Link><Link to={`/documents?machine=${selectedMachine.id}`}>View Documents</Link><button className="button primary" disabled={Boolean(blockingIssues.length)} onClick={() => setStep("details")}>Continue Setup</button></footer>
    </section>}
    {step === "details" && selectedMachine && <section className="gpost-draft-confirm panel"><div><h2>Draft identity</h2><label>Draft Name<input autoFocus value={draftName} onChange={(event) => setDraftName(event.target.value)} /></label><label>Template Family<select value={family} onChange={(event) => setFamily(event.target.value)}><option value="fanuc_lathe">FANUC Lathe</option><option value="fanuc_mill">FANUC Mill</option><option value="haas_mill">Haas Mill</option><option value="generic_research">Generic Research</option></select></label></div><dl><div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Controller</dt><dd>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</dd></div><div><dt>Profile Revision</dt><dd>v{selectedRevision?.revision_number} · {selectedRevision?.status}</dd></div><div><dt>Selected sources</dt><dd>{selectedContext?.documents.length ?? 0} documents · {approvedReferences.length} approved programs</dd></div></dl><footer><button onClick={() => setStep("readiness")}>Back</button><button className="button primary" disabled={busy || !draftName.trim()} onClick={() => void createDraft()}>{busy ? "Creating…" : "Create Draft"}</button></footer></section>}
  </section>;

  return <section className="page gpost-home-page">
    <PageHeader eyebrow="Machine-specific post configuration" title="G-POST Generator"
      description="Build, review, and test machine-specific post configurations."
      action={<button className="button primary" onClick={() => void openCreate()}>+ Create G-POST</button>} />
    <SafetyBanner title="R&D post-development workspace" message="All drafts and generated output are non-production and not validated for machine use. Qualified post review, simulation, and controlled approval remain required." />
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="gpost-drafts-section"><header><div><h2>G-POST Drafts</h2><p>Versioned machine configurations and their current engineering review state.</p></div><span>{drafts.length} configurations</span></header>
      {!drafts.length ? <div className="gpost-empty-state"><span aria-hidden="true">⚙</span><h2>No G-POST configurations yet</h2><p>Create a machine-specific draft using an existing machine profile, manuals, controller documentation, and reference programs.</p><div><button className="button primary" onClick={() => void openCreate()}>Create G-POST</button><Link to="/machines">View Machine Profiles</Link></div></div> : <div className="gpost-draft-table-wrap"><table className="gpost-draft-table"><thead><tr><th>Name</th><th>Machine</th><th>Controller</th><th>Version</th><th>Status</th><th>Mappings</th><th>Warnings</th><th>Last Updated</th><th>Actions</th></tr></thead><tbody>{draftRows.map(({ draft, mappings, machine, reviewed }) => <tr key={draft.id}><td><strong>{draft.name}</strong><small>R&D configuration</small></td><td>{machine?.name ?? `Machine #${draft.machine_profile_id}`}<small>{draft.machine_type.replaceAll("_", " ")}</small></td><td>{machine?.controller_manufacturer || machine?.controller_name || draft.controller_family}<small>{machine?.controller_model || draft.controller_family.replaceAll("_", " ")}</small></td><td><strong>v{draft.version}</strong></td><td><GPostStatusBadge status={draft.status} /></td><td><strong>{reviewed}/{mappings.length}</strong><small>reviewed</small></td><td><span className={draft.warnings_json.length ? "gpost-warning-count" : "gpost-zero-count"}>{draft.warnings_json.length}</span></td><td>{friendlyDate(draft.updated_at)}</td><td><Link className="gpost-open-link" to={`/gpost/${draft.id}`}>Open <span aria-hidden="true">→</span></Link></td></tr>)}</tbody></table></div>}
    </section>
  </section>;
}
