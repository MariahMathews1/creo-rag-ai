import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { MachineKnowledgeFact, PostOpenQuestion } from "../../types";

const showValue = (value: unknown) => value == null || value === "" ? "—" : Array.isArray(value) ? value.join(" – ") : typeof value === "object" ? "Configured values" : String(value);
const pretty = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const needsInformation = (fact: MachineKnowledgeFact) => ["unknown", "conflicting"].includes(fact.status);
const reviewedForPost = (fact: MachineKnowledgeFact) => fact.post_review_status === "reviewed_for_post";
const cleanSource = (fact: MachineKnowledgeFact) => /^machine configuration revision\s+\d+/i.test(fact.source_label || "") ? "Existing Machine Configuration" : fact.source_label || "Manual entry";
const cleanLocation = (fact: MachineKnowledgeFact) => cleanSource(fact) === "Existing Machine Configuration" && fact.source_location === "Reviewed machine profile" ? "" : fact.source_location || "";
const sourceSummary = (fact: MachineKnowledgeFact) => [cleanSource(fact), cleanLocation(fact)].filter(Boolean).join(" · ");
const reviewPayload = (fact: MachineKnowledgeFact, status: string, value: unknown = fact.value_json) => ({
  category: fact.category, fact_key: fact.fact_key, name: fact.name, value_json: value, unit: fact.unit, status,
  post_review_status: status === "not_applicable" ? "not_applicable" : "reviewed_for_post",
  source_document_id: fact.source_document_id, source_label: fact.source_label, source_location: fact.source_location,
  reviewer: "Local Engineer", review_note: status === "not_applicable" ? "Marked not applicable during engineering review." : fact.review_note,
});

function usedBy(fact: MachineKnowledgeFact) {
  if (!fact.used_by.length) return "Not mapped";
  return fact.used_by.map((use) => use.type === "ofg_setting" ? `OFG → ${use.label}` : use.label).join(", ");
}

function FactReview({ fact, close, onReview }: { fact: MachineKnowledgeFact; close: () => void; onReview: (fact: MachineKnowledgeFact, payload: Record<string, unknown>) => void }) {
  const [editing, setEditing] = useState(false); const [value, setValue] = useState(showValue(fact.value_json) === "—" ? "" : showValue(fact.value_json));
  const decide = (status: string, nextValue: unknown = fact.value_json) => { onReview(fact, reviewPayload(fact, status, nextValue)); close(); };
  return <div className="confirmation-backdrop" onMouseDown={(event) => { if (event.currentTarget === event.target) close(); }}><aside className="fact-review-drawer" role="dialog" aria-modal="true" aria-label={`Review ${fact.name}`}>
    <header><div><span className="eyebrow">{fact.category}</span><h3>Review Machine Information</h3></div><button className="button tertiary" onClick={close} aria-label="Close review">×</button></header>
    <dl><div><dt>Information</dt><dd>{fact.name}</dd></div><div><dt>Available Value</dt><dd>{showValue(fact.value_json)} {fact.unit}</dd></div><div><dt>Source</dt><dd>{cleanSource(fact)}</dd></div><div><dt>Source Context</dt><dd>{cleanLocation(fact) || "Location not recorded"}</dd></div><div><dt>Post Review</dt><dd>{reviewedForPost(fact) ? "Reviewed for this Post" : "Not Yet Reviewed"}</dd></div></dl>
    {editing && <label>Edit value<input autoFocus value={value} onChange={(event) => setValue(event.target.value)} /></label>}
    {fact.source_document_id && <Link className="button secondary source-review-link" to={`/documents/${fact.source_document_id}`}>View Source</Link>}
    <footer><button className="button tertiary" onClick={() => decide("not_applicable")}>Not Applicable</button>{editing ? <button className="button secondary" onClick={() => decide("confirmed", value)}>Save &amp; Review</button> : <button className="button secondary" onClick={() => setEditing(true)}>Edit Value</button>}<button className="button primary" onClick={() => decide("confirmed")}>Mark Reviewed for Post</button></footer>
  </aside></div>;
}

export function MachineKnowledgeView({ facts, questions, machineId, base, context = "post", onReview }: {
  facts: MachineKnowledgeFact[]; questions: PostOpenQuestion[]; machineId: number; base: string; context?: "machine" | "post";
  onReview: (fact: MachineKnowledgeFact, payload: Record<string, unknown>) => void;
}) {
  const [reviewing, setReviewing] = useState<MachineKnowledgeFact | null>(null); const [search, setSearch] = useState(""); const [category, setCategory] = useState("all");
  const categories = useMemo(() => [...new Set(facts.map((fact) => fact.category))].sort(), [facts]);
  const visible = facts.filter((fact) => (!search || `${fact.name} ${showValue(fact.value_json)} ${sourceSummary(fact)}`.toLowerCase().includes(search.toLowerCase())) && (category === "all" || fact.category === category));
  const missing = visible.filter(needsInformation); const available = visible.filter((fact) => !needsInformation(fact) && !reviewedForPost(fact) && fact.status !== "not_applicable"); const reviewed = visible.filter(reviewedForPost);
  const next = facts.find((fact) => needsInformation(fact) || !reviewedForPost(fact)); const engineerQuestions = questions.filter((question) => question.question_type !== "system_missing_information" && question.status !== "resolved");
  const purpose = context === "machine" ? "Review information extracted from machine/controller documentation. Confirmed values become engineering inputs used by the Post Builder." : "These are the machine/controller values available to this Post Record. Review missing or post-specific information before configuring OFG.";
  const table = (items: MachineKnowledgeFact[], action: string) => !items.length ? <p className="compact-empty">No items in this section.</p> : <div className="table-wrap"><table><thead><tr><th>Information</th><th>Value</th><th>Source</th><th>Post Review</th><th>Used By</th><th>Action</th></tr></thead><tbody>{items.map((fact) => <tr key={fact.id}><td><strong>{fact.name}</strong><small>{fact.category}</small></td><td>{showValue(fact.value_json)} {fact.unit}</td><td>{sourceSummary(fact)}</td><td>{reviewedForPost(fact) ? "Reviewed for this Post" : needsInformation(fact) ? "Needs Information" : "Not Yet Reviewed"}</td><td>{usedBy(fact)}</td><td><button className="button tertiary" onClick={() => setReviewing(fact)}>{action}</button></td></tr>)}</tbody></table></div>;
  return <section className="engineering-module machine-knowledge-demo">
    <header className="machine-knowledge-heading"><div><h2>Machine Information <span className="concept-help" title="Reviewed machine/controller information used by the Post Builder.">ⓘ</span></h2><p>{purpose}</p></div>{context === "machine" ? <div className="machine-information-header-actions"><Link className="button primary" to={`/machines/${machineId}/profile-extraction/new`}>Extract from Documents</Link><Link className="button secondary" to={`/machines/${machineId}/machine-information/manual`}>Add Manually</Link>{next && <button className="button tertiary" onClick={() => setReviewing(next)}>Review Next</button>}</div> : next ? <button className="button primary" onClick={() => setReviewing(next)}>Review Next Fact</button> : facts.length ? <Link className="button primary" to={base}>Continue Post</Link> : <Link className="button primary" to={`/documents?machine=${machineId}`}>Upload Documents</Link>}</header>
    <div className="machine-knowledge-filters"><label>Search Information<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search information" /></label><label>Category<select value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All Categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label></div>
    {!facts.length && <div className="panel empty-state"><h3>No reviewed machine information yet.</h3><p>Upload machine/controller documentation to extract proposed values, or add a value manually.</p><div className="machine-information-empty-actions"><Link className="button primary" to={`/documents?machine=${machineId}`}>Upload Documents</Link><Link className="button secondary" to={`/machines/${machineId}/machine-information/manual`}>Add Information Manually</Link></div></div>}
    {!!facts.length && <div className="knowledge-review-sections"><section><header><h3>Needs Information</h3><strong>{facts.filter(needsInformation).length}</strong></header>{table(missing, "Resolve →")}</section><section><header><h3>Available from Machine</h3><strong>{facts.filter((fact) => !needsInformation(fact) && !reviewedForPost(fact) && fact.status !== "not_applicable").length}</strong></header>{table(available, "Review →")}</section><section><header><h3>Reviewed for this Post</h3><strong>{facts.filter(reviewedForPost).length}</strong></header>{table(reviewed, "Open")}</section></div>}
    {engineerQuestions.length > 0 && <section className="open-questions compact-questions"><header><h3>Engineer Questions · {engineerQuestions.length}</h3><Link className="button tertiary" to={`${base}/review-export`}>View Questions</Link></header>{engineerQuestions.slice(0, 2).map((question) => <article key={question.id}><strong>{question.title}</strong></article>)}</section>}
    {reviewing && <FactReview fact={reviewing} close={() => setReviewing(null)} onReview={onReview} />}
  </section>;
}
