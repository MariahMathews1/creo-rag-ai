import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { MachineKnowledgeFact, PostOpenQuestion } from "../../types";

const showValue = (value: unknown) => value == null || value === "" ? "—" : Array.isArray(value) ? value.join(" – ") : typeof value === "object" ? JSON.stringify(value) : String(value);
const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const isProposed = (fact: MachineKnowledgeFact) => ["needs_review", "unknown", "conflicting"].includes(fact.status);
const cleanSource = (fact: MachineKnowledgeFact) => /^machine configuration revision\s+\d+/i.test(fact.source_label || "") ? "Existing Machine Configuration" : fact.source_label || "Manual entry";
const cleanLocation = (fact: MachineKnowledgeFact) => cleanSource(fact) === "Existing Machine Configuration" && fact.source_location === "Reviewed machine profile" ? "" : fact.source_location || "";
const sourceSummary = (fact: MachineKnowledgeFact) => [cleanSource(fact), cleanLocation(fact)].filter(Boolean).join(" · ");
const reviewPayload = (fact: MachineKnowledgeFact, status: string, value: unknown = fact.value_json) => ({
  category: fact.category, fact_key: fact.fact_key, name: fact.name, value_json: value, unit: fact.unit, status,
  source_document_id: fact.source_document_id, source_label: fact.source_label, source_location: fact.source_location,
  reviewer: "Local Engineer", review_note: status === "not_applicable" ? "Rejected during engineering review." : fact.review_note,
});

function usedBy(fact: MachineKnowledgeFact) {
  if (!fact.used_by.length) return "Not mapped";
  return fact.used_by.map((use) => use.type === "ofg_setting" ? `OFG → ${fact.category}` : use.type === "site_standard" ? `Site Standard → ${use.label}` : use.type === "custom_logic" ? `Custom Logic → ${use.label}` : use.label).join(", ");
}

function Source({ fact }: { fact: MachineKnowledgeFact }) {
  return <div className="fact-source"><strong>{cleanSource(fact)}</strong>{cleanLocation(fact) && <small>{cleanLocation(fact)}</small>}</div>;
}

function FactReview({ fact, close, onReview }: { fact: MachineKnowledgeFact; close: () => void; onReview: (fact: MachineKnowledgeFact, payload: Record<string, unknown>) => void }) {
  const [editing, setEditing] = useState(false); const [value, setValue] = useState(showValue(fact.value_json) === "—" ? "" : showValue(fact.value_json));
  const decide = (status: string, nextValue: unknown = fact.value_json) => { onReview(fact, reviewPayload(fact, status, nextValue)); close(); };
  return <div className="confirmation-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) close(); }}><aside className="fact-review-drawer" role="dialog" aria-modal="true" aria-label={`Review ${fact.name}`}>
    <header><div><span className="eyebrow">{fact.category}</span><h3>Review Machine Fact</h3></div><button className="button tertiary" onClick={close} aria-label="Close review">×</button></header>
    <dl><div><dt>Fact</dt><dd>{fact.name}</dd></div><div><dt>Proposed Value</dt><dd>{showValue(fact.value_json)} {fact.unit}</dd></div><div><dt>Source</dt><dd>{cleanSource(fact)}</dd></div><div><dt>Source Context</dt><dd>{cleanLocation(fact) || "Location not recorded"}</dd></div><div><dt>Decision</dt><dd>{pretty(fact.status)}</dd></div></dl>
    {editing && <label>Edit proposed value<input autoFocus value={value} onChange={(event) => setValue(event.target.value)} /></label>}
    {fact.source_document_id && <Link className="button secondary source-review-link" to={`/documents/${fact.source_document_id}`}>View Source</Link>}
    <footer><button className="button tertiary" onClick={() => decide("not_applicable")}>Reject</button>{editing ? <button className="button secondary" onClick={() => decide("confirmed", value)}>Save &amp; Confirm</button> : <button className="button secondary" onClick={() => setEditing(true)}>Edit &amp; Confirm</button>}<button className="button primary" onClick={() => decide("confirmed")}>Confirm</button></footer>
  </aside></div>;
}

export function MachineKnowledgeView({ facts, questions, machineId, base, onReview }: {
  facts: MachineKnowledgeFact[]; questions: PostOpenQuestion[]; machineId: number; base: string;
  onReview: (fact: MachineKnowledgeFact, payload: Record<string, unknown>) => void;
}) {
  const [reviewing, setReviewing] = useState<MachineKnowledgeFact | null>(null); const [search, setSearch] = useState(""); const [status, setStatus] = useState("all"); const [category, setCategory] = useState("all");
  const categories = useMemo(() => [...new Set(facts.map((fact) => fact.category))].sort(), [facts]);
  const visible = facts.filter((fact) => (!search || `${fact.name} ${showValue(fact.value_json)} ${sourceSummary(fact)}`.toLowerCase().includes(search.toLowerCase())) && (category === "all" || fact.category === category) && (status === "all" || status === "needs_review" && isProposed(fact) || status === "confirmed" && fact.status === "confirmed"));
  const proposed = visible.filter(isProposed); const confirmed = visible.filter((fact) => fact.status === "confirmed"); const allProposed = facts.filter(isProposed); const openQuestions = questions.filter((question) => question.status !== "resolved");
  return <section className="engineering-module machine-knowledge-demo">
    <header className="machine-knowledge-heading"><div><h2>Machine Knowledge <span className="concept-help" title="Reviewed machine/controller facts extracted from manuals or entered by an engineer.">ⓘ</span></h2><p>Review proposed facts extracted from machine/controller sources. Confirmed facts become the engineering values used by the Post Builder.</p></div>{allProposed.length ? <button className="button primary" onClick={() => setReviewing(allProposed[0])}>Review Next Fact</button> : facts.length ? <Link className="button primary" to={base}>Continue Post</Link> : <Link className="button primary" to={`/machines/${machineId}/profile-extraction/new`}>Add Machine Fact</Link>}</header>
    <div className="machine-knowledge-filters"><label>Search Facts<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search facts" /></label><label>Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All</option><option value="needs_review">Needs Review</option><option value="confirmed">Confirmed</option></select></label><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All Categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label></div>
    {!facts.length && <p className="machine-document-hint">Upload machine/controller documentation to begin building machine knowledge.</p>}
    <div className="knowledge-review-sections">
      <section><header><h3>Needs Review</h3><strong>{allProposed.length}</strong></header>{!proposed.length ? <p className="compact-empty">No machine facts are waiting for review.</p> : <div className="table-wrap"><table><thead><tr><th>Fact</th><th>Proposed Value</th><th>Source</th><th>Status</th><th>Action</th></tr></thead><tbody>{proposed.map((fact) => <tr key={fact.id}><td><strong>{fact.name}</strong><small>{fact.category}</small></td><td>{showValue(fact.value_json)} {fact.unit}</td><td>{sourceSummary(fact)}</td><td><span className={`post-status ${fact.status}`}>{fact.status === "unknown" ? "Needs Information" : "Needs Review"}</span></td><td><button className="button tertiary" onClick={() => setReviewing(fact)}>Review →</button></td></tr>)}</tbody></table></div>}</section>
      <section><header><h3>Confirmed</h3><strong>{facts.filter((fact) => fact.status === "confirmed").length}</strong></header>{!confirmed.length ? <p className="compact-empty">No confirmed machine knowledge yet.</p> : <div className="table-wrap"><table><thead><tr><th>Fact</th><th>Value</th><th>Source</th><th>Used By</th><th>Action</th></tr></thead><tbody>{confirmed.map((fact) => <tr key={fact.id}><td><strong>{fact.name}</strong><small>{fact.category}</small></td><td>{showValue(fact.value_json)} {fact.unit}</td><td><Source fact={fact} /></td><td>{usedBy(fact)}</td><td><Link className="button tertiary" to={`${base}/machine-knowledge/${fact.id}`}>Edit</Link></td></tr>)}</tbody></table></div>}</section>
    </div>
    {openQuestions.length > 0 && <section className="open-questions compact-questions"><header><h3>Open Questions · {openQuestions.length}</h3><Link className="button tertiary" to={`${base}/review-export`}>View Questions</Link></header>{openQuestions.slice(0, 2).map((question) => <article key={question.id}><div><strong>{question.title}</strong><small>{question.description || question.source_context || "Needs confirmation"}</small></div></article>)}</section>}
    {reviewing && <FactReview fact={reviewing} close={() => setReviewing(null)} onReview={onReview} />}
  </section>;
}
