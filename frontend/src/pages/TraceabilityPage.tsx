import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { AlignmentIssue, AlignmentLink, AlignmentRun, AnalysisProject, CLRecord, GCodeBlock } from "../types";

const PAGE_SIZE = 200;

export function TraceabilityPage() {
  const { analysisId } = useParams();
  const id = Number(analysisId);
  const [project, setProject] = useState<AnalysisProject | null>(null);
  const [runs, setRuns] = useState<AlignmentRun[]>([]);
  const [run, setRun] = useState<AlignmentRun | null>(null);
  const [cl, setCL] = useState<CLRecord[]>([]);
  const [gcode, setGCode] = useState<GCodeBlock[]>([]);
  const [links, setLinks] = useState<AlignmentLink[]>([]);
  const [issues, setIssues] = useState<AlignmentIssue[]>([]);
  const [selectedCL, setSelectedCL] = useState<number | null>(null);
  const [selectedGCode, setSelectedGCode] = useState<number | null>(null);
  const [selectedLink, setSelectedLink] = useState<number | null>(null);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadRun(value: AlignmentRun) {
    setRun(value);
    const [recordData, blockData, linkData, issueData] = await Promise.all([
      api.listCLRecords(id, 1, PAGE_SIZE), api.listGCodeBlocks(id, 1, PAGE_SIZE),
      api.listAlignmentLinks(value.id), api.listAlignmentIssues(value.id),
    ]);
    setCL(recordData); setGCode(blockData); setLinks(linkData); setIssues(issueData);
  }
  useEffect(() => {
    Promise.all([api.getProject(id), api.listAlignmentRuns(id)])
      .then(async ([projectData, runData]) => {
        setProject(projectData); setRuns(runData);
        if (runData[0]) await loadRun(runData[0]);
      }).catch((cause) => setError(cause.message));
  }, [id]);

  async function start() {
    setBusy(true); setError("");
    try {
      const value = await api.createAlignmentRun(id);
      setRuns((current) => [value, ...current]); await loadRun(value);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Alignment failed"); }
    finally { setBusy(false); }
  }
  const updateLocal = (value: AlignmentLink) =>
    setLinks((current) => current.map((item) => item.id === value.id ? value : item));
  const selected = links.find((item) => item.id === selectedLink) ??
    links.find((item) => item.cl_record_id === selectedCL || item.gcode_block_id === selectedGCode);
  const linkedCL = new Set(links.filter((item) => item.gcode_block_id === selectedGCode || item.id === selected?.id).map((item) => item.cl_record_id));
  const linkedG = new Set(links.filter((item) => item.cl_record_id === selectedCL || item.id === selected?.id).map((item) => item.gcode_block_id));
  const visibleLinks = useMemo(() => links.filter((item) => {
    if (filter === "high") return item.confidence >= .9;
    if (filter === "medium") return item.confidence >= .7 && item.confidence < .9;
    if (filter === "low") return item.confidence < .7;
    if (["confirmed", "rejected", "proposed"].includes(filter)) return item.status === filter;
    return true;
  }), [links, filter]);
  const nextIssue = (kind: "cl" | "gcode") => {
    const issue = issues.find((value) => kind === "cl" ? value.cl_record_id : value.gcode_block_id);
    if (kind === "cl") setSelectedCL(issue?.cl_record_id ?? null);
    else setSelectedGCode(issue?.gcode_block_id ?? null);
  };

  if (!project) return <section className="page">{error ? <p role="alert" className="form-error">{error}</p> : <p>Loading traceability…</p>}</section>;
  return <section className="page traceability-page">
    <PageHeader eyebrow={`Analysis #${id}`} title="CL / G-code Traceability" description={`${project.name} · deterministic inferred alignment`} action={<Link className="button secondary" to={`/analysis/${id}`}>Validation results</Link>} />
    <aside className="safety-banner" role="alert"><span className="safety-icon">!</span><div><strong>Alignment is inferred</strong><p>CL-to-G-code alignment does not certify post correctness, machining safety, or production readiness. Qualified review and simulation remain required.</p></div></aside>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="trace-toolbar">
      <button className="button primary" disabled={busy} onClick={() => void start()}>{busy ? "Parsing and aligning…" : run ? "Create new alignment version" : "Parse and run alignment"}</button>
      {runs.length > 0 && <label>Version<select value={run?.id ?? ""} onChange={(e) => { const value = runs.find((item) => item.id === Number(e.target.value)); if (value) void loadRun(value); }}>{runs.map((item) => <option key={item.id} value={item.id}>Alignment v{item.version}{item.stale ? " — stale" : ""}</option>)}</select></label>}
      <label>Links<select aria-label="Confidence filter" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All confidence</option><option value="high">High confidence</option><option value="medium">Medium confidence</option><option value="low">Low confidence</option><option value="proposed">Proposed</option><option value="confirmed">Confirmed</option><option value="rejected">Rejected</option></select></label>
      <button onClick={() => nextIssue("cl")}>Next unmatched CL</button><button onClick={() => nextIssue("gcode")}>Next unmatched G-code</button>
      {run && selectedCL && selectedGCode && !selected && <button onClick={() => void api.createManualAlignmentLink(run.id, selectedCL, selectedGCode).then((value) => { setLinks((current) => [...current, value]); setSelectedLink(value.id); })}>Add manual link</button>}
      {run && <a className="button secondary" href={api.alignmentReportUrl(run.id)}>Export report</a>}
    </div>
    {run?.stale && <p className="stale-notice">This alignment is stale because a source changed. Create a new version for current results.</p>}
    {run && <div className="trace-summary">{Object.entries(run.summary_json).slice(0, 8).map(([key, value]) => <div key={key}><strong>{String(value)}</strong><small>{key.replaceAll("_", " ")}</small></div>)}</div>}
    {!run ? <div className="empty-state"><h2>No alignment run yet</h2><p>Both CL and G-code sources are required. Parsing preserves unsupported records for review.</p></div> :
    <div className="trace-grid">
      <section className="trace-source-panel"><header><strong>CL / NCL</strong><small>{cl.length} loaded · paginated</small></header><div className="trace-scroll">{cl.map((record) => <button id={`cl-${record.id}`} className={selectedCL === record.id || linkedCL.has(record.id) ? "trace-row selected" : "trace-row"} key={record.id} onClick={() => { setSelectedCL(record.id); setSelectedLink(null); }}><span>{record.record_index}</span><code>{record.original_text}</code><small>{record.command} · {record.motion_type ?? "state"}{record.tool_number ? ` · T${record.tool_number}` : ""}{record.parse_errors_json.length ? " · parse issue" : ""}</small></button>)}</div></section>
      <section className="relationship-panel"><header><strong>Relationships</strong><small>{visibleLinks.length} shown</small></header><div className="trace-scroll">{visibleLinks.map((link) => <button className={selected?.id === link.id ? "relationship-card selected" : "relationship-card"} key={link.id} onClick={() => { setSelectedLink(link.id); setSelectedCL(link.cl_record_id); setSelectedGCode(link.gcode_block_id); }}><strong>{Math.round(link.confidence * 100)}% · {link.link_type}</strong><span>{link.status}</span><small>CL {link.cl_record_id} → G-code {link.gcode_block_id}</small></button>)}</div></section>
      <section className="trace-source-panel"><header><strong>G-code</strong><small>{gcode.length} loaded · paginated</small></header><div className="trace-scroll">{gcode.map((block) => <button id={`gc-${block.id}`} className={selectedGCode === block.id || linkedG.has(block.id) ? "trace-row selected" : "trace-row"} key={block.id} onClick={() => { setSelectedGCode(block.id); setSelectedLink(null); }}><span>{block.block_index}</span><code>{block.original_text}</code><small>{[...block.g_codes_json, ...block.m_codes_json].join(" ")} · {block.motion_mode ?? "state"}{block.tool_number ? ` · T${block.tool_number}` : ""}{block.parse_errors_json.length ? " · parse issue" : ""}</small></button>)}</div></section>
    </div>}
    {selected && <section className="relationship-details"><header><div><span className="eyebrow">Deterministic Alignment</span><h2>Relationship details</h2></div><strong>{Math.round(selected.confidence * 100)}% confidence</strong></header><div className="detail-columns"><div><h3>Match reasons</h3><ul>{selected.match_reasons_json.map((value) => <li key={value}>{value}</li>)}</ul></div><div><h3>Mismatch and uncertainty</h3><ul>{selected.mismatch_reasons_json.map((value) => <li key={value}>{value}</li>)}</ul></div><div><h3>Manual review</h3><div className="review-actions"><button onClick={() => void api.confirmAlignmentLink(selected.id).then(updateLocal)}>Confirm</button><button onClick={() => void api.rejectAlignmentLink(selected.id).then(updateLocal)}>Reject</button></div><textarea aria-label="Review note" defaultValue={selected.review_note ?? ""} onBlur={(e) => void api.updateAlignmentLink(selected.id, { review_note: e.target.value, status: "modified" }).then(updateLocal)} placeholder="Add review note" /></div></div><div className="separated-context"><div><strong>Manual-Based Explanation</strong><Link to={`/manual-assistant?machine=${project.machine_profile_id}&question=${encodeURIComponent("Explain this CL-to-G-code relationship using uploaded machine documentation.")}`}>Explain using machine documentation →</Link></div><div><strong>Program Validation Findings</strong><Link to={`/analysis/${id}`}>Open deterministic findings →</Link></div></div></section>}
  </section>;
}
