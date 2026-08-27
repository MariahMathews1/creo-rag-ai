import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { ActionMenu } from "../components/ActionMenu";
import { PageHeader } from "../components/PageHeader";
import type { GPostDraft, MachineProfile, MachineProfileRevision, PostRecordSummary, SourceDocument } from "../types";

type MachineContext = { revisions: MachineProfileRevision[]; documents: SourceDocument[] };
type CreateStep = "machine" | "setup" | "create";
type Dialog = { kind: "rename" | "delete"; draft: GPostDraft; value: string; error?: string } | null;

const statusLabels: Record<string, string> = {
  draft: "Building", setup: "Setup", building: "Building", needs_information: "Needs Information",
  ready_for_review: "Ready for Review", ready_for_engineering_review: "Ready for Review",
  under_review: "Ready for Review", review_required: "Needs Information", under_validation: "Under Validation",
  validated_for_rnd: "R&D Validated", rnd_validated: "R&D Validated", archived: "Archived",
};

function startingPoint(machine: MachineProfile) {
  const controller = `${machine.controller_manufacturer || ""} ${machine.controller_name || ""}`.toLowerCase();
  const lathe = ["lathe", "turning_center", "vertical_lathe"].includes(machine.machine_type);
  if (controller.includes("haas") && !lathe) return { key: "haas_mill", label: "Haas Mill" };
  if (controller.includes("fanuc")) return { key: lathe ? "fanuc_lathe" : "fanuc_mill", label: lathe ? "FANUC Lathe" : "FANUC Mill" };
  return { key: "generic_research", label: "Generic OFG Initialization Reference" };
}

export function GPostGeneratorPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const preselected = useRef(false);
  const [machines, setMachines] = useState<MachineProfile[]>([]);
  const [posts, setPosts] = useState<GPostDraft[]>([]);
  const [summaries, setSummaries] = useState<Record<number, PostRecordSummary>>({});
  const [contexts, setContexts] = useState<Record<number, MachineContext>>({});
  const [siteStandardCount, setSiteStandardCount] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const [step, setStep] = useState<CreateStep>("machine");
  const [machineId, setMachineId] = useState(0);
  const [revisionId, setRevisionId] = useState(0);
  const [postName, setPostName] = useState("");
  const [search, setSearch] = useState("");
  const [machineFilter, setMachineFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadLanding() {
    setError("");
    try {
      const machineRows = await api.listProfiles();
      const grouped = await Promise.all(machineRows.map((machine) => api.listGPostDrafts(machine.id)));
      const allPosts = grouped.flat().filter((post) => post.status !== "superseded");
      setMachines(machineRows); setPosts(allPosts);
      const nextSummaries = await Promise.all(allPosts.map(async (post) => {
        try { return [post.id, await api.getPostRecordSummary(post.id)] as const; } catch { return null; }
      }));
      setSummaries(Object.fromEntries(nextSummaries.filter(Boolean) as Array<readonly [number, PostRecordSummary]>));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load posts."); }
  }
  useEffect(() => { void loadLanding(); }, []);

  async function openCreate(preselectedId?: number) {
    setCreateOpen(true); setStep("machine"); setMachineId(0); setError("");
    try {
      const [rows, standards] = await Promise.all([
        Promise.all(machines.map(async (machine) => [machine.id, { revisions: await api.listProfileRevisions(machine.id), documents: await api.listDocuments(machine.id) }] as const)),
        api.listSiteStandards(),
      ]);
      const next = Object.fromEntries(rows); setContexts(next); setSiteStandardCount(standards.length);
      const chosen = machines.find((machine) => machine.id === preselectedId);
      if (chosen) chooseMachine(chosen, next[chosen.id]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine setup."); }
  }
  function chooseMachine(machine: MachineProfile, supplied?: MachineContext) {
    const context = supplied ?? contexts[machine.id];
    const revision = context?.revisions.find((item) => item.id === machine.active_revision_id) ?? context?.revisions.find((item) => item.status === "approved");
    setMachineId(machine.id); setRevisionId(revision?.id ?? 0);
    setPostName(`${machine.model} ${machine.controller_manufacturer || machine.controller_name} Post`);
    setStep("setup");
  }
  useEffect(() => {
    const id = Number(params.get("machine"));
    if (!preselected.current && id && machines.some((machine) => machine.id === id)) { preselected.current = true; void openCreate(id); }
  }, [machines]);

  async function createPost() {
    const context = contexts[machineId]; const machine = machines.find((item) => item.id === machineId);
    if (!context || !machine || !revisionId) return;
    setBusy(true); setError("");
    try {
      const created = await api.createGPostDraft(machineId, {
        machine_profile_revision_id: revisionId, name: postName.trim(), controller_family: startingPoint(machine).key,
        selected_document_ids: context.documents.filter((document) => document.processing_status === "ready").map((document) => document.id), reference_program_ids: [],
      });
      navigate(`/gpost/${created.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Post creation failed."); }
    finally { setBusy(false); }
  }
  async function createVersion(post: GPostDraft) {
    try { const created = await api.createGPostVersion(post.id); navigate(`/gpost/${created.id}/versions`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Version creation failed."); }
  }
  async function archive(post: GPostDraft) {
    try { await api.archiveGPostDraft(post.id); await loadLanding(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Archive failed."); }
  }
  async function confirmDialog() {
    if (!dialog) return; setBusy(true);
    try {
      if (dialog.kind === "rename") await api.updateGPostDraft(dialog.draft.id, { name: dialog.value.trim() });
      else await api.deleteGPostDraft(dialog.draft.id);
      setDialog(null); await loadLanding();
    } catch (cause) { setDialog({ ...dialog, error: cause instanceof Error ? cause.message : "Action failed." }); }
    finally { setBusy(false); }
  }

  const selectedMachine = machines.find((machine) => machine.id === machineId);
  const selectedContext = contexts[machineId];
  const selectedRevision = selectedContext?.revisions.find((revision) => revision.id === revisionId);
  const selectedStartingPoint = selectedMachine ? startingPoint(selectedMachine) : null;
  const rows = useMemo(() => posts.filter((post) => {
    const machine = machines.find((item) => item.id === post.machine_profile_id);
    const summaryStatus = summaries[post.id]?.status ?? post.status;
    return (!search || `${post.name} ${machine?.name || ""}`.toLowerCase().includes(search.toLowerCase()))
      && (machineFilter === "all" || post.machine_profile_id === Number(machineFilter))
      && (statusFilter === "all" || summaryStatus === statusFilter);
  }).sort((a, b) => b.updated_at.localeCompare(a.updated_at)), [posts, machines, summaries, search, machineFilter, statusFilter]);

  if (createOpen) return <section className="page gpost-home-page v1-post-create">
    <PageHeader eyebrow={`Create Post · Step ${step === "machine" ? 1 : step === "setup" ? 2 : 3} of 3`} title={step === "machine" ? "Select Machine" : step === "setup" ? "Post Setup" : "Create Post"} description="Create a machine-specific Post Record." action={<button className="button secondary" onClick={() => setCreateOpen(false)}>Cancel</button>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="gpost-create-progress" aria-label="Create progress"><span className={step === "machine" ? "active" : "complete"}>1 <b>Machine</b></span><span className={step === "setup" ? "active" : step === "create" ? "complete" : ""}>2 <b>Post Setup</b></span><span className={step === "create" ? "active" : ""}>3 <b>Create Post</b></span></div>
    {step === "machine" && <section className="gpost-machine-selection" aria-label="Machine profiles">{machines.map((machine) => <article key={machine.id}><div className="gpost-machine-icon" aria-hidden="true">◆</div><div><h2>{machine.name}</h2><p>{machine.machine_type.replaceAll("_", " ")} · {machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</p></div><button className="button primary" disabled={!contexts[machine.id]} onClick={() => chooseMachine(machine)}>Select</button></article>)}</section>}
    {step === "setup" && selectedMachine && <section className="panel post-setup-summary"><h2>Post Setup</h2><dl>
      <div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Machine Type</dt><dd>{selectedMachine.machine_type.replaceAll("_", " ")}</dd></div><div><dt>Controller</dt><dd>{selectedMachine.controller_manufacturer || selectedMachine.controller_name} {selectedMachine.controller_model || ""}</dd></div>
      <div><dt>Documents</dt><dd>{selectedContext?.documents.length ?? 0} available</dd></div><div><dt>Machine Knowledge</dt><dd>{selectedRevision ? "Available" : "Needs Information"}</dd></div>
      <div><dt>Suggested OFG Starting Point</dt><dd>{selectedStartingPoint?.label}</dd></div><div><dt>Site Standards</dt><dd>{siteStandardCount} available</dd></div>
      <div><dt>Verification</dt><dd>Local G-POST verification required</dd></div>
    </dl><footer><button className="button secondary" onClick={() => setStep("machine")}>Back</button><button className="button primary" disabled={!selectedRevision} onClick={() => setStep("create")}>Continue</button></footer></section>}
    {step === "create" && selectedMachine && <section className="gpost-draft-confirm panel"><div><h2>Post identity</h2><label>Post Name<input autoFocus value={postName} onChange={(event) => setPostName(event.target.value)} /></label></div><dl>
      <div><dt>Machine</dt><dd>{selectedMachine.name}</dd></div><div><dt>Suggested OFG Starting Point</dt><dd>{selectedStartingPoint?.label}</dd></div><div><dt>Documents</dt><dd>{selectedContext?.documents.length ?? 0} selected</dd></div>
    </dl><footer><button className="button secondary" onClick={() => setStep("setup")}>Back</button><button className="button primary" disabled={busy || !postName.trim()} onClick={() => void createPost()}>{busy ? "Creating…" : "Create Post"}</button></footer></section>}
  </section>;

  return <section className="page gpost-home-page v1-post-list">
    <PageHeader eyebrow="Machine-specific post development" title="Post Builder" description="Build, review, and version each machine-specific post." action={<button aria-label="Create Post" className="button primary" onClick={() => void openCreate()}>+ Create Post</button>} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="post-list-controls" aria-label="Post filters"><label>Search<input value={search} placeholder="Search posts or machines" onChange={(event) => setSearch(event.target.value)} /></label><label>Machine<select value={machineFilter} onChange={(event) => setMachineFilter(event.target.value)}><option value="all">All machines</option>{machines.map((machine) => <option value={machine.id} key={machine.id}>{machine.name}</option>)}</select></label><label>Status<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="all">All statuses</option>{["setup", "building", "needs_information", "ready_for_engineering_review", "under_validation", "rnd_validated", "archived"].map((status) => <option value={status} key={status}>{statusLabels[status]}</option>)}</select></label></section>
    <section className="gpost-drafts-section"><header><div><h2>Posts</h2><p>Current Post Records and their next engineering action.</p></div><span>{rows.length} shown</span></header>
      {!rows.length ? <div className="gpost-empty-state"><h2>No posts match these filters.</h2><p>Adjust the filters or create a post.</p><button className="button primary" onClick={() => void openCreate()}>Create Post</button></div> : <div className="gpost-draft-table-wrap"><table className="gpost-draft-table"><thead><tr><th>Post</th><th>Machine</th><th>Controller</th><th>Status</th><th>Next Action</th><th>Updated</th><th>Action</th></tr></thead><tbody>{rows.map((post) => {
        const machine = machines.find((item) => item.id === post.machine_profile_id); const summary = summaries[post.id]; const status = summary?.status ?? post.status;
        return <tr key={post.id}><td><strong>{post.name}</strong></td><td>{machine?.name ?? `Machine #${post.machine_profile_id}`}</td><td>{machine?.controller_model || machine?.controller_name || post.controller_family}</td><td><span className={`post-status ${status}`}>{statusLabels[status] || "Building"}</span></td><td>{summary?.next_action.label || "Continue setup"}</td><td>{new Date(post.updated_at).toLocaleDateString()}</td><td><div className="row-actions"><Link className="button secondary" to={`/gpost/${post.id}`}>Open</Link><ActionMenu label={`More actions for ${post.name}`} items={[
          { label: "Rename", onSelect: () => setDialog({ kind: "rename", draft: post, value: post.name }) },
          { label: "Create Version", onSelect: () => void createVersion(post) },
          ...(post.status !== "archived" ? [{ label: "Archive", onSelect: () => void archive(post) }] : []),
          { label: "Export Development Package", onSelect: () => window.location.assign(api.postDevelopmentPackageUrl(post.id, "markdown")) },
          { label: "Delete", danger: true, divider: true, onSelect: () => setDialog({ kind: "delete", draft: post, value: post.name }) },
        ]} /></div></td></tr>;
      })}</tbody></table></div>}
    </section>
    {dialog && <div className="confirmation-backdrop" role="presentation"><section className="confirmation-dialog" role="dialog" aria-modal="true" aria-labelledby="post-dialog-title"><h2 id="post-dialog-title">{dialog.kind === "rename" ? "Rename Post" : `Delete “${dialog.draft.name}”?`}</h2>{dialog.kind === "rename" ? <label>Post Name<input autoFocus value={dialog.value} onChange={(event) => setDialog({ ...dialog, value: event.target.value })} /></label> : <p>This removes the active draft. Posts with retained versions must be archived.</p>}{dialog.error && <p className="form-error">{dialog.error}</p>}<footer><button className="button secondary" onClick={() => setDialog(null)}>Cancel</button><button className={`button ${dialog.kind === "delete" ? "danger" : "primary"}`} disabled={busy || !dialog.value.trim()} onClick={() => void confirmDialog()}>{dialog.kind === "delete" ? "Delete Post" : "Save Name"}</button></footer></section></div>}
  </section>;
}
