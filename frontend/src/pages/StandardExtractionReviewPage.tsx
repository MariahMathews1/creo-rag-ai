import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  StandardConvention, StandardExtractionRun, StandardProfile,
} from "../types";

const QUEUES = [
  ["pending", "Pending"], ["conflicts", "Conflicts"], ["high", "High support"],
  ["medium", "Medium support"], ["low", "Low support"], ["exceptions", "Exceptions"],
  ["accepted", "Accepted"], ["rejected", "Rejected"], ["deferred", "Deferred"],
] as const;

function inQueue(item: StandardConvention, queue: string) {
  if (queue === "pending") return item.review_status === "pending";
  if (queue === "conflicts") return item.review_status === "pending" && item.proposal_status === "conflicting";
  if (queue === "high") return item.review_status === "pending" && item.support_percentage >= 90;
  if (queue === "medium") return item.review_status === "pending" && item.support_percentage >= 60 && item.support_percentage < 90;
  if (queue === "low") return item.review_status === "pending" && item.support_percentage < 60;
  if (queue === "exceptions") return item.evidence.some((e) => e.evidence_type !== "supporting");
  return item.review_status === queue;
}

export function StandardExtractionReviewPage() {
  const machineId = Number(useParams().machineId);
  const runId = Number(useParams().runId);
  const [params, setParams] = useSearchParams();
  const queue = params.get("queue") ?? "pending";
  const search = params.get("q") ?? "";
  const selectedId = Number(params.get("convention") ?? 0);
  const evidenceId = Number(params.get("evidence") ?? 0);
  const [run, setRun] = useState<StandardExtractionRun | null>(null);
  const [items, setItems] = useState<StandardConvention[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [draft, setDraft] = useState<StandardProfile | null>(null);
  const [approval, setApproval] = useState(false);

  async function load() {
    try {
      const [runData, proposals] = await Promise.all([
        api.getStandardExtraction(runId), api.listStandardConventions(runId),
      ]);
      setRun(runData); setItems(proposals);
      if (!selectedId && proposals.length) {
        setParams((current) => {
          const next = new URLSearchParams(current);
          next.set("convention", String(proposals[0].id)); return next;
        }, { replace: true });
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load extraction");
    }
  }
  useEffect(() => { void load(); }, [runId]);

  const counts = Object.fromEntries(QUEUES.map(([key]) => [
    key, items.filter((item) => inQueue(item, key)).length,
  ]));
  const visible = useMemo(() => items.filter((item) =>
    inQueue(item, queue)
    && (!search || `${item.title} ${item.category} ${item.description}`
      .toLowerCase().includes(search.toLowerCase()))
  ), [items, queue, search]);
  const selected = items.find((item) => item.id === selectedId) ?? visible[0];
  const evidence = selected?.evidence.find((item) => item.id === evidenceId);
  const pending = items.filter((item) => item.review_status === "pending").length;
  const categories = Array.from(new Set(items.map((item) => item.category)));

  function update(updates: Record<string, string | null>) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      Object.entries(updates).forEach(([key, value]) => {
        if (value) next.set(key, value); else next.delete(key);
      });
      return next;
    });
  }

  async function review(status: string) {
    if (!selected) return;
    setError("");
    const note = status === "accepted"
      ? "Reviewer accepted this convention as scoped organizational guidance; frequency alone was not treated as authority."
      : `Reviewer marked this convention ${status}.`;
    try {
      await api.reviewStandardConvention(selected.id, {
        review_status: status, review_note: note,
      });
      setNotice(`${selected.title}: ${status.replaceAll("_", " ")}.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Review failed");
    }
  }

  async function batch(status: string) {
    try {
      const result = await api.batchReviewConventions(
        runId, [...selectedIds], status,
      );
      setNotice(`${result.succeeded.length} updated; ${result.failed.length} require individual review.`);
      setSelectedIds(new Set()); await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Batch review failed");
    }
  }

  async function createDraft() {
    try {
      const value = await api.createStandardDraft(
        runId, `Organizational programming standard ${new Date().toLocaleDateString()}`,
      );
      setDraft(value);
      setNotice(`Standard v${value.revision_number} created as an inactive draft.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Draft creation failed");
    }
  }

  async function approveDraft() {
    if (!draft || !approval) return;
    const submitted = draft.status === "draft"
      ? await api.submitStandard(draft.id, "Submitted after convention review.")
      : draft;
    const approved = await api.approveStandard(
      submitted.id,
      "Explicit approval after applicability and evidence review.",
    );
    setDraft(approved); setNotice(`Standard v${approved.revision_number} explicitly approved.`);
  }

  if (!run) return <section className="page"><p role={error ? "alert" : "status"}>{error || "Loading standard review…"}</p></section>;
  return <section className="page standard-review-page">
    <PageHeader eyebrow={`Standard extraction #${run.id}`}
      title="Programming-convention review"
      description={`${String(run.summary_json.eligible_program_count ?? 0)} explicitly eligible programs · deterministic ${run.algorithm_version}`} />
    <SafetyBanner title="Observed frequency is not authority"
      message="Recurring historical patterns require human review. Similarity does not certify safety, correctness, or production readiness." />
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}

    <section className="panel convention-dashboard">
      <header><div><span className="eyebrow">Review progress</span>
        <h2>{items.length - pending} / {items.length} conventions reviewed</h2></div>
        <strong>{pending} pending</strong></header>
      <progress max={items.length} value={items.length - pending} />
      <div className="category-progress">{categories.map((category) => {
        const values = items.filter((item) => item.category === category);
        return <button key={category} onClick={() => update({ q: category })}>
          <strong>{category.replaceAll("_", " ")}</strong>
          <span>{values.filter((item) => item.review_status !== "pending").length} / {values.length}</span>
        </button>;
      })}</div>
    </section>

    <nav className="review-queues" aria-label="Convention queues">
      {QUEUES.map(([key, label]) => <button key={key}
        className={queue === key ? "active" : ""}
        onClick={() => update({ queue: key, convention: null })}>
        {label}<span>{counts[key]}</span>
      </button>)}
    </nav>
    <section className="sticky-review-header">
      <label className="review-search">Search conventions<input
        aria-label="Search conventions" value={search}
        onChange={(e) => update({ q: e.target.value || null })} /></label>
      <span>{visible.length} visible · {selectedIds.size} selected</span>
      <button disabled={!selectedIds.size} onClick={() => void batch("deferred")}>Batch defer</button>
      <button disabled={!selectedIds.size} onClick={() => void batch("accepted")}>Protected batch accept</button>
    </section>

    <div className="standard-review-grid">
      <section className="convention-list" aria-label="Convention proposals">
        {visible.map((item) => <article key={item.id}
          className={selected?.id === item.id ? "selected" : ""}>
          <input aria-label={`Select ${item.title}`} type="checkbox"
            checked={selectedIds.has(item.id)}
            onChange={() => setSelectedIds((current) => {
              const next = new Set(current);
              if (next.has(item.id)) next.delete(item.id); else next.add(item.id);
              return next;
            })} />
          <button onClick={() => update({ convention: String(item.id) })}>
            <span className={`strong-status ${item.proposal_status}`}>{item.proposal_status}</span>
            <strong>{item.title}</strong>
            <small>{item.category.replaceAll("_", " ")} · {item.support_count}/{item.eligible_program_count} programs ({item.support_percentage}%)</small>
            <span className={`strong-status ${item.review_status}`}>{item.review_status.replaceAll("_", " ")}</span>
          </button>
        </article>)}
      </section>
      {selected && <section className="panel convention-detail">
        <header><div><span className="eyebrow">{selected.convention_type}</span><h2>{selected.title}</h2></div>
          {selected.safety_relevant && <span className="strong-status requires-review">Individual review</span>}
        </header>
        <p>{selected.description}</p>
        <dl className="convention-metrics">
          <div><dt>Support</dt><dd>{selected.support_count} / {selected.eligible_program_count}</dd></div>
          <div><dt>Frequency</dt><dd>{selected.support_percentage}% · {selected.frequency_classification.replaceAll("_", " ")}</dd></div>
          <div><dt>Confidence</dt><dd>{Math.round(selected.confidence * 100)}% prioritization only</dd></div>
          <div><dt>Scope</dt><dd>{JSON.stringify(selected.applicability_json)}</dd></div>
        </dl>
        {Object.keys(selected.condition_json).length > 0 && <div className="conditional-convention">
          <strong>Heuristic condition</strong><code>{JSON.stringify(selected.condition_json)}</code>
          <p>Full semantic equivalence is not claimed.</p>
        </div>}
        <h3>Program-line evidence</h3>
        <div className="convention-evidence-list">{selected.evidence.map((item) =>
          <button key={item.id} className={item.evidence_type}
            onClick={() => update({ evidence: String(item.id) })}>
            <span className={`strong-status ${item.evidence_type}`}>{item.evidence_type}</span>
            <strong>{item.program_name}</strong>
            <small>Line {item.line_start ?? "—"} · Post {String(item.match_context_json.post_processor_revision ?? "unspecified")}</small>
            <code>{item.excerpt}</code>
          </button>
        )}</div>
        <div className="review-action-bar">
          <button className="button primary" onClick={() => void review("accepted")}>Accept as scoped convention</button>
          <button onClick={() => void review("rejected")}>Reject weak convention</button>
          <button onClick={() => void review("deferred")}>Defer</button>
        </div>
      </section>}
    </div>

    <section className={`panel draft-readiness ${pending ? "not-ready" : "ready"}`}>
      <header><div><span className="eyebrow">Draft readiness</span>
        <h2>{pending ? `${pending} proposals still require intentional review` : "Ready to create an inactive standard draft"}</h2></div>
        <button className="button primary" disabled={pending > 0} onClick={() => void createDraft()}>Create standard draft</button>
      </header>
      {draft && <div className="standard-draft-gate">
        <p><strong>{draft.name} · v{draft.revision_number}</strong> is {draft.status}. It is not active automatically.</p>
        <label className="checkbox-label"><input type="checkbox" checked={approval}
          onChange={(e) => setApproval(e.target.checked)} />
          I reviewed machine revision, controller, post revision, program scope, evidence, and exceptions.
        </label>
        <button className="button primary" disabled={!approval || draft.status === "approved"}
          onClick={() => void approveDraft()}>Submit and explicitly approve</button>
        <a href={api.standardReportUrl(draft.id)}>Export standard report</a>
      </div>}
    </section>

    {evidence && <div className="source-drawer-backdrop">
      <aside className="source-drawer" role="dialog" aria-modal="true" aria-label="Program evidence">
        <header><div><span className="eyebrow">{evidence.evidence_type} program evidence</span>
          <h2>{evidence.program_name}</h2></div>
          <button aria-label="Close program evidence" onClick={() => update({ evidence: null })}>×</button></header>
        <p>Exact source line {evidence.line_start ?? "unknown"}</p>
        <pre>{evidence.excerpt}</pre>
        <dl><div><dt>Context</dt><dd>{JSON.stringify(evidence.match_context_json)}</dd></div></dl>
        <p>This line shows prior practice only; exact machine and setup applicability must be verified.</p>
      </aside>
    </div>}
  </section>;
}
