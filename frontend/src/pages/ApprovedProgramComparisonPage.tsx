import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  ComparisonFinding, ProgramComparison, SideBySideComparison, SimilarProgram,
} from "../types";

const TYPES = ["matches", "differs", "missing", "unexpected", "not_applicable"];

export function ApprovedProgramComparisonPage() {
  const analysisId = Number(useParams().analysisId);
  const comparisonId = Number(useParams().comparisonId);
  const [params, setParams] = useSearchParams();
  const filter = params.get("type") ?? "all";
  const [comparison, setComparison] = useState<ProgramComparison | null>(null);
  const [side, setSide] = useState<SideBySideComparison | null>(null);
  const [similar, setSimilar] = useState<SimilarProgram[]>([]);
  const [selected, setSelected] = useState<ComparisonFinding | null>(null);
  const [classification, setClassification] = useState("requires_investigation");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    try {
      const [run, sideData, similarData] = await Promise.all([
        api.getStandardComparison(comparisonId),
        api.getSideBySideComparison(comparisonId),
        api.listSimilarPrograms(analysisId),
      ]);
      setComparison(run); setSide(sideData); setSimilar(similarData);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load comparison");
    }
  }
  useEffect(() => { void load(); }, [comparisonId]);
  const visible = useMemo(
    () => (comparison?.findings ?? []).filter(
      (item) => filter === "all" || item.comparison_type === filter,
    ),
    [comparison, filter],
  );

  async function classify() {
    if (!selected || !note.trim()) return;
    try {
      await api.classifyComparisonException(
        selected.id, classification, note.trim(),
      );
      setNotice("Difference classification saved. The standard was not changed.");
      setSelected(null); setNote(""); await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Classification failed");
    }
  }

  if (!comparison || !side) return <section className="page"><p role={error ? "alert" : "status"}>{error || "Loading approved-program comparison…"}</p></section>;
  return <section className="page comparison-page">
    <PageHeader eyebrow={`Analysis #${analysisId} · comparison #${comparison.id}`}
      title="Approved-program comparison"
      description={`Standard #${comparison.standard_profile_id} · ${comparison.algorithm_version} · organizational differences remain separate from deterministic findings`}
      action={<a className="button secondary" href={api.comparisonReportUrl(comparison.id)}>Export report</a>} />
    <SafetyBanner title="Historical similarity is not certification" message={comparison.safety_notice} />
    {comparison.stale && <p className="form-error" role="alert">
      Stale comparison: {comparison.stale_reasons_json.join(", ")}
    </p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}

    <section className="comparison-summary-grid">
      {TYPES.map((type) => <button key={type}
        className={filter === type ? "active" : ""}
        onClick={() => setParams({ type })}>
        <strong>{Number(comparison.summary_json[type] ?? 0)}</strong>
        <span>{type.replaceAll("_", " ")}</span>
      </button>)}
      <button onClick={() => setParams({})}><strong>{comparison.findings.length}</strong><span>all convention findings</span></button>
    </section>

    <div className="finding-separation">
      <section className="panel">
        <span className="eyebrow">Deterministic validation</span>
        <h2>{side.deterministic_findings.length} machine/controller rule findings</h2>
        <p>Axis limits, restricted commands, spindle limits, and parser findings remain safety-oriented deterministic checks.</p>
      </section>
      <section className="panel">
        <span className="eyebrow">Organizational conventions</span>
        <h2>{comparison.findings.filter((item) => item.comparison_type !== "matches").length} historical-pattern differences</h2>
        <p>These describe differences from accepted examples. They are not assigned deterministic safety severity.</p>
      </section>
      <section className="panel">
        <span className="eyebrow">Manual-based explanation</span>
        <h2>Separate citation workflow</h2>
        <p>Controller and company-standard explanations remain grounded in uploaded documentation.</p>
      </section>
    </div>

    <section className="panel comparison-findings">
      <header><div><span className="eyebrow">Exact line references</span><h2>Convention findings</h2></div>
        <label>Difference filter<select value={filter}
          onChange={(e) => setParams(e.target.value === "all" ? {} : { type: e.target.value })}>
          <option value="all">All types</option>{TYPES.map((item) => <option key={item}>{item}</option>)}
        </select></label></header>
      <div>{visible.map((item) => <button key={item.id}
        className={`comparison-finding ${item.comparison_type}`}
        onClick={() => setSelected(item)}>
        <span className={`strong-status ${item.comparison_type}`}>{item.comparison_type.replaceAll("_", " ")}</span>
        <strong>{item.title}</strong>
        <p>{item.description}</p>
        <small>{item.line_number ? `Line ${item.line_number}` : "Program-level difference"}</small>
        {item.source_line && <code>{item.source_line}</code>}
        {item.exception_classification && <span>Classified: {item.exception_classification.replaceAll("_", " ")}</span>}
      </button>)}</div>
    </section>

    <section className="panel side-by-side">
      <header><div><span className="eyebrow">Logical sections and lines</span><h2>Current versus reference program</h2></div>
        <small>{String(side.source_metadata.reference_program_name ?? "")} · post {String(side.source_metadata.post_processor_revision ?? "unspecified")}</small></header>
      <div className="diff-grid diff-head"><strong>Reference program</strong><strong>Current program</strong></div>
      {side.sections.map((section, index) => <div className={`diff-grid ${section.type}`} key={index}>
        <div><small>Line {section.reference_line_start} · {section.type}</small>
          <pre>{section.reference_lines.join("\n") || " "}</pre></div>
        <div><small>Line {section.current_line_start} · {section.type}</small>
          <pre>{section.current_lines.join("\n") || " "}</pre></div>
      </div>)}
    </section>

    <section className="panel similar-programs">
      <header><div><span className="eyebrow">Historical retrieval</span><h2>Similar eligible references</h2></div></header>
      <p>Similarity prioritizes examples; it is not a correctness or safety score.</p>
      <div>{similar.map((item) => <article key={item.program.id}>
        <strong>{item.program.name}</strong><span>{item.similarity_score}% structural similarity</span>
        <p>{item.match_reasons.join(" · ")}</p>
        {item.differences.length > 0 && <small>{item.differences.join(" · ")}</small>}
      </article>)}</div>
    </section>

    {selected && <div className="modal-backdrop">
      <section className="review-modal" role="dialog" aria-modal="true" aria-label="Classify program difference">
        <header><h2>Classify difference</h2><button aria-label="Close classification" onClick={() => setSelected(null)}>×</button></header>
        <p><strong>{selected.title}</strong></p>
        <label>Classification<select value={classification} onChange={(e) => setClassification(e.target.value)}>
          {[
            "expected_exception", "different_operation_type", "different_post_revision",
            "different_machine_option", "intentional_programmer_choice",
            "requires_investigation", "standard_should_be_updated", "unknown",
          ].map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}
        </select></label>
        <label>Required note<textarea rows={5} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        <p>The standard will not be modified automatically from this exception.</p>
        <button className="button primary" disabled={!note.trim()} onClick={() => void classify()}>Save classification</button>
      </section>
    </div>}
  </section>;
}
