import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { MachineProfileRevision, ProfileExtractionRun, ProfileProposal } from "../types";

const showValue = (value: unknown) => value == null ? "Not found" : typeof value === "object" ? JSON.stringify(value) : String(value);

export function ProfileExtractionReviewPage() {
  const { machineId, runId } = useParams(); const machine = Number(machineId), id = Number(runId);
  const navigate = useNavigate();
  const [run, setRun] = useState<ProfileExtractionRun | null>(null);
  const [proposals, setProposals] = useState<ProfileProposal[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [category, setCategory] = useState("all"); const [error, setError] = useState("");
  const [draft, setDraft] = useState<MachineProfileRevision | null>(null);
  const [revisions, setRevisions] = useState<MachineProfileRevision[]>([]);
  const [comparison, setComparison] = useState<Array<{field_key:string;current:unknown;proposed:unknown;changed:boolean}>>([]);
  const [base, setBase] = useState<"active"|"blank"|"selected_revision">("active");
  const [sourceRevisionId, setSourceRevisionId] = useState<number | undefined>();
  const [approval, setApproval] = useState(false);
  const [variantSelection, setVariantSelection] = useState("");
  const [rerunBusy, setRerunBusy] = useState(false);
  async function load() {
    const [runData, proposalData, revisionData] = await Promise.all([api.getProfileExtraction(id), api.listProfileProposals(id), api.listProfileRevisions(machine)]);
    setRun(runData); setVariantSelection(runData.selected_machine_variant ?? "");
    setProposals(proposalData); setRevisions(revisionData);
    setSourceRevisionId((current) => current ?? revisionData[0]?.id);
    setSelectedId((current) => current ?? proposalData[0]?.id ?? null);
  }
  useEffect(() => { load().catch((cause) => setError(cause.message)); }, [id]);
  const selected = proposals.find((item) => item.id === selectedId);
  const categories = Array.from(new Set(proposals.map((item) => item.field_category)));
  const activeRevision = revisions.find((item) => item.status === "approved");
  const visible = useMemo(() => proposals.filter((item) => category === "all" || item.field_category === category), [proposals, category]);
  const draftSummary = {
    reviewed: proposals.filter((item) => item.review_status !== "pending").length,
    edited: proposals.filter((item) => item.review_status === "accepted_with_edit").length,
    manual: proposals.filter((item) => item.review_status === "manually_entered").length,
    rejected: proposals.filter((item) => item.review_status === "rejected").length,
    deferred: proposals.filter((item) => item.review_status === "deferred").length,
    conflicts_remaining: proposals.filter((item) => item.proposal_status === "conflicting" && item.review_status === "pending").length,
    not_found: proposals.filter((item) => item.proposal_status === "not_found").length,
    options_unverified: proposals.filter((item) => item.requires_exact_machine_verification && item.review_status === "pending").length,
    documents_used: run?.selected_document_ids_json.length ?? 0,
  };
  async function review(status: string, edited = false) {
    if (!selected) return;
    let reviewed_value: unknown = undefined; let review_note = "";
    if (edited) {
      const raw = window.prompt("Reviewed value", showValue(selected.proposed_value_json));
      if (raw == null) return;
      reviewed_value = Number.isNaN(Number(raw)) ? raw : Number(raw);
      review_note = window.prompt("Required review note", "") ?? "";
    } else if (
      status === "accepted"
      && (selected.proposal_status === "conflicting" || selected.confidence < .45)
    ) {
      review_note = window.prompt("Required review note for low-confidence or conflicting evidence", "") ?? "";
      if (!review_note.trim()) return;
    }
    try {
      const updated = await api.reviewProfileProposal(selected.id, { review_status: status, reviewed_value, review_note });
      setProposals((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Review failed"); }
  }
  async function createDraft() {
    try {
      const result = await api.applyProfileDraft(id, {
        base_strategy: base,
        source_revision_id: base === "selected_revision" ? sourceRevisionId : undefined,
        review_summary: "Reviewed local draft; not approved.",
      });
      setDraft(result.revision); setComparison(result.comparison);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Draft creation failed"); }
  }
  async function approve() {
    if (!draft || !approval) return;
    try { setDraft(await api.approveProfileRevision(draft.id, "Exact machine applicability reviewed and acknowledged.")); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Approval failed"); }
  }
  async function rerunForVariant() {
    if (!variantSelection) return;
    setRerunBusy(true); setError("");
    try {
      const next = await api.rerunProfileExtraction(id, variantSelection);
      navigate(`/machines/${machine}/profile-extraction/${next.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Variant re-run failed"); }
    finally { setRerunBusy(false); }
  }
  if (!run) return <section className="page">{error ? <p role="alert" className="form-error">{error}</p> : <p>Loading extraction…</p>}</section>;
  return <section className="page extraction-review-page">
    <PageHeader eyebrow={`Extraction #${run.id}`} title="Profile field review" description={`${run.status} · ${run.provider_name} provider`} action={<Link className="button secondary" to={`/machines/${machine}/profile-extraction/new`}>New extraction</Link>} />
    <aside className="safety-banner" role="alert"><span className="safety-icon">!</span><div><strong>Qualified review required</strong><p>{run.safety_notice}</p></div></aside>
    {error && <p role="alert" className="form-error">{error}</p>}
    {run.detected_variants_json.length > 1 && <div className="variant-warning"><strong>Multiple machine variants detected</strong><p>{run.detected_variants_json.join(", ")}. Variant-dependent fields remain ambiguous until exact applicability is confirmed.</p><label>Exact variant<select aria-label="Exact machine variant" value={variantSelection} onChange={(event) => setVariantSelection(event.target.value)} disabled={rerunBusy}><option value="">Select exact variant</option>{run.detected_variants_json.map((value) => <option key={value}>{value}</option>)}</select></label><button className="button secondary" disabled={rerunBusy || !variantSelection || variantSelection === run.selected_machine_variant} onClick={() => void rerunForVariant()}>{rerunBusy ? "Re-running extraction…" : "Re-run for selected variant"}</button></div>}
    <div className="extraction-metrics">{Object.entries(run.summary_json).map(([key, value]) => <div key={key}><strong>{value}</strong><small>{key.replaceAll("_", " ")}</small></div>)}</div>
    <div className="field-review-grid">
      <nav className="field-category-nav"><button className={category === "all" ? "active" : ""} onClick={() => setCategory("all")}>All fields <span>{proposals.length}</span></button>{categories.map((value) => <button className={category === value ? "active" : ""} key={value} onClick={() => setCategory(value)}>{value.replaceAll("_", " ")} <span>{proposals.filter((item) => item.field_category === value).length}</span></button>)}</nav>
      <section className="proposal-list">{visible.map((proposal) => <button className={selectedId === proposal.id ? "proposal-row selected" : "proposal-row"} key={proposal.id} onClick={() => setSelectedId(proposal.id)}><div><strong>{proposal.field_label}</strong><small>{proposal.proposal_status} · {proposal.review_status}</small></div><b>{showValue(proposal.reviewed_value_json ?? proposal.proposed_value_json)} {proposal.unit ?? ""}</b><span>{Math.round(proposal.confidence*100)}%</span></button>)}</section>
      <aside className="proposal-evidence">{selected ? <><header><span className="eyebrow">{selected.field_category.replaceAll("_"," ")}</span><h2>{selected.field_label}</h2></header><dl><div><dt>Current active</dt><dd>{showValue(activeRevision ? (activeRevision as unknown as Record<string, unknown>)[selected.field_key] : null)}</dd></div><div><dt>Proposal</dt><dd>{showValue(selected.proposed_value_json)} {selected.unit}</dd></div><div><dt>Status</dt><dd>{selected.proposal_status}</dd></div><div><dt>Confidence</dt><dd>{Math.round(selected.confidence*100)}%</dd></div></dl>{selected.interpretation_note && <p className="variant-warning">{selected.interpretation_note}</p>}{selected.requires_exact_machine_verification && <p className="processing-error">Exact machine option must be verified.</p>}<div className="proposal-actions"><button onClick={() => void review("accepted")}>Accept</button><button onClick={() => void review("accepted_with_edit", true)}>Edit and accept</button><button onClick={() => void review("rejected")}>Reject</button><button onClick={() => void review("deferred")}>Defer</button><button onClick={() => void review("manually_entered", true)}>Enter manually</button><button onClick={() => void review("not_applicable")}>Not applicable</button></div><h3>Evidence</h3>{selected.evidence.length ? selected.evidence.map((evidence) => <article className={`profile-evidence ${evidence.evidence_type}`} key={evidence.id}><strong>[{evidence.citation_number}] {evidence.evidence_type}</strong><small>{evidence.document_title} · {evidence.document_type.replaceAll("_", " ")} · Page {evidence.page_start ?? "—"} · {evidence.section_title ?? "Unlabeled"}</small><p>{evidence.excerpt}</p><Link to={`/documents/${evidence.document_id}?page=${evidence.page_start ?? 1}&highlight=${encodeURIComponent(evidence.raw_value_text ?? selected.field_label)}`}>Open source →</Link></article>) : <p>Not found in selected documents.</p>}<Link to={`/manual-assistant?machine=${machine}&question=${encodeURIComponent(`Explain the evidence and missing information for ${selected.field_label}.`)}`}>Ask why this was proposed →</Link></> : <p>Select a field.</p>}</aside>
    </div>
    <section className="draft-summary panel"><header><div><span className="eyebrow">Reviewed draft</span><h2>Create revision</h2></div></header><div className="panel-body"><label>Draft basis<select value={base} onChange={(event) => setBase(event.target.value as "active"|"blank"|"selected_revision")}><option value="active">Start from current active revision</option><option value="blank">Start from blank draft</option><option value="selected_revision">Start from selected prior revision</option></select></label>{base === "selected_revision" && <label>Prior revision<select aria-label="Prior revision" value={sourceRevisionId} onChange={(event) => setSourceRevisionId(Number(event.target.value))}>{revisions.map((revision) => <option key={revision.id} value={revision.id}>v{revision.revision_number} · {revision.status}</option>)}</select></label>}<button className="button primary" disabled={base === "selected_revision" && !sourceRevisionId} onClick={() => void createDraft()}>Create reviewed draft</button>{draft && <><p><strong>Revision v{draft.revision_number}</strong> · {draft.status}. This draft is not active.</p><div className="revision-comparison">{comparison.filter((item) => item.changed).map((item) => <div key={item.field_key}><strong>{item.field_key.replaceAll("_"," ")}</strong><span>{showValue(item.current)} → {showValue(item.proposed)}</span></div>)}</div><label className="approval-check"><input type="checkbox" checked={approval} onChange={(e) => setApproval(e.target.checked)} />I confirm this draft was reviewed against the exact machine configuration and is not automatically certified for production use.</label><button className="button primary" disabled={!approval || draft.status === "approved"} onClick={() => void approve()}>{draft.status === "approved" ? "Explicitly approved" : "Approve as active revision"}</button></>}</div></section>
  </section>;
}
