import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { ActionMenu } from "../components/ActionMenu";
import { MachineKnowledgeView } from "../features/postRecords/MachineKnowledgeView";
import type { GPostDraft, MachineKnowledgeFact, MachineProfile, ManualMachineInformation, PostOpenQuestion, SourceDocument } from "../types";

const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const showInformationValue = (value: unknown) => value == null || value === "" ? "—" : Array.isArray(value) ? value.join(", ") : typeof value === "object" ? JSON.stringify(value) : String(value);
function informationStatus(facts: MachineKnowledgeFact[]) {
  if (!facts.length) return "No Information";
  const missing = facts.filter((fact) => fact.status === "unknown").length;
  if (missing) return `Needs ${missing} Value${missing === 1 ? "" : "s"}`;
  if (facts.some((fact) => ["needs_review", "conflicting"].includes(fact.status))) return "Needs Review";
  return "Ready";
}

export function MachineDetailPage() {
  const machineId = Number(useParams().machineId); const view = useParams().view || "overview"; const [params] = useSearchParams();
  const [machine, setMachine] = useState<MachineProfile | null>(null); const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [posts, setPosts] = useState<GPostDraft[]>([]); const [facts, setFacts] = useState<MachineKnowledgeFact[]>([]);
  const [manualInformation, setManualInformation] = useState<ManualMachineInformation[]>([]);
  const [questions, setQuestions] = useState<PostOpenQuestion[]>([]); const [error, setError] = useState("");
  async function load() { try {
    const selected = await api.getProfile(machineId);
    const [docs, postRows, manualRows] = await Promise.all([api.listDocuments(machineId), api.listGPostDrafts(machineId), api.listManualMachineInformation(machineId)]);
    const current = postRows.find((item) => !["superseded", "archived"].includes(item.status));
    setMachine(selected); setDocuments(docs); setPosts(postRows); setManualInformation(manualRows);
    if (current) { const [nextFacts, nextQuestions] = await Promise.all([api.listMachineKnowledge(current.id), api.listPostQuestions(current.id)]); setFacts(nextFacts); setQuestions(nextQuestions); }
    else { setFacts([]); setQuestions([]); }
  } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine."); } }
  useEffect(() => { void load(); }, [machineId]);
  async function discardInformation(item: ManualMachineInformation) {
    if (!confirm(`Discard “${item.label}”? The current entry will be removed and the previous machine value will be restored when available. Revision and audit history will be preserved.`)) return;
    setError("");
    try { await api.discardMachineInformation(machineId, item.fact_key); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to discard Machine Information."); }
  }
  async function removeDocument(item: SourceDocument) {
    if (!confirm(`Delete “${item.title}” and its extracted chunks?`)) return;
    setError("");
    try { await api.deleteDocument(item.id); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to delete document."); }
  }
  if (!machine) return <section className="page">{error ? <p role="alert" className="form-error">{error}</p> : <p>Loading machine…</p>}</section>;
  const base = `/machines/${machine.id}`; const activePost = posts.find((post) => !["superseded", "archived"].includes(post.status));
  const issues = facts.filter((item) => ["needs_review", "unknown", "conflicting"].includes(item.status)); const status = facts.length ? informationStatus(facts) : manualInformation.length ? (manualInformation.some((item) => item.review_status === "needs_review") ? "Needs Review" : "Ready") : "No Information";
  const nextStep = !documents.length
    ? { title: "Upload machine documentation.", label: "Upload Documents", to: `/documents?machine=${machine.id}` }
    : issues.length || !facts.length
      ? { title: "Review Machine Information", label: "Review Information", to: `${base}/machine-knowledge` }
      : !activePost ? { title: "Create Post Record", label: "Create Post", to: `/gpost?machine=${machine.id}` }
        : { title: "Continue Post Development", label: "Open Post", to: `/gpost/${activePost.id}` };
  return <section className="page machine-detail-page">
    <header className="workspace-compact-header"><div><Link to="/machines">← Machines</Link><h1>{machine.name}</h1><p>{pretty(machine.machine_type)} · {machine.controller_model || machine.controller_name}</p></div></header>
    <nav className="post-record-tabs" aria-label="Machine views"><Link className={view === "overview" ? "active" : ""} to={base}>Overview</Link><Link className={view === "machine-knowledge" ? "active" : ""} to={`${base}/machine-knowledge`}>Machine Information</Link><Link className={view === "documents" ? "active" : ""} to={`${base}/documents`}>Documents</Link><Link className={view === "post-records" ? "active" : ""} to={`${base}/post-records`}>Post Records</Link></nav>
    {params.get("manualSaved") && <p className="success-message" role="status">Machine Information saved successfully.</p>}
    {view === "overview" && <section className="machine-overview-compact"><div className="machine-summary-metrics"><article><span>Documents</span><strong>{documents.length}</strong></article><article><span>Machine Information</span><strong>{status}</strong></article><article><span>Post Records</span><strong>{posts.length}</strong></article></div><aside className="machine-next-step"><div><span className="eyebrow">Next Step</span><h2>{nextStep.title}</h2></div><Link className="button primary" to={nextStep.to}>{nextStep.label}</Link></aside><section className="machine-basic-details"><h2>Machine Details</h2><dl><div><dt>Manufacturer</dt><dd>{machine.manufacturer}</dd></div><div><dt>Model</dt><dd>{machine.model}</dd></div><div><dt>Machine Type</dt><dd>{pretty(machine.machine_type)}</dd></div><div><dt>Controller</dt><dd>{machine.controller_model || machine.controller_name}</dd></div></dl><details><summary>More Details</summary><p>Secondary configuration and audit information is retained for engineering traceability.</p><Link to={`/machines/${machine.id}/revisions`}>Machine Change History</Link><small>Shows changes made to the machine definition over time.</small></details></section></section>}
    {view === "machine-knowledge" && (activePost ? <MachineKnowledgeView facts={facts} questions={questions} machineId={machine.id} base={`/gpost/${activePost.id}`} context="machine" onReview={(fact, payload) => void api.updateMachineKnowledge(fact.post_record_id, fact.id, payload).then(load).catch((cause) => setError(cause instanceof Error ? cause.message : "Review failed."))} /> : <section className="engineering-module machine-information-workspace"><header className="module-heading machine-information-heading"><div><h2>Machine Information</h2><p>Review traceable machine/controller values used as engineering inputs by the Post Builder.</p></div><div className="machine-information-header-actions"><Link className="button primary" to={`/machines/${machine.id}/profile-extraction/new`}>Extract from Documents</Link><Link className="button secondary" to={`/machines/${machine.id}/machine-information/manual`}>Add Manually</Link></div></header>{manualInformation.length ? <div className="panel table-wrap machine-information-table"><table><thead><tr><th>Information</th><th>Value</th><th>Source / Basis</th><th>Review Status</th><th><span className="visually-hidden">Actions</span></th></tr></thead><tbody>{manualInformation.map((item) => <tr key={item.id}><td><strong>{item.label}</strong><small>{item.category}</small></td><td><span className="machine-information-value">{showInformationValue(item.value)}</span>{item.unit && <small>{item.unit === "inch" ? "in" : item.unit}</small>}</td><td><strong>{item.source_label}</strong>{item.source_detail && <small>{item.source_detail}</small>}</td><td><span className={`machine-information-status ${item.review_status}`}>{pretty(item.review_status)}</span></td><td><ActionMenu label={`Actions for ${item.label}`} triggerLabel="More" items={[{ label: "Replace Manually", to: `/machines/${machine.id}/machine-information/manual?field=${encodeURIComponent(item.fact_key)}` }, { label: "Discard Information", danger: true, divider: true, onSelect: () => void discardInformation(item) }]} /></td></tr>)}</tbody></table></div> : <div className="empty-state"><h3>No reviewed machine information yet.</h3><p>Extract proposed values from uploaded machine/controller documents, or add a known value manually.</p><div className="machine-information-empty-actions"><Link className="button primary" to={`/machines/${machine.id}/profile-extraction/new`}>Extract from Documents</Link><Link className="button secondary" to={`/machines/${machine.id}/machine-information/manual`}>Add Information Manually</Link></div></div>}</section>)}
    {view === "documents" && <section className="engineering-module machine-documents-workspace"><header className="module-heading machine-documents-heading"><div><h2>Documents</h2><p>Machine and controller references available for extraction, review, and engineering traceability.</p></div><Link className="button primary" to={`/documents?machine=${machine.id}`}>Upload Document</Link></header>{documents.length ? <div className="panel table-wrap machine-documents-table"><table><thead><tr><th>Document</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead><tbody>{documents.map((item) => <tr key={item.id}><td><strong>{item.title}</strong>{item.original_filename && <small>{item.original_filename}</small>}{item.processing_error && <small className="processing-error">{item.processing_error}</small>}</td><td>{pretty(item.document_type)}</td><td><span className={`document-status ${item.processing_status}`}>{pretty(item.processing_status)}</span></td><td><div className="machine-document-row-actions"><Link className="button tertiary machine-document-open" to={`/documents/${item.id}`}>Open <span>→</span></Link><ActionMenu label={`More actions for ${item.title}`} triggerLabel="More" items={[{ label: "Extract Information", to: `/machines/${machine.id}/profile-extraction/new` }, { label: "Ask Machine Assistant", to: `/machine-assistant?machine=${machine.id}` }, ...(item.processing_status === "failed" ? [{ label: "Reprocess Document", onSelect: () => void api.reprocessDocument(item.id).then(load).catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to reprocess document.")) }] : []), { label: "Delete Document", danger: true, divider: true, onSelect: () => void removeDocument(item) }]} /></div></td></tr>)}</tbody></table></div> : <div className="panel empty-state"><h3>No documents uploaded yet.</h3><p>Upload machine or controller documentation to begin extracting Machine Information.</p><Link className="button primary" to={`/documents?machine=${machine.id}`}>Upload Document</Link></div>}</section>}
    {view === "post-records" && <section className="engineering-module"><header className="module-heading"><div><h2>Post Records</h2><p>Posts created for this machine. Archive records when engineering history must be retained.</p></div><Link className="button primary" to={`/gpost?machine=${machine.id}`}>Create Post</Link></header>{posts.length ? <div className="panel table-wrap"><table><thead><tr><th>Post</th><th>Status</th><th>Updated</th><th>Action</th></tr></thead><tbody>{posts.map((post) => <tr key={post.id}><td>{post.name}</td><td>{post.status === "superseded" ? "Historical" : pretty(post.status)}</td><td>{new Date(post.updated_at).toLocaleDateString()}</td><td><Link className="button tertiary" to={`/gpost/${post.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <div className="panel empty-state"><h3>No Post Records yet.</h3><p>Create a machine-specific Post Record to begin configuring G-POST.</p></div>}</section>}
  </section>;
}
