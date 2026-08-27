import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { MachineKnowledgeView } from "../features/postRecords/MachineKnowledgeView";
import type { GPostDraft, MachineKnowledgeFact, MachineProfile, PostOpenQuestion, SourceDocument } from "../types";

const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
function knowledgeStatus(facts: MachineKnowledgeFact[]) {
  if (!facts.length) return "No Knowledge";
  const missing = facts.filter((fact) => fact.status === "unknown").length;
  if (missing) return `Needs ${missing} Fact${missing === 1 ? "" : "s"}`;
  if (facts.some((fact) => ["needs_review", "conflicting"].includes(fact.status))) return "Needs Review";
  return "Ready";
}

export function MachineDetailPage() {
  const machineId = Number(useParams().machineId); const view = useParams().view || "overview";
  const [machine, setMachine] = useState<MachineProfile | null>(null); const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [posts, setPosts] = useState<GPostDraft[]>([]); const [facts, setFacts] = useState<MachineKnowledgeFact[]>([]); const [questions, setQuestions] = useState<PostOpenQuestion[]>([]); const [error, setError] = useState("");
  async function load() { try {
    const selected = await api.getProfile(machineId);
    const [docs, postRows] = await Promise.all([api.listDocuments(machineId), api.listGPostDrafts(machineId)]);
    const current = postRows.find((item) => item.status !== "superseded" && item.status !== "archived");
    setMachine(selected); setDocuments(docs); setPosts(postRows);
    if (current) { const [nextFacts, nextQuestions] = await Promise.all([api.listMachineKnowledge(current.id), api.listPostQuestions(current.id)]); setFacts(nextFacts); setQuestions(nextQuestions); }
    else { setFacts([]); setQuestions([]); }
  } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load machine."); } }
  useEffect(() => { void load(); }, [machineId]);
  if (!machine) return <section className="page">{error ? <p role="alert" className="form-error">{error}</p> : <p>Loading machine…</p>}</section>;
  const base = `/machines/${machine.id}`; const activePost = posts.find((post) => post.status !== "superseded" && post.status !== "archived"); const issues = facts.filter((item) => ["needs_review", "unknown", "conflicting"].includes(item.status)); const status = knowledgeStatus(facts);
  const nextStep = !documents.length
    ? { title: "Upload machine documentation.", label: "Upload Documents", to: `/documents?machine=${machine.id}` }
    : issues.length || !facts.length
      ? { title: "Review Machine Knowledge", label: "Review Knowledge", to: `${base}/machine-knowledge` }
      : !activePost
        ? { title: "Create Post Record", label: "Create Post", to: `/gpost?machine=${machine.id}` }
        : { title: "Continue Post Development", label: "Open Post", to: `/gpost/${activePost.id}` };
  return <section className="page machine-detail-page"><header className="workspace-compact-header"><div><Link to="/machines">← Machines</Link><h1>{machine.name}</h1><p>{pretty(machine.machine_type)} · {machine.controller_model || machine.controller_name}</p></div></header>
    <nav className="post-record-tabs" aria-label="Machine views"><Link className={view === "overview" ? "active" : ""} to={base}>Overview</Link><Link className={view === "machine-knowledge" ? "active" : ""} to={`${base}/machine-knowledge`}>Machine Knowledge</Link><Link className={view === "documents" ? "active" : ""} to={`${base}/documents`}>Documents</Link><Link className={view === "post-records" ? "active" : ""} to={`${base}/post-records`}>Post Records</Link></nav>
    {view === "overview" && <section className="machine-overview-compact"><div className="machine-summary-metrics"><article><span>Documents</span><strong>{documents.length}</strong></article><article><span>Machine Knowledge</span><strong>{status}</strong></article><article><span>Post Records</span><strong>{posts.length}</strong></article></div><aside className="machine-next-step"><div><span className="eyebrow">Next Step</span><h2>{nextStep.title}</h2></div><Link className="button primary" to={nextStep.to}>{nextStep.label}</Link></aside><section className="machine-basic-details"><h2>Machine Details</h2><dl><div><dt>Manufacturer</dt><dd>{machine.manufacturer}</dd></div><div><dt>Model</dt><dd>{machine.model}</dd></div><div><dt>Machine Type</dt><dd>{pretty(machine.machine_type)}</dd></div><div><dt>Controller</dt><dd>{machine.controller_model || machine.controller_name}</dd></div></dl><details><summary>View Technical Details</summary><div className="technical-detail-list"><p>Machine ID: {machine.id}</p><p>Profile revision: {machine.active_revision_id ?? "Not assigned"}</p><p>Audit context is retained with each Post Record snapshot.</p><Link to={`/machines/${machine.id}/revisions`}>Configuration history</Link></div></details></section></section>}
    {view === "machine-knowledge" && (activePost ? <MachineKnowledgeView facts={facts} questions={questions} machineId={machine.id} base={`/gpost/${activePost.id}`} onReview={(fact, payload) => void api.updateMachineKnowledge(fact.post_record_id, fact.id, payload).then(load).catch((cause) => setError(cause instanceof Error ? cause.message : "Review failed."))} /> : <section className="engineering-module"><header><h2>Machine Knowledge</h2><p>Review proposed facts extracted from machine/controller sources. Confirmed facts become the engineering values used by the Post Builder.</p></header><div className="empty-state"><h3>No confirmed machine knowledge yet.</h3><p>{!documents.length ? "Upload machine/controller documentation to begin building machine knowledge." : "No machine facts are waiting for review."}</p><Link className="button primary" to={`/machines/${machine.id}/profile-extraction/new`}>Add Machine Fact</Link></div></section>)}
    {view === "documents" && <section className="engineering-module"><header className="module-heading"><div><h2>Documents</h2><p>Documentation associated with this machine.</p></div><Link className="button primary" to={`/documents?machine=${machine.id}`}>Upload Document</Link></header><div className="panel table-wrap"><table><thead><tr><th>Document</th><th>Type</th><th>Status</th><th>Action</th></tr></thead><tbody>{documents.map((item) => <tr key={item.id}><td>{item.title}</td><td>{pretty(item.document_type)}</td><td>{pretty(item.processing_status)}</td><td><Link className="button tertiary" to={`/documents/${item.id}`}>Open</Link></td></tr>)}</tbody></table></div></section>}
    {view === "post-records" && <section className="engineering-module"><header><h2>Post Records</h2></header>{posts.length ? <div className="panel table-wrap"><table><thead><tr><th>Post</th><th>Status</th><th>Updated</th><th>Action</th></tr></thead><tbody>{posts.map((post) => <tr key={post.id}><td>{post.name}</td><td>{post.status === "superseded" ? "Historical" : pretty(post.status)}</td><td>{new Date(post.updated_at).toLocaleDateString()}</td><td><Link className="button tertiary" to={`/gpost/${post.id}`}>Open</Link></td></tr>)}</tbody></table></div> : <div className="panel empty-state"><h3>No Post Records.</h3><Link className="button primary" to={`/gpost?machine=${machine.id}`}>Create Post</Link></div>}</section>}
  </section>;
}
