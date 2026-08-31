import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { ActionMenu } from "../components/ActionMenu";
import { PageHeader } from "../components/PageHeader";
import { MachineProfileForm } from "../features/machines/MachineProfileForm";
import type { GPostDraft, MachineKnowledgeFact, MachineProfile, MachineProfileInput, SourceDocument } from "../types";

const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const isDemo = (profile: MachineProfile) => /\b(demo|fictional|test)\b/i.test(`${profile.name} ${profile.manufacturer} ${profile.notes || ""}`);
type LifecycleFilter = "active" | "archived" | "all";
function knowledgeLabel(facts: MachineKnowledgeFact[]) {
  if (!facts.length) return "No Information";
  const missing = facts.filter((fact) => fact.status === "unknown").length;
  if (missing) return `Needs ${missing} Value${missing === 1 ? "" : "s"}`;
  if (facts.some((fact) => ["needs_review", "conflicting"].includes(fact.status))) return "Needs Review";
  return "Ready";
}

export function MachineProfilesPage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [editing, setEditing] = useState<MachineProfile | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [postRecords, setPostRecords] = useState<Record<number, GPostDraft[]>>({});
  const [documents, setDocuments] = useState<Record<number, SourceDocument[]>>({});
  const [knowledge, setKnowledge] = useState<Record<number, MachineKnowledgeFact[]>>({});
  const [lifecycleFilter, setLifecycleFilter] = useState<LifecycleFilter>("active");
  const [deleting, setDeleting] = useState<MachineProfile | null>(null);
  const [deleteError, setDeleteError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    return api
      .listProfiles(true)
      .then(async (items) => {
        setProfiles(items);
        const related = await Promise.all(items.map(async (profile) => {
          const [posts, profileDocuments] = await Promise.all([api.listGPostDrafts(profile.id), api.listDocuments(profile.id)]);
          const current = posts.find((post) => !["superseded", "archived"].includes(post.status));
          const facts = current ? await api.listMachineKnowledge(current.id).catch(() => []) : [];
          return { id: profile.id, posts, documents: profileDocuments, facts };
        }));
        setPostRecords(Object.fromEntries(related.map((item) => [item.id, item.posts])));
        setDocuments(Object.fromEntries(related.map((item) => [item.id, item.documents])));
        setKnowledge(Object.fromEntries(related.map((item) => [item.id, item.facts])));
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "Unable to load profiles."),
      )
      .finally(() => setLoading(false));
  };
  useEffect(() => { void load(); }, []);

  async function save(value: MachineProfileInput) {
    if (editing) await api.updateProfile(editing.id, value);
    else {
      const created = await api.createProfile(value);
      navigate(`/machines/${created.id}`);
      return;
    }
    setShowForm(false);
    setEditing(null);
    await load();
  }

  async function archive(profile: MachineProfile) {
    setError("");
    try { await api.archiveProfile(profile.id); setDeleting(null); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to archive machine."); }
  }

  async function restore(profile: MachineProfile) {
    setError("");
    try { await api.restoreProfile(profile.id); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to restore machine."); }
  }

  async function confirmDelete() {
    if (!deleting) return;
    setDeleteError("");
    try { await api.deleteProfile(deleting.id); setDeleting(null); await load(); }
    catch (cause) { setDeleteError(cause instanceof Error ? cause.message : "Unable to delete machine."); }
  }

  if (showForm) {
    return (
      <section className="page">
        <PageHeader eyebrow="Machine configuration" title={editing ? "Edit Machine" : "Add Machine"} description="Enter the machine and controller identity used throughout the engineering workflow." />
        <MachineProfileForm simple profile={editing} onSubmit={save} onCancel={() => { setShowForm(false); setEditing(null); }} />
      </section>
    );
  }
  const deletionBlocked = Boolean(deleting && ((postRecords[deleting.id]?.length ?? 0) > 0 || deleteError.includes("cannot be deleted")));

  return (
    <section className="page">
      <PageHeader
        eyebrow="Configuration"
        title="Machines"
        description="Machine identity, controller context, reviewed information, source documents, and associated Post Records."
        action={<button className="button primary" onClick={() => setShowForm(true)}>+ Add Machine</button>}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="machine-lifecycle-filter" role="group" aria-label="Machine status filter">{(["active", "archived", "all"] as LifecycleFilter[]).map((value) => <button key={value} type="button" className={lifecycleFilter === value ? "active" : ""} aria-pressed={lifecycleFilter === value} onClick={() => setLifecycleFilter(value)}>{pretty(value)}</button>)}</div>
      {loading ? <p className="loading" role="status">Loading machine profiles…</p> : profiles.filter((profile) => lifecycleFilter === "all" || (lifecycleFilter === "archived" ? Boolean(profile.archived_at) : !profile.archived_at)).length === 0 ? (
        <div className="empty-state"><span>◆</span><h2>No machines yet</h2><p>Add a machine before generating or reviewing G-code.</p><button className="button primary" onClick={() => setShowForm(true)}>Add Machine</button></div>
      ) : <div className="panel table-wrap compact-machine-list"><table><thead><tr><th>Machine</th><th>Type</th><th>Controller</th><th>Documents</th><th>Machine Info</th><th>Posts</th><th>Actions</th></tr></thead><tbody>{profiles.filter((profile) => lifecycleFilter === "all" || (lifecycleFilter === "archived" ? Boolean(profile.archived_at) : !profile.archived_at)).map((profile) => { const label = knowledgeLabel(knowledge[profile.id] || []); return <tr className="clickable-machine-row" key={profile.id} tabIndex={0} onClick={() => navigate(`/machines/${profile.id}`)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") navigate(`/machines/${profile.id}`); }}><td><div className="machine-cell-primary"><strong>{profile.name}</strong>{isDemo(profile) && <span className="demo-badge">DEMO</span>}{profile.archived_at && <span className="archived-badge">ARCHIVED</span>}</div><small>{profile.manufacturer} · {profile.model}</small></td><td><span className="compact-type">{pretty(profile.machine_type)}</span></td><td><span className="compact-controller">{profile.controller_model || profile.controller_name}</span></td><td>{documents[profile.id]?.length ?? 0}</td><td><span className={`knowledge-label ${label === "Ready" ? "ready" : label === "No Information" ? "empty" : "review"}`}>{label}</span></td><td>{postRecords[profile.id]?.length ?? 0}</td><td><div className="machine-row-actions" onClick={(event) => event.stopPropagation()} onKeyDown={(event) => event.stopPropagation()}><Link className="button tertiary machine-open-link" to={`/machines/${profile.id}`}>Open <span>→</span></Link><ActionMenu label={`More actions for ${profile.name}`} triggerLabel="More" items={[
        { label: "Edit Machine", onSelect: () => { setEditing(profile); setShowForm(true); } },
        { label: "Create Post", to: `/gpost?machine=${profile.id}` },
        profile.archived_at ? { label: "Restore Machine", onSelect: () => void restore(profile) } : { label: "Archive Machine", onSelect: () => void archive(profile) },
        { label: "Delete Machine", danger: true, divider: true, onSelect: () => { setDeleting(profile); setDeleteError(""); } },
      ]} /></div></td></tr>; })}</tbody></table></div>}
      {deleting && <div className="confirmation-backdrop" role="presentation"><section className="confirmation-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-machine-title"><h2 id="delete-machine-title">Delete “{deleting.name}”?</h2>{(postRecords[deleting.id]?.length ?? 0) > 0 ? <p className="form-error">This machine has {postRecords[deleting.id].length} Post Records and cannot be deleted. Archive it instead or resolve the dependent records.</p> : !deleteError && <p>This permanently deletes the machine profile. This action cannot be undone.</p>}{deleteError && <p className="form-error" role="alert">{deleteError}</p>}<footer><button className="button secondary" onClick={() => setDeleting(null)}>Cancel</button>{deletionBlocked ? <button className="button primary" onClick={() => void archive(deleting)}>Archive Machine</button> : <button className="button danger" onClick={() => void confirmDelete()}>Delete Machine</button>}</footer></section></div>}
    </section>
  );
}
