import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { GPostCodeViewer } from "../components/GPostCodeViewer";
import { GPostSourceDrawer } from "../components/GPostSourceDrawer";
import { GPostStatusBadge } from "../components/GPostStatusBadge";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  GPostDraft, GPostMapping, GPostPreview, GPostVersionDiff, MachineProfile,
  MachineProfileRevision, ReferenceProgram, SourceDocument, StandardProfile,
} from "../types";
import {
  draftReviewMetrics, mappingCategory, mappingVisualStatus, MAPPING_CATEGORIES,
  MAPPING_QUEUES, type GPostTab, WORKSPACE_TABS,
} from "./gpostUi";

const SAMPLE_CL = `PPRINT/OPERATION: R&D SAMPLE
LOADTL/2
SPINDL/RPM,2500,CLW
FEDRAT/IPM,12
COOLNT/ON
RAPID
GOTO/1,2,3
GOTO/2,3,4
COOLNT/OFF
FINI`;
const RESULT_TABS = ["generated-code", "cl-trace", "validation", "warnings", "reference-diff"] as const;
const TEMPLATE_GROUPS: Array<[string, Array<[string, string]>]> = [
  ["Program Structure", [["program_header", "Program header"], ["safe_start", "Safe start"], ["program_end", "Program end"], ["footer", "Footer"]]],
  ["Motion", [["rapid_move", "Rapid"], ["linear_feed_move", "Linear interpolation"], ["arc_cw", "CW arc"], ["arc_ccw", "CCW arc"], ["plane_selection", "Plane"]]],
  ["Tooling", [["tool_selection", "Tool selection"], ["tool_change", "Tool change"]]],
  ["Spindle", [["spindle_start_cw", "CW"], ["spindle_start_ccw", "CCW"], ["spindle_stop", "Stop"]]],
  ["Coolant", [["coolant_on", "Coolant on"], ["coolant_off", "Coolant off"]]],
  ["Coordinates", [["units", "Units"], ["distance_mode", "Absolute / incremental"], ["work_offset", "Work offset"], ["reference_return", "Reference return"]]],
  ["Cycles", [["canned_cycle", "Supported cycles"], ["cycle_cancel", "Cycle cancel"]]],
];

function countLabel(count: number, singular: string) { return `${count} ${singular}${count === 1 ? "" : "s"}`; }
function warningText(item: Record<string, unknown>) { return String(item.message ?? item.reason ?? JSON.stringify(item)); }

export function GPostWorkspacePage() {
  const id = Number(useParams().draftId);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const activeTab = (WORKSPACE_TABS.includes(params.get("tab") as GPostTab) ? params.get("tab") : "overview") as GPostTab;
  const queue = params.get("queue") ?? "all";
  const category = params.get("category") ?? "All";
  const resultTab = (RESULT_TABS.includes(params.get("result") as typeof RESULT_TABS[number]) ? params.get("result") : "generated-code") as typeof RESULT_TABS[number];
  const autoAdvance = params.get("auto") !== "0";
  const [draft, setDraft] = useState<GPostDraft | null>(null);
  const [machine, setMachine] = useState<MachineProfile | null>(null);
  const [revision, setRevision] = useState<MachineProfileRevision | null>(null);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [references, setReferences] = useState<ReferenceProgram[]>([]);
  const [standards, setStandards] = useState<StandardProfile[]>([]);
  const [mappings, setMappings] = useState<GPostMapping[]>([]);
  const [versions, setVersions] = useState<GPostDraft[]>([]);
  const [templates, setTemplates] = useState<Record<string, string>>({});
  const [preview, setPreview] = useState<GPostPreview | null>(null);
  const [clSource, setClSource] = useState(SAMPLE_CL);
  const [traceIndex, setTraceIndex] = useState(0);
  const [compareId, setCompareId] = useState(0);
  const [versionDiff, setVersionDiff] = useState<GPostVersionDiff | null>(null);
  const [reviewTemplate, setReviewTemplate] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function updateParams(updates: Record<string, string | null>, replace = false) {
    const next = new URLSearchParams(params);
    Object.entries(updates).forEach(([key, value]) => value ? next.set(key, value) : next.delete(key));
    setParams(next, { replace });
  }

  async function load() {
    setError("");
    try {
      const nextDraft = await api.getGPostDraft(id);
      const [machines, nextMappings, nextDocuments, nextRevisions, nextReferences, nextStandards, nextVersions] = await Promise.all([
        api.listProfiles(), api.listGPostMappings(id), api.listDocuments(nextDraft.machine_profile_id),
        api.listProfileRevisions(nextDraft.machine_profile_id), api.listReferencePrograms(nextDraft.machine_profile_id),
        api.listStandards(nextDraft.machine_profile_id), api.listGPostDrafts(nextDraft.machine_profile_id),
      ]);
      setDraft(nextDraft); setMachine(machines.find((item) => item.id === nextDraft.machine_profile_id) ?? null);
      setRevision(nextRevisions.find((item) => item.id === nextDraft.machine_profile_revision_id) ?? null);
      setMappings(nextMappings); setDocuments(nextDocuments); setReferences(nextReferences);
      setStandards(nextStandards); setVersions(nextVersions.filter((item) => item.name === nextDraft.name));
      setTemplates(nextDraft.templates_json);
      const selectedKey = params.get("mapping");
      const selected = nextMappings.find((item) => item.mapping_key === selectedKey || String(item.id) === selectedKey) ?? nextMappings[0];
      if (selected) { setReviewTemplate(selected.output_template ?? ""); setReviewNote(selected.review_note ?? ""); }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load G-POST workspace."); }
  }
  useEffect(() => { void load(); }, [id]);
  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const visibleMappings = useMemo(() => mappings.filter((item) => {
    const status = mappingVisualStatus(item);
    const queueMatch = queue === "all" || (queue === "needs-review" && item.review_status === "pending" && status !== "unsupported")
      || (queue === "accepted" && item.review_status.startsWith("accepted")) || (queue === "conflicts" && status === "conflict")
      || (queue === "unsupported" && status === "unsupported") || (queue === "deferred" && item.review_status === "deferred");
    return queueMatch && (category === "All" || mappingCategory(item) === category);
  }), [mappings, queue, category]);
  const selectedMapping = mappings.find((item) => item.mapping_key === params.get("mapping") || String(item.id) === params.get("mapping"))
    ?? visibleMappings[0] ?? null;
  useEffect(() => {
    if (activeTab === "mappings" && selectedMapping && !params.get("mapping")) updateParams({ mapping: selectedMapping.mapping_key }, true);
  }, [activeTab, selectedMapping?.id]);
  useEffect(() => {
    if (!selectedMapping) return;
    setReviewTemplate(selectedMapping.output_template ?? "");
    setReviewNote(selectedMapping.review_note ?? "");
  }, [selectedMapping?.id]);
  const metrics = draft ? draftReviewMetrics(draft, mappings) : { total: 0, reviewed: 0, percent: 0, unsupported: 0, warnings: 0 };
  const selectedDocument = documents.find((item) => item.id === selectedMapping?.source_document_id) ?? null;
  const drawerOpen = params.get("source") === "1" && Boolean(selectedMapping);
  const selectedTrace = preview?.traceability_json[traceIndex];
  const approvedStandard = standards.find((item) => item.id === draft?.standard_profile_id);
  const selectedReferences = references.filter((item) => draft?.reference_program_ids_json.includes(item.id));

  function selectMapping(mapping: GPostMapping) {
    updateParams({ mapping: mapping.mapping_key }); setReviewTemplate(mapping.output_template ?? ""); setReviewNote(mapping.review_note ?? "");
  }

  async function reviewMapping(status: "accepted" | "accepted_with_edit" | "rejected" | "deferred") {
    if (!selectedMapping) return;
    setBusy(true); setError("");
    try {
      const updated = await api.updateGPostMapping(selectedMapping.id, {
        review_status: status, review_note: reviewNote,
        ...(status === "accepted_with_edit" ? { output_template: reviewTemplate } : {}),
      });
      const nextRows = mappings.map((item) => item.id === updated.id ? updated : item);
      setMappings(nextRows); setToast(`${updated.cl_command} marked ${status.replaceAll("_", " ")}.`);
      window.setTimeout(() => setToast(""), 2800);
      if (autoAdvance) {
        const currentIndex = visibleMappings.findIndex((item) => item.id === selectedMapping.id);
        const next = [...visibleMappings.slice(currentIndex + 1), ...visibleMappings.slice(0, currentIndex)]
          .find((item) => item.id !== selectedMapping.id && item.review_status === "pending" && item.supported);
        if (next) selectMapping(next);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Mapping review failed."); }
    finally { setBusy(false); }
  }

  async function saveConfiguration() {
    if (!draft) return;
    setBusy(true);
    try { const updated = await api.updateGPostDraft(draft.id, { templates_json: templates }); setDraft(updated); setToast("Draft configuration saved."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Save failed."); } finally { setBusy(false); }
  }

  async function toggleDocument(documentId: number) {
    if (!draft) return;
    const selected = new Set(draft.selected_document_ids_json);
    selected.has(documentId) ? selected.delete(documentId) : selected.add(documentId);
    try { const updated = await api.updateGPostDraft(draft.id, { selected_document_ids: [...selected] }); setDraft(updated); setToast("Source selection updated."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Source update failed."); }
  }

  async function generatePreview() {
    if (!draft) return;
    setBusy(true); setError("");
    try { const result = await api.previewGPost(draft.id, clSource); setPreview(result); setTraceIndex(0); updateParams({ result: "generated-code" }); setToast(result.status === "blocked" ? "Preview generated with blocking issues." : "Preview generated, reparsed, and validated."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Preview generation failed."); } finally { setBusy(false); }
  }

  async function createVersion() {
    if (!draft) return;
    try { const created = await api.createGPostVersion(draft.id); navigate(`/gpost/${created.id}?tab=overview`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Version creation failed."); }
  }

  async function compareVersions() {
    if (!draft || !compareId) return;
    try { setVersionDiff(await api.compareGPostVersions(draft.id, compareId)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Version comparison failed."); }
  }

  if (!draft || !machine) return <section className="page">{error ? <p className="form-error">{error}</p> : <p className="loading">Loading G-POST workspace…</p>}</section>;
  const axes = (draft.capability_snapshot_json.configured_axes as string[] | undefined)?.join(" / ") || "Unknown";
  const generationStatus = !preview ? "Pending" : preview.status === "blocked" ? "Blocked" : preview.warnings_json.length ? "Warning" : "Pass";

  return <section className="page gpost-workspace-page">
    <div className="gpost-toast-region" role="region" aria-label="Notifications">{toast && <div className="gpost-toast" role="status"><span>{toast}</span><button type="button" aria-label="Dismiss notification" onClick={() => setToast("")}>×</button></div>}</div>
    <header className="gpost-workspace-header"><div><Link to="/gpost" className="gpost-back-link">← G-POST Generator</Link><h1 className="gpost-draft-title">{draft.name}</h1><p>{machine.name} · {machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</p></div><div className="gpost-header-actions"><GPostStatusBadge status={draft.status} large /><button disabled={busy} onClick={() => void saveConfiguration()}>Save</button><button onClick={() => void createVersion()}>New Version</button><details><summary>Export</summary><a href={api.gpostExportUrl(draft.id, "json")}>JSON</a><a href={api.gpostExportUrl(draft.id, "markdown")}>Markdown</a></details><details><summary>More</summary><button onClick={() => void api.archiveGPostDraft(draft.id).then(setDraft)}>Archive Draft</button></details></div></header>
    <div className="gpost-persistent-context"><span><small>Machine</small>{machine.model}</span><span><small>Controller</small>{machine.controller_model || machine.controller_name}</span><span><small>Draft Version</small>G-POST v{draft.version}</span><span><small>Status</small><GPostStatusBadge status={draft.status} /></span></div>
    <div className="gpost-progress-strip"><span><strong>{metrics.total}</strong> mappings</span><span><strong>{metrics.reviewed}</strong> reviewed</span><span className={metrics.warnings ? "warning" : ""}><strong>{metrics.warnings}</strong> warnings</span><span><strong>{metrics.unsupported}</strong> unsupported</span><div><progress value={metrics.percent} max={100} /><strong>{metrics.percent}% reviewed</strong></div></div>
    <nav className="gpost-workflow-nav" aria-label="G-POST workflow">{WORKSPACE_TABS.map((tab) => <button key={tab} aria-current={activeTab === tab ? "page" : undefined} className={activeTab === tab ? "active" : ""} onClick={() => updateParams({ tab, ...(tab !== "mappings" ? {} : { mapping: selectedMapping?.mapping_key ?? null }) })}>{tab.replaceAll("-", " ")}</button>)}</nav>
    {error && <p className="form-error" role="alert">{error}</p>}

    {activeTab === "overview" && <div className="gpost-overview-grid"><section className="panel gpost-overview-machine"><header><h2>Machine</h2><Link to={`/machines/${machine.id}/revisions`}>Review profile</Link></header><dl><div><dt>Machine</dt><dd><strong>{machine.name}</strong><small>{machine.machine_type.replaceAll("_", " ")}</small></dd></div><div><dt>Controller</dt><dd><strong>{machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</strong><small>{machine.controller_version || "Version not recorded"}</small></dd></div><div><dt>Axes</dt><dd><strong>{axes}</strong><small>{machine.axis_count} configured axes</small></dd></div><div><dt>Profile Revision</dt><dd><strong>v{revision?.revision_number}</strong><small>{revision?.status}</small></dd></div></dl></section><section className="panel gpost-overview-readiness"><header><h2>G-POST Readiness</h2><span>{metrics.percent}%</span></header><ul><li className="pass"><span>Machine Configuration</span><strong>✓</strong></li><li className="pass"><span>Controller Configuration</span><strong>✓</strong></li><li className={draft.selected_document_ids_json.length ? "pass" : "warning"}><span>Documents</span><strong>{draft.selected_document_ids_json.length ? "✓" : "Review"}</strong></li><li className={metrics.reviewed === metrics.total ? "pass" : "warning"}><span>Mappings</span><strong>{metrics.reviewed} / {metrics.total}</strong></li><li><span>Validation</span><strong>{generationStatus}</strong></li><li><span>Reference Comparison</span><strong>{preview ? "Available" : "Pending"}</strong></li></ul></section><section className="panel gpost-open-issues"><header><h2>Open Issues</h2><span>Actionable only</span></header><button onClick={() => updateParams({ tab: "mappings", queue: "needs-review" })}><strong>{countLabel(mappings.filter((item) => item.review_status === "pending" && item.supported).length, "mapping")} need review</strong><span>Open Mappings →</span></button><button onClick={() => updateParams({ tab: "mappings", queue: "unsupported" })}><strong>{countLabel(metrics.unsupported, "command")} unsupported</strong><span>Review unsupported →</span></button>{draft.warnings_json.map((item, index) => <button key={index} onClick={() => updateParams({ tab: "validation" })}><strong>{warningText(item)}</strong><span>Inspect warning →</span></button>)}</section></div>}

    {activeTab === "sources" && <div className="gpost-sources-tab"><section className="panel"><header><div><h2>Machine Profile</h2><p>Exact immutable revision used by this G-POST version.</p></div><GPostStatusBadge status={revision?.status ?? "draft"} /></header><div className="gpost-source-summary"><strong>{machine.name}</strong><span>Revision v{revision?.revision_number} · {axes} · {machine.controller_model || machine.controller_name}</span><Link to={`/machines/${machine.id}/revisions`}>View Profile</Link></div></section><section className="panel"><header><div><h2>Reference Documents</h2><p>Only documents owned by {machine.name} are available.</p></div><span>{draft.selected_document_ids_json.length} selected</span></header><div className="gpost-source-table"><table><thead><tr><th>Document</th><th>Category</th><th>Status</th><th>Pages</th><th>Actions</th></tr></thead><tbody>{documents.map((document) => { const included = draft.selected_document_ids_json.includes(document.id); return <tr key={document.id}><td><strong>{document.title}</strong></td><td>{document.document_type.replaceAll("_", " ")}</td><td><GPostStatusBadge status={included ? "accepted" : "deferred"} /></td><td>{document.page_count ?? "—"} pages</td><td><div className="gpost-row-actions"><Link to={`/documents/${document.id}`}>View</Link><button onClick={() => void toggleDocument(document.id)}>{included ? "Exclude" : "Include"}</button></div></td></tr>; })}</tbody></table></div></section><section className="gpost-sources-split"><article className="panel"><header><h2>Approved Programs</h2><span>{selectedReferences.length} selected</span></header>{selectedReferences.length ? selectedReferences.map((program) => <div className="gpost-evidence-row" key={program.id}><strong>{program.name}</strong><span>Post {program.post_processor_revision || "unspecified"}</span><small>{program.approval_status.replaceAll("_", " ")}</small></div>) : <div className="gpost-compact-empty"><p>No approved programs selected.</p><Link className="button secondary" to={`/machines/${machine.id}/reference-programs`}>Select Programs</Link></div>}</article><article className="panel"><header><h2>Programming Standards</h2></header>{approvedStandard ? <div className="gpost-evidence-row"><strong>{approvedStandard.name} v{approvedStandard.revision_number}</strong><span>{approvedStandard.conventions.filter((item) => item.review_status === "accepted").length} accepted conventions</span><small>Organizational evidence—not controller documentation</small></div> : <div className="gpost-compact-empty"><p>No programming standard selected.</p><Link className="button secondary" to={`/machines/${machine.id}/reference-programs`}>Select Standard</Link></div>}</article></section></div>}

    {activeTab === "configuration" && <section className="gpost-configuration-tab"><header><div><h2>Post Configuration</h2><p>Review readable template groups. Raw configuration JSON remains hidden.</p></div><button className="button primary" disabled={busy} onClick={() => void saveConfiguration()}>Save Configuration</button></header>{TEMPLATE_GROUPS.map(([group, fields]) => <details className="panel" key={group} open={group === "Program Structure"}><summary><div><strong>{group}</strong><small>{fields.filter(([key]) => Boolean(templates[key])).length}/{fields.length} configured</small></div><GPostStatusBadge status={fields.every(([key]) => Boolean(templates[key])) ? "accepted" : fields.some(([key]) => Boolean(templates[key])) ? "pending" : "unsupported"} /></summary><div>{fields.map(([key, label]) => <label key={key}><span>{label}<GPostStatusBadge status={templates[key] ? "accepted" : key.includes("arc") || key.includes("cycle") ? "unsupported" : "pending"} /></span><textarea rows={templates[key]?.includes("\n") ? 3 : 2} value={templates[key] ?? ""} placeholder="Unknown / not configured" onChange={(event) => setTemplates((current) => ({ ...current, [key]: event.target.value }))} /></label>)}</div></details>)}</section>}

    {activeTab === "mappings" && <div className="gpost-mapping-workspace"><aside className="gpost-mapping-filters panel"><h2>Mappings</h2><nav>{MAPPING_QUEUES.map(([key, label]) => <button key={key} className={queue === key ? "active" : ""} onClick={() => updateParams({ queue: key, mapping: null })}><span>{label}</span><strong>{mappings.filter((item) => key === "all" || key === "needs-review" && item.review_status === "pending" && item.supported || key === "accepted" && item.review_status.startsWith("accepted") || key === "unsupported" && !item.supported || key === "deferred" && item.review_status === "deferred" || key === "conflicts" && mappingVisualStatus(item) === "conflict").length}</strong></button>)}</nav><h3>Categories</h3><nav><button className={category === "All" ? "active" : ""} onClick={() => updateParams({ category: null, mapping: null })}>All categories</button>{MAPPING_CATEGORIES.map((item) => <button key={item} className={category === item ? "active" : ""} onClick={() => updateParams({ category: item, mapping: null })}>{item}</button>)}</nav></aside><section className="gpost-mapping-list panel"><header><div><h2>{queue.replaceAll("-", " ")}</h2><p>{visibleMappings.length} mappings shown</p></div><label className="auto-advance-toggle"><input type="checkbox" checked={autoAdvance} onChange={(event) => updateParams({ auto: event.target.checked ? null : "0" })} /> Auto-advance</label></header><div>{visibleMappings.map((mapping) => <button key={mapping.id} className={selectedMapping?.id === mapping.id ? "selected" : ""} onClick={() => selectMapping(mapping)}><div><strong>{mapping.cl_command}</strong><small>{mappingCategory(mapping)} · {mapping.mapping_type}</small></div><code>{mapping.output_template || "No generated pattern"}</code><GPostStatusBadge status={mappingVisualStatus(mapping)} large /></button>)}</div></section><aside className="gpost-mapping-detail panel">{selectedMapping ? <><header><div><span className="eyebrow">Selected Mapping</span><h2>{selectedMapping.cl_command}</h2></div><GPostStatusBadge status={mappingVisualStatus(selectedMapping)} large /></header><section><h3>Generated Pattern</h3><textarea aria-label="Generated Pattern" rows={3} disabled={!selectedMapping.supported} value={reviewTemplate} onChange={(event) => setReviewTemplate(event.target.value)} /></section><dl><div><dt>Status</dt><dd><GPostStatusBadge status={mappingVisualStatus(selectedMapping)} /></dd></div><div><dt>Confidence</dt><dd>{selectedMapping.confidence == null ? "Not scored" : selectedMapping.confidence >= .8 ? "High" : selectedMapping.confidence >= .6 ? "Medium" : "Low"}</dd></div><div><dt>Scope</dt><dd>{selectedMapping.machine_type_scope} · {selectedMapping.dialect_scope}</dd></div></dl><section className="gpost-evidence-block"><h3>Source Evidence</h3>{selectedDocument ? <button onClick={() => updateParams({ source: "1" })}><strong>{selectedDocument.title}</strong><span>Page {selectedMapping.source_page ?? "—"} · {selectedMapping.source_section || "Section not recorded"}</span><small>View Source →</small></button> : <p>Manual configuration / no document evidence</p>}</section><section className="gpost-evidence-block"><h3>Reference Program Evidence</h3><p>Observed context available from {selectedReferences.length} selected approved programs.</p></section><section className="gpost-evidence-block"><h3>Organizational Standard</h3><p>{approvedStandard ? `${approvedStandard.conventions.filter((item) => item.review_status === "accepted").length} accepted conventions are available for scoped review.` : "No approved standard selected."}</p></section><label>Review note<textarea rows={3} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} /></label><div className="gpost-review-actions"><button disabled={busy || !selectedMapping.supported} className="button primary" onClick={() => void reviewMapping("accepted")}>Accept</button><button disabled={busy || !selectedMapping.supported} onClick={() => void reviewMapping("accepted_with_edit")}>Edit &amp; Accept</button><button disabled={busy} onClick={() => void reviewMapping("rejected")}>Reject</button><button disabled={busy} onClick={() => void reviewMapping("deferred")}>Defer</button></div></> : <p>Select a mapping to review.</p>}</aside></div>}

    {activeTab === "test" && <section className="gpost-test-tab"><header><h2>Test G-POST Draft</h2><p>Run Creo CL/NCL through the current draft configuration and inspect the generated R&D G-code.</p></header><div className="gpost-test-inputs"><section className="panel"><header><strong>CL / NCL Input</strong><label className="button secondary">Upload CL File<input aria-label="Upload CL File" type="file" accept=".cl,.ncl,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) void file.text().then(setClSource); }} /></label></header><textarea aria-label="CL / NCL Input" rows={18} value={clSource} onChange={(event) => setClSource(event.target.value)} /></section><section className="panel"><header><strong>Generated G-code</strong><span>R&D preview</span></header>{preview ? <GPostCodeViewer code={preview.generated_gcode} /> : <div className="gpost-test-placeholder"><span>⌁</span><strong>No preview generated</strong><p>Generate a preview after reviewing the current mappings.</p></div>}</section></div><div className="gpost-generate-bar"><p>Existing CL parser → reviewed mappings → G-code parser → deterministic rules</p><button className="button primary" disabled={busy || !clSource.trim()} onClick={() => void generatePreview()}>{busy ? "Generating…" : "Generate Preview"}</button></div>{preview && <><nav className="gpost-result-tabs">{RESULT_TABS.map((tab) => <button key={tab} className={resultTab === tab ? "active" : ""} onClick={() => updateParams({ result: tab })}>{tab.replaceAll("-", " ")}</button>)}</nav><div className="gpost-test-results">{resultTab === "generated-code" && <GPostCodeViewer code={preview.generated_gcode} title="Generated Code" />}{resultTab === "cl-trace" && <div className="gpost-trace-table-layout"><table><thead><tr><th>CL Line</th><th>CL Command</th><th>Mapping</th><th>Generated Block</th><th>Status</th></tr></thead><tbody>{preview.traceability_json.map((item, index) => <tr key={index} className={traceIndex === index ? "selected" : ""} onClick={() => setTraceIndex(index)}><td>{String(item.source_cl_line)}</td><td><code>{String(item.source_cl_text)}</code></td><td>{String(item.cl_command)} · #{String(item.mapping_id)}</td><td><code>{String(item.generated_gcode)}</code></td><td>✓</td></tr>)}</tbody></table>{selectedTrace && <aside><h3>Trace rationale</h3><dl><div><dt>Mapping version</dt><dd>v{String(selectedTrace.mapping_version)}</dd></div><div><dt>Template</dt><dd><code>{String(selectedTrace.template_used ?? "State transition")}</code></dd></div><div><dt>State before</dt><dd><code>{JSON.stringify(selectedTrace.state_before)}</code></dd></div><div><dt>State after</dt><dd><code>{JSON.stringify(selectedTrace.state_after)}</code></dd></div><div><dt>Evidence</dt><dd><code>{JSON.stringify(selectedTrace.source_evidence)}</code></dd></div></dl></aside>}</div>}{resultTab === "validation" && <ValidationSummary preview={preview} />}{resultTab === "warnings" && <div className="gpost-warning-list">{[...draft.warnings_json, ...preview.warnings_json, ...preview.unsupported_commands_json, ...preview.missing_mappings_json].map((item, index) => <article key={index}><strong>{String(item.category ?? item.command ?? "Warning")}</strong><p>{warningText(item)}</p></article>)}</div>}{resultTab === "reference-diff" && <ReferenceDifference programs={selectedReferences} preview={preview} />}</div></>}</section>}

    {activeTab === "validation" && <section className="gpost-validation-tab"><header><h2>Validation</h2><p>Generation, parser, machine, command, and historical evidence remain separate.</p></header>{preview ? <ValidationSummary preview={preview} /> : <div className="gpost-validation-empty panel"><h2>Validation pending</h2><p>Generate an R&D preview from the Test tab before reviewing validation.</p><button className="button primary" onClick={() => updateParams({ tab: "test" })}>Open Test</button></div>}</section>}

    {activeTab === "versions" && <section className="gpost-versions-tab"><header><div><h2>Version History</h2><p>Historical versions remain read-only and are never silently overwritten.</p></div><button className="button primary" onClick={() => void createVersion()}>New Version</button></header><div className="gpost-version-layout"><section className="panel"><table><thead><tr><th>Version</th><th>Status</th><th>Updated</th><th>Action</th></tr></thead><tbody>{versions.sort((a, b) => b.version - a.version).map((item) => <tr key={item.id}><td><strong>v{item.version}</strong></td><td><GPostStatusBadge status={item.status} /></td><td>{new Date(item.updated_at).toLocaleString()}</td><td>{item.id === draft.id ? "Current" : <Link to={`/gpost/${item.id}?tab=versions`}>Open</Link>}</td></tr>)}</tbody></table></section><section className="panel"><h2>Compare Versions</h2><div className="gpost-version-controls"><select aria-label="Compare version" value={compareId} onChange={(event) => setCompareId(Number(event.target.value))}><option value={0}>Select historical version</option>{versions.filter((item) => item.id !== draft.id).map((item) => <option key={item.id} value={item.id}>v{item.version} · {item.status}</option>)}</select><button onClick={() => void compareVersions()}>Compare</button></div>{versionDiff ? <dl className="gpost-version-diff">{Object.entries(versionDiff).filter(([key]) => !key.endsWith("draft_id")).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{Array.isArray(value) && value.length ? value.map(String).join(", ") : "None"}</dd></div>)}</dl> : <p>Select a version to inspect technical changes.</p>}</section></div></section>}

    <SafetyBanner title="Non-production configuration" message="R&D ONLY · NON-PRODUCTION · NOT VALIDATED FOR MACHINE USE. Generated output requires qualified review and controlled simulation." />
    {drawerOpen && selectedMapping && <GPostSourceDrawer mapping={selectedMapping} document={selectedDocument} onClose={() => updateParams({ source: null }, true)} />}
  </section>;
}

function ValidationSummary({ preview }: { preview: GPostPreview }) {
  const findings = preview.deterministic_findings_json;
  const limits = findings.filter((item) => item.category === "machine_limits");
  const commands = findings.filter((item) => item.category === "commands");
  const summary = [
    ["Generation", preview.status === "blocked" ? "Blocked" : preview.warnings_json.length ? "Warning" : "Pass"],
    ["Parser", preview.parser_diagnostics_json.length ? "Warnings" : "Pass"],
    ["Machine Limits", limits.length ? "Findings" : "Pass"],
    ["Supported Commands", commands.length || preview.unsupported_commands_json.length ? "Findings" : "Pass"],
    ["Reference Comparison", "Not Run"],
  ];
  return <div className="gpost-validation-summary"><div className="gpost-validation-cards">{summary.map(([label, status]) => <article key={label}><span>{label}</span><GPostStatusBadge status={status.toLowerCase().replaceAll(" ", "_")} large /></article>)}</div><section className="panel"><h2>Detailed Findings</h2>{!findings.length && !preview.parser_diagnostics_json.length ? <p>No parser or deterministic findings.</p> : <>{preview.parser_diagnostics_json.map((item) => <article className="gpost-finding" key={item}><GPostStatusBadge status="pending" /><div><strong>Parser diagnostic</strong><p>{item}</p></div></article>)}{findings.map((item, index) => <article className="gpost-finding" key={index}><GPostStatusBadge status={String(item.severity)} /><div><strong>{String(item.title)}</strong><p>{String(item.description)}</p><small>{String(item.category)} · {String(item.rule_id)}</small></div></article>)}</>}</section></div>;
}

function ReferenceDifference({ programs, preview }: { programs: ReferenceProgram[]; preview: GPostPreview }) {
  return <div className="gpost-reference-diff"><header><div><h2>Reference Difference</h2><p>Historical program evidence remains separate from deterministic validation.</p></div><GPostStatusBadge status={programs.length ? "pending" : "deferred"} /></header>{programs.length ? programs.map((program) => <article key={program.id}><strong>{program.name}</strong><span>Post revision {program.post_processor_revision || "unspecified"}</span><small>{String(program.validation_summary_json.blocking_count ?? 0)} historical blocking findings · comparison not automatically authoritative</small></article>) : <p>No approved reference program is selected for this draft.</p>}<p className="field-help">Preview #{preview.id} generated {String(preview.summary_json.generated_block_count)} mapped blocks. A structural reference comparison is not run automatically.</p></div>;
}
