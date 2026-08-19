import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { ActionMenu } from "../components/ActionMenu";
import { PageHeader } from "../components/PageHeader";
import type { AssembledPostDraft, GPostDraft, MachineProfile, MachineProfileRevision, SourceDocument } from "../types";

type MachineContext = { revisions: MachineProfileRevision[]; documents: SourceDocument[]; verifiedTranslations: number };
type CreateStep = "machines" | "setup" | "create";
type Dialog = { kind: "rename" | "delete"; draft: GPostDraft; value: string; error?: string } | null;

const activeStatuses = new Set(["draft", "under_review", "review_required", "validated_for_rnd"]);
const overallLabels: Record<string, string> = { setup: "Setup", building: "Building", needs_information: "Needs Information", ready_for_review: "Ready for Review", reviewed_rnd_draft: "Reviewed R&D Draft", archived: "Archived" };

function foundation(machine: MachineProfile) {
  const controller = `${machine.controller_manufacturer || ""} ${machine.controller_name || ""}`.toLowerCase();
  const lathe = ["lathe", "turning_center", "vertical_lathe"].includes(machine.machine_type);
  if (controller.includes("haas") && !lathe) return { key: "haas_mill", label: "Haas Mill" };
  if (controller.includes("fanuc")) return { key: lathe ? "fanuc_lathe" : "fanuc_mill", label: lathe ? "FANUC Lathe" : "FANUC Mill" };
  return { key: "generic_research", label: "Generic Research" };
}
function dateLabel(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }

export function GPostGeneratorPage() {
  const navigate = useNavigate(); const [params] = useSearchParams(); const preselected = useRef(false);
  const [machines, setMachines] = useState<MachineProfile[]>([]); const [drafts, setDrafts] = useState<GPostDraft[]>([]);
  const [assemblies, setAssemblies] = useState<Record<number, AssembledPostDraft>>({}); const [contexts, setContexts] = useState<Record<number, MachineContext>>({});
  const [createOpen, setCreateOpen] = useState(false); const [step, setStep] = useState<CreateStep>("machines");
  const [machineId, setMachineId] = useState(0); const [revisionId, setRevisionId] = useState(0); const [postName, setPostName] = useState("");
  const [search, setSearch] = useState(""); const [machineFilter, setMachineFilter] = useState("all"); const [statusFilter, setStatusFilter] = useState("all");
  const [visibility, setVisibility] = useState("active"); const [sort, setSort] = useState("updated"); const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");

  async function loadLanding() {
    setError("");
    try {
      const machineRows = await api.listProfiles(); const grouped = await Promise.all(machineRows.map((item) => api.listGPostDrafts(item.id)));
      const all = grouped.flat(); setMachines(machineRows); setDrafts(all);
      if (typeof api.getAssembledPost === "function") {
        const states = await Promise.all(all.map(async (draft) => { try { return [draft.id, await api.getAssembledPost(draft.id)] as const; } catch { return null; } }));
        setAssemblies(Object.fromEntries(states.filter(Boolean) as Array<readonly [number, AssembledPostDraft]>));
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load posts."); }
  }
  useEffect(() => { void loadLanding(); }, []);

  async function openCreate(preselectedId?: number) {
    setCreateOpen(true); setStep("machines"); setMachineId(0); setError("");
    try {
      const rows = await Promise.all(machines.map(async (machine) => [machine.id, { revisions: await api.listProfileRevisions(machine.id), documents: await api.listDocuments(machine.id), verifiedTranslations: 0 }] as const));
      const next = Object.fromEntries(rows); setContexts(next);
      const chosen = machines.find((item) => item.id === preselectedId); if (chosen) chooseMachine(chosen, next[chosen.id]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine setup."); }
  }
  function chooseMachine(machine: MachineProfile, supplied?: MachineContext) {
    const context = supplied ?? contexts[machine.id]; const revision = context?.revisions.find((item) => item.id === machine.active_revision_id) ?? context?.revisions.find((item) => item.status === "approved");
    setMachineId(machine.id); setRevisionId(revision?.id ?? 0); setPostName(`${machine.model} ${machine.controller_manufacturer || machine.controller_name} Post`); setStep("setup");
  }
  useEffect(() => { const id = Number(params.get("machine")); if (!preselected.current && id && machines.some((item) => item.id === id)) { preselected.current = true; void openCreate(id); } }, [machines]);

  async function createPost() {
    const context = contexts[machineId]; const machine = machines.find((item) => item.id === machineId); if (!context || !machine || !revisionId) return;
    setBusy(true); setError("");
    try { const created = await api.createGPostDraft(machineId, { machine_profile_revision_id: revisionId, name: postName.trim(), controller_family: foundation(machine).key, selected_document_ids: context.documents.filter((item) => item.processing_status === "ready").map((item) => item.id), reference_program_ids: [] }); navigate(`/gpost/${created.id}`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Post creation failed."); } finally { setBusy(false); }
  }
  async function archive(draft: GPostDraft) { try { await api.archiveGPostDraft(draft.id); await loadLanding(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Archive failed."); } }
  async function duplicate(draft: GPostDraft) { try { const created = await api.duplicateGPostDraft(draft.id); await loadLanding(); navigate(`/gpost/${created.id}`); } catch (cause) { setError(cause instanceof Error ? cause.message : "Duplicate failed."); } }
  async function confirmDialog() {
    if (!dialog) return; setBusy(true);
    try {
      if (dialog.kind === "rename") await api.updateGPostDraft(dialog.draft.id, { name: dialog.value.trim() });
      else await api.deleteGPostDraft(dialog.draft.id);
      setDialog(null); await loadLanding();
    } catch (cause) { setDialog({ ...dialog, error: cause instanceof Error ? cause.message : "Action failed." }); } finally { setBusy(false); }
  }

  const selectedMachine = machines.find((item) => item.id === machineId); const selectedContext = contexts[machineId];
  const selectedRevision = selectedContext?.revisions.find((item) => item.id === revisionId); const selectedFoundation = selectedMachine ? foundation(selectedMachine) : null;
  const eligibleCount = selectedContext?.documents.filter((item) => item.ai_post_builder_allowed).length ?? 0;
  const rows = useMemo(() => drafts.map((draft) => ({ draft, machine: machines.find((item) => item.id === draft.machine_profile_id), assembly: assemblies[draft.id] })).filter(({ draft, machine, assembly }) => {
    const text = `${draft.name} ${machine?.name ?? ""}`.toLowerCase(); if (search && !text.includes(search.toLowerCase())) return false;
    if (machineFilter !== "all" && draft.machine_profile_id !== Number(machineFilter)) return false;
    if (visibility === "active" && !activeStatuses.has(draft.status)) return false; if (visibility === "archived" && draft.status !== "archived") return false;
    return statusFilter === "all" || (assembly?.status ?? draft.status) === statusFilter;
  }).sort((a, b) => sort === "name" ? a.draft.name.localeCompare(b.draft.name) : sort === "machine" ? (a.machine?.name ?? "").localeCompare(b.machine?.name ?? "") : sort === "status" ? (a.assembly?.status ?? a.draft.status).localeCompare(b.assembly?.status ?? b.draft.status) : b.draft.updated_at.localeCompare(a.draft.updated_at)), [drafts, machines, assemblies, search, machineFilter, visibility, statusFilter, sort]);

  if (createOpen) return <section className="page gpost-home-page v1-post-create">
    <PageHeader eyebrow={`Create Post · Step ${step === "machines" ? 1 : step === "setup" ? 2 : 3} of 3`} title={step === "machines" ? "Select Machine" : step === "setup" ? "Post Setup" : "Create Post"} description="Create one machine-specific R&D post configuration." action={<button className="button secondary" onClick={() => setCreateOpen(false)}>Cancel</button>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="gpost-create-progress" aria-label="Create progress"><span className={step === "machines" ? "active" : "complete"}>1 <b>Machine</b></span><span className={step === "setup" ? "active" : step === "create" ? "complete" : ""}>2 <b>Post Setup</b></span><span className={step === "create" ? "active" : ""}>3 <b>Create Post</b></span></div>
    {step === "machines" && <section className="gpost-machine-selection" aria-label="Machine profiles">{machines.map((machine) => { const context = contexts[machine.id]; const revision = context?.revisions.find((item) => item.id === machine.active_revision_id); const unresolved = revision?.capabilities_json?.unresolved_fields; const needs = Array.isArray(unresolved) && unresolved.length > 0; return <article key={machine.id}><div className="gpost-machine-icon" aria-hidden="true">◆</div><div><h2>{machine.name}</h2><p>{machine.machine_type.replaceAll("_", " ")} · {machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</p><dl><div><dt>Machine Knowledge</dt><dd>{needs ? "Needs Information" : "Ready"}</dd></div><div><dt>Documents</dt><dd>{context?.documents.length ?? "—"}</dd></div></dl></div><button className="button primary" disabled={!context} onClick={() => chooseMachine(machine)}>Select</button></article>; })}</section>}
    {step === "setup" && selectedMachine && <section className="panel post-setup-summary"><h2>Post Setup</h2><dl><div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Controller</dt><dd>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</dd></div><div><dt>Machine Knowledge</dt><dd>{selectedRevision ? "Ready for initial setup" : "Needs Information"}</dd></div><div><dt>Documents</dt><dd>{selectedContext?.documents.length ?? 0} attached</dd></div><div><dt>Post Foundation <span title="Provides the starting structure for this machine/controller type. Machine-specific rules are built and reviewed in this post.">ⓘ</span></dt><dd>{selectedFoundation?.label}</dd></div><div><dt>Warnings</dt><dd>{selectedRevision ? "None" : "Current machine configuration is unavailable"}</dd></div></dl><footer><button className="button secondary" onClick={() => setStep("machines")}>Back</button><Link className="button tertiary" to={`/machines/${selectedMachine.id}/revisions`}>View Technical Details</Link><button className="button primary" disabled={!selectedRevision} onClick={() => setStep("create")}>Continue</button></footer></section>}
    {step === "create" && selectedMachine && <section className="gpost-draft-confirm panel"><div><h2>Post identity</h2><label>Post Name<input autoFocus value={postName} onChange={(event) => setPostName(event.target.value)} /></label><label>Post Foundation <span title="Automatically selected from the machine type and controller.">ⓘ</span><input value={selectedFoundation?.label ?? ""} readOnly /></label></div><dl><div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Machine Configuration</dt><dd>Current <span title={`Revision v${selectedRevision?.revision_number} · ${selectedRevision?.status}`}>ⓘ</span></dd></div><div><dt>Machine Sources</dt><dd>{selectedContext?.documents.length ?? 0} documents</dd></div><div><dt>AI-Eligible Sources</dt><dd>{eligibleCount}</dd></div></dl><footer><button className="button secondary" onClick={() => setStep("setup")}>Back</button><button className="button primary" disabled={busy || !postName.trim()} onClick={() => void createPost()}>{busy ? "Creating…" : "Create Post"}</button></footer></section>}
  </section>;

  return <section className="page gpost-home-page v1-post-list">
    <PageHeader eyebrow="Machine-specific R&D post configuration" title="Post Builder" description="Build, review, and version one complete post configuration for each machine." action={<button aria-label="Create Post" className="button primary" onClick={() => void openCreate()}>+ Create Post</button>} />
    <aside className="compact-governance"><strong>AI ASSISTS POST DEVELOPMENT ONLY</strong><span>CL/NCL, part geometry, toolpaths, and production programs are excluded from AI context.</span><Link to="/docs/post-builder-ai-context">Learn More</Link></aside>
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="post-list-controls" aria-label="Post filters"><label>Search<input value={search} placeholder="Search posts or machines" onChange={(event) => setSearch(event.target.value)} /></label><label>Machine<select value={machineFilter} onChange={(event) => setMachineFilter(event.target.value)}><option value="all">All machines</option>{machines.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All statuses</option>{Object.entries(overallLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label>View<select value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="active">Active</option><option value="archived">Archived</option><option value="all">All</option></select></label><label>Sort<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="updated">Recently Updated</option><option value="name">Name</option><option value="machine">Machine</option><option value="status">Status</option></select></label></section>
    <section className="gpost-drafts-section"><header><div><h2>Posts</h2><p>Current machine-level configurations. Historical versions stay inside their logical post.</p></div><span>{rows.length} shown</span></header>
      {!rows.length ? <div className="gpost-empty-state"><h2>No posts match these filters.</h2><p>Adjust the filters or create a new machine-specific post.</p><button className="button primary" onClick={() => void openCreate()}>Create Post</button></div> : <div className="gpost-draft-table-wrap"><table className="gpost-draft-table"><thead><tr><th>Post</th><th>Machine</th><th>Status</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{rows.map(({ draft, machine, assembly }) => <tr key={draft.id}><td><strong>{draft.name}</strong><small>{draft.status === "archived" ? "Archived" : draft.status === "superseded" ? `Historical · v${draft.version}` : "Current Draft"}</small></td><td>{machine?.name ?? `Machine #${draft.machine_profile_id}`}<small>{machine?.machine_type.replaceAll("_", " ")} · {machine?.controller_model || machine?.controller_name || draft.controller_family}</small></td><td><span className={`post-status ${assembly?.status ?? draft.status}`}>{overallLabels[assembly?.status ?? ""] ?? (draft.status === "archived" ? "Archived" : draft.status === "superseded" ? "Superseded" : "Building")}</span></td><td>{dateLabel(draft.updated_at)}</td><td><div className="row-actions"><Link className="button secondary" to={`/gpost/${draft.id}`}>Open</Link><ActionMenu label={`More actions for ${draft.name}`} items={[{ label: "Rename", onSelect: () => setDialog({ kind: "rename", draft, value: draft.name }) }, { label: "Duplicate", onSelect: () => void duplicate(draft) }, ...(draft.status !== "archived" ? [{ label: "Archive", onSelect: () => void archive(draft) }] : []), { label: "Delete", danger: true, divider: true, onSelect: () => setDialog({ kind: "delete", draft, value: draft.name }) }]} /></div></td></tr>)}</tbody></table></div>}
    </section>
    {dialog && <div className="confirmation-backdrop" role="presentation"><section className="confirmation-dialog" role="dialog" aria-modal="true" aria-labelledby="post-dialog-title"><h2 id="post-dialog-title">{dialog.kind === "rename" ? "Rename Post" : `Delete “${dialog.draft.name}”?`}</h2>{dialog.kind === "rename" ? <label>Post Name<input autoFocus value={dialog.value} onChange={(event) => setDialog({ ...dialog, value: event.target.value })} /></label> : <p>This removes the active R&amp;D draft. Posts with immutable version history must be archived instead.</p>}{dialog.error && <p className="form-error">{dialog.error}</p>}<footer><button className="button secondary" onClick={() => setDialog(null)}>Cancel</button><button className={`button ${dialog.kind === "delete" ? "danger" : "primary"}`} disabled={busy || !dialog.value.trim()} onClick={() => void confirmDialog()}>{dialog.kind === "delete" ? "Delete Post" : "Save Name"}</button></footer></section></div>}
  </section>;
}
