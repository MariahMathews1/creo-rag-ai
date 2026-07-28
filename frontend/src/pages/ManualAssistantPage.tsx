import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { DocumentType, MachineProfile, ManualQuestion, ManualSession } from "../types";

export function ManualAssistantPage() {
  const [params] = useSearchParams();
  const [machines, setMachines] = useState<MachineProfile[]>([]);
  const [machineId, setMachineId] = useState(params.get("machine") ?? "");
  const [sessions, setSessions] = useState<ManualSession[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [questions, setQuestions] = useState<ManualQuestion[]>([]);
  const [question, setQuestion] = useState(params.get("question") ?? "");
  const [category, setCategory] = useState("general");
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { api.listProfiles().then((items) => { setMachines(items); if (!machineId && items[0]) setMachineId(String(items[0].id)); }).catch((cause) => setError(cause.message)); }, []);
  useEffect(() => { if (!machineId) return; api.listManualSessions(Number(machineId)).then(setSessions).catch((cause) => setError(cause.message)); }, [machineId]);
  useEffect(() => { if (!sessionId) { setQuestions([]); return; } api.getManualSession(Number(sessionId)).then((value) => setQuestions(value.questions)); }, [sessionId]);

  async function newSession() {
    if (!machineId) return;
    const created = await api.createManualSession(Number(machineId), `Technical reference ${new Date().toLocaleDateString()}`);
    setSessions((current) => [created, ...current]); setSessionId(String(created.id)); setQuestions([]);
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!question.trim() || !machineId) return;
    setBusy(true); setError("");
    try {
      let active = sessionId;
      if (!active) {
        const created = await api.createManualSession(Number(machineId), question.slice(0, 80));
        setSessions((current) => [created, ...current]); active = String(created.id); setSessionId(active);
      }
      const answer = await api.askManualQuestion(Number(active), { question, document_types: types, category });
      setQuestions((current) => [...current, answer]); setQuestion("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Question failed."); }
    finally { setBusy(false); }
  }
  const toggleType = (value: DocumentType) => setTypes((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value]);
  return <section className="page">
    <PageHeader eyebrow="Citation-grounded reference" title="Manual Assistant" description="Answers are limited to documents uploaded for the selected machine." action={<Link className="button secondary" to={`/documents?machine=${machineId}`}>Manage documents</Link>} />
    <aside className="safety-banner" role="alert"><span className="safety-icon">!</span><div><strong>Technical reference only</strong><p>Machine documentation, simulation, and approval by a qualified CNC programmer remain required.</p></div></aside>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="assistant-layout">
      <aside className="session-rail"><label>Machine<select value={machineId} onChange={(event) => { setMachineId(event.target.value); setSessionId(""); }}><option value="">Select machine</option>{machines.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><button className="button primary" onClick={() => void newSession()}>+ New session</button><h2>Session history</h2>{sessions.map((item) => <button className={sessionId === String(item.id) ? "active" : ""} onClick={() => setSessionId(String(item.id))} key={item.id}><strong>{item.title}</strong><small>{new Date(item.updated_at).toLocaleDateString()}</small></button>)}</aside>
      <main className="reference-workspace">
        <form className="question-form" onSubmit={submit}><label>Technical question<textarea rows={3} value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What does the uploaded controller manual state about G84?" /></label><div className="question-options"><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}>{["general","command_meaning","cycle_support","machine_limit","setup_requirement","tool_change","work_offset","spindle","feed","coolant","alarm","post_processor"].map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label><fieldset><legend>Limit sources (optional)</legend>{(["controller_manual","programming_manual","company_standard","post_processor_document"] as DocumentType[]).map((item) => <label key={item}><input type="checkbox" checked={types.includes(item)} onChange={() => toggleType(item)} />{item.replaceAll("_", " ")}</label>)}</fieldset><button className="button primary large" disabled={busy || !question.trim() || !machineId}>{busy ? "Retrieving evidence…" : "Retrieve grounded answer"}</button></div></form>
        <div className="answer-history">{!questions.length && <div className="empty-state"><h2>No questions in this session</h2><p>Ask about a command, cycle, limit, or setup requirement documented for this machine.</p></div>}{questions.map((item) => <article className={`manual-answer ${item.answer_status}`} key={item.id}><header><span>{item.answer_status === "answered" ? "✓ Answered from documents" : "! Insufficient evidence"}</span><small>{item.category.replaceAll("_", " ")}</small></header><section><h2>Question</h2><p>{item.question}</p></section><section><h2>Answer</h2><p>{item.answer}</p></section><section><h2>Supporting Sources</h2>{!item.citations.length ? <p>No supporting citation met the evidence threshold.</p> : <div className="citation-list">{item.citations.map((citation) => <article key={citation.citation_number}><span>[{citation.citation_number}]</span><div><strong>{citation.document_title}</strong><small>{citation.document_type.replaceAll("_", " ")} · Page {citation.page_start ?? "—"} · {citation.section_title ?? "Unlabeled section"}</small><p>{citation.excerpt}</p><Link onClick={() => void api.recordCitationOpen(citation.document_id)} to={`/documents/${citation.document_id}?page=${citation.page_start ?? 1}&highlight=${encodeURIComponent(item.question.split(" ").slice(-2).join(" "))}`}>Open source →</Link></div></article>)}</div>}</section>{item.unresolved_questions.length > 0 && <section><h2>Unresolved Questions</h2><ul>{item.unresolved_questions.map((text) => <li key={text}>{text}</li>)}</ul></section>}<section className="answer-safety"><h2>Safety Notice</h2><p>{item.safety_notice}</p></section></article>)}</div>
      </main>
    </div>
  </section>;
}

