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
  controllerFamilyCompatible, draftReviewMetrics, mappingCategory, mappingVisualStatus, MAPPING_CATEGORIES,
  MAPPING_QUEUES, templateFamilyCompatible, type GPostTab, WORKSPACE_TABS,
} from "./gpostUi";

const SAMPLE_CL = `PPRINT/OPERATION: OD TURN
LOADTL/2
SPINDL/RPM,1200,CLW
FEDRAT/IPM,12
COOLNT/ON
RAPID
GOTO/1.0,0.1
GOTO/0.8,-1.0
COOLNT/OFF
SPINDL/OFF
FINI`;
const RESULT_TABS = ["generated-code", "cl-trace", "validation", "warnings", "reference-diff"] as const;
const TEMPLATE_GROUPS: Array<[string, Array<[string, string]>]> = [
  ["Program Structure", [["program_header", "Program header"], ["safe_start", "Safe start"], ["footer", "Footer"]]],
  ["Tooling", [["tool_selection", "Tool selection"], ["tool_change", "Tool change"]]],
  ["Spindle", [["spindle_start_cw", "Clockwise start"], ["spindle_start_ccw", "Counter-clockwise start"], ["spindle_stop", "Stop"]]],
  ["Coolant", [["coolant_on", "Coolant on"], ["coolant_off", "Coolant off"]]],
  ["Motion", [["feed_rate", "Feed rate"], ["rapid_move", "Rapid move"], ["linear_feed_move", "Feed move"]]],
  ["Coordinates", [["units", "Units"], ["plane_selection", "Plane"], ["distance_mode", "Absolute / incremental"], ["feed_mode", "Feed mode"], ["work_offset", "Work offset"], ["reference_return", "Reference return"]]],
  ["Program End", [["program_end", "Program end"]]],
  ["Advanced / Future", [["arc_cw", "CW arc"], ["arc_ccw", "CCW arc"], ["canned_cycle", "Supported cycles"], ["cycle_cancel", "Cycle cancel"]]],
];

function mappingDisplayName(mapping: GPostMapping) {
  const suffix = String(mapping.conditions_json.direction ?? mapping.conditions_json.mode ?? "");
  return suffix ? `${mapping.cl_command} / ${suffix}` : mapping.cl_command === "GOTO" ? "GOTO / x,y,z" : mapping.cl_command;
}

function countLabel(count: number, singular: string) { return `${count} ${singular}${count === 1 ? "" : "s"}`; }
function warningText(item: Record<string, unknown>) { return String(item.message ?? item.reason ?? JSON.stringify(item)); }

export function GPostWorkspacePage() {
  const id = Number(useParams().draftId);
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const activeTab = (WORKSPACE_TABS.includes(params.get("tab") as GPostTab) ? params.get("tab") : "overview") as GPostTab;
  const queue = params.get("queue") ?? "required";
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
      setStandards(nextStandards);
      const relatedIds = new Set<number>([nextDraft.id]);
      let changed = true;
      while (changed) {
        changed = false;
        nextVersions.forEach((item) => {
          if ((item.created_from_draft_id && relatedIds.has(item.created_from_draft_id)) || (relatedIds.has(item.id) && item.created_from_draft_id && !relatedIds.has(item.created_from_draft_id))) {
            if (!relatedIds.has(item.id)) { relatedIds.add(item.id); changed = true; }
            if (item.created_from_draft_id && !relatedIds.has(item.created_from_draft_id)) { relatedIds.add(item.created_from_draft_id); changed = true; }
          }
        });
      }
      setVersions(nextVersions.filter((item) => relatedIds.has(item.id)));
      setTemplates(nextDraft.templates_json);
      const selectedKey = params.get("mapping");
      const selected = nextMappings.find((item) => item.mapping_key === selectedKey || String(item.id) === selectedKey) ?? nextMappings[0];
      if (selected) { setReviewTemplate(selected.effective_output_template ?? selected.output_template ?? ""); setReviewNote(selected.review_note ?? ""); }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load G-POST workspace."); }
  }
  useEffect(() => { void load(); }, [id]);
  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 3500);
    return () => window.clearTimeout(timeout);
  }, [toast]);
  useEffect(() => {
    setMappings((rows) => rows.map((mapping) => mapping.uses_override || !mapping.template_key
      ? mapping
      : { ...mapping, effective_output_template: templates[mapping.template_key] ?? null }));
  }, [templates]);

  const visibleMappings = useMemo(() => mappings.filter((item) => {
    const queueMatch = queue === "all" || (queue === "required" && item.required_for_v1)
      || (queue === "needs-review" && item.required_for_v1 && item.review_status === "pending")
      || (queue === "accepted" && item.review_status.startsWith("accepted"))
      || (queue === "not-applicable" && item.support_status === "not_applicable")
      || (queue === "blocking" && item.support_status === "unsupported_required")
      || (queue === "advanced" && item.support_status === "not_implemented");
    return queueMatch && (category === "All" || mappingCategory(item) === category);
  }), [mappings, queue, category]);
  const selectedMapping = mappings.find((item) => item.mapping_key === params.get("mapping") || String(item.id) === params.get("mapping"))
    ?? visibleMappings[0] ?? null;
  useEffect(() => {
    if (activeTab === "mappings" && selectedMapping && !params.get("mapping")) updateParams({ mapping: selectedMapping.mapping_key }, true);
  }, [activeTab, selectedMapping?.id]);
  useEffect(() => {
    if (!selectedMapping) return;
    setReviewTemplate(selectedMapping.uses_override
      ? selectedMapping.template_override ?? ""
      : selectedMapping.template_key ? templates[selectedMapping.template_key] ?? "" : selectedMapping.output_template ?? "");
    setReviewNote(selectedMapping.review_note ?? "");
  }, [selectedMapping?.id, templates]);
  const metrics = draft ? draftReviewMetrics(draft, mappings) : { total: 0, required: 0, reviewed: 0, needsReview: 0, percent: 0, notApplicable: 0, notImplemented: 0, blocking: 0, unsupported: 0, warnings: 0 };
  const selectedDocument = documents.find((item) => item.id === selectedMapping?.source_document_id) ?? null;
  const drawerOpen = params.get("source") === "1" && Boolean(selectedMapping);
  const selectedTrace = preview?.traceability_json[traceIndex];
  const approvedStandard = standards.find((item) => item.id === draft?.standard_profile_id);
  const selectedReferences = references.filter((item) => draft?.reference_program_ids_json.includes(item.id));
  function effectiveMappingTemplate(mapping: GPostMapping) {
    if (mapping.uses_override) return mapping.template_override ?? "";
    if (mapping.template_key) return templates[mapping.template_key] ?? "";
    return mapping.output_template ?? "";
  }

  function selectMapping(mapping: GPostMapping) {
    updateParams({ mapping: mapping.mapping_key }); setReviewTemplate(effectiveMappingTemplate(mapping)); setReviewNote(mapping.review_note ?? "");
  }

  async function reviewMapping(status: "accepted" | "accepted_with_edit" | "rejected" | "deferred") {
    if (!selectedMapping) return;
    setBusy(true); setError("");
    try {
      const updated = await api.updateGPostMapping(selectedMapping.id, {
        review_status: status, review_note: reviewNote,
        ...(status === "accepted_with_edit" ? { template_override: reviewTemplate, uses_override: true } : {}),
      });
      const nextRows = mappings.map((item) => item.id === updated.id ? updated : item);
      setMappings(nextRows); setToast(`${updated.cl_command} marked ${status.replaceAll("_", " ")}.`);
      window.setTimeout(() => setToast(""), 2800);
      if (autoAdvance) {
        const currentIndex = visibleMappings.findIndex((item) => item.id === selectedMapping.id);
        const next = [...visibleMappings.slice(currentIndex + 1), ...visibleMappings.slice(0, currentIndex)]
          .find((item) => item.id !== selectedMapping.id && item.review_status === "pending" && item.required_for_v1 && item.support_status === "supported");
        if (next) selectMapping(next);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Mapping review failed."); }
    finally { setBusy(false); }
  }

  async function markNotApplicable() {
    if (!selectedMapping) return;
    if (selectedMapping.required_for_v1 && !window.confirm("This behavior is required for V1. Continue only when capability rules truly exclude it.")) return;
    try {
      const updated = await api.updateGPostMapping(selectedMapping.id, { support_status: "not_applicable", review_status: "accepted", review_note: reviewNote || "Confirmed not applicable for the selected machine capability." });
      setMappings((rows) => rows.map((item) => item.id === updated.id ? updated : item));
      setToast(`${mappingDisplayName(updated)} marked not applicable.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to mark mapping not applicable."); }
  }

  async function resetOverride() {
    if (!selectedMapping) return;
    try {
      const updated = await api.resetGPostMappingOverride(selectedMapping.id);
      setMappings((rows) => rows.map((item) => item.id === updated.id ? updated : item));
      setReviewTemplate(updated.effective_output_template ?? "");
      setToast("Mapping reset to the shared configuration template.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to reset mapping override."); }
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
  const familyCompatible = templateFamilyCompatible(draft.machine_type, draft.controller_family)
    && controllerFamilyCompatible(revision, draft.controller_family);
  const machineTypeMatches = !revision || draft.machine_type === revision.machine_type;
  const revisionApproved = revision?.status === "approved" || revision?.status === "active";
  const sourceReady = draft.selected_document_ids_json.length > 0 || draft.manual_configuration_acknowledged;
  const setupBlockers = [!familyCompatible, !machineTypeMatches, !revisionApproved, !templates.safe_start, !sourceReady, metrics.blocking > 0].filter(Boolean).length;
  const templateFamilyLabel = draft.controller_family.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

  return <section className="page gpost-workspace-page">
    <div className="gpost-toast-region" role="region" aria-label="Notifications">{toast && <div className="gpost-toast" role="status"><span>{toast}</span><button type="button" aria-label="Dismiss notification" onClick={() => setToast("")}>×</button></div>}</div>
    <header className="gpost-workspace-header"><div><Link to="/gpost" className="gpost-back-link">← G-POST Generator</Link><h1 className="gpost-draft-title">{draft.name}</h1><p>{machine.name} · {machine.controller_manufacturer || machine.controller_name} {machine.controller_model || ""}</p></div><div className="gpost-header-actions"><GPostStatusBadge status={draft.status} large /><button disabled={busy} onClick={() => void saveConfiguration()}>Save</button><button onClick={() => void createVersion()}>New Version</button><details><summary>Export</summary><a href={api.gpostExportUrl(draft.id, "json")}>JSON</a><a href={api.gpostExportUrl(draft.id, "markdown")}>Markdown</a></details><details><summary>More</summary><button onClick={() => void api.archiveGPostDraft(draft.id).then(setDraft)}>Archive Draft</button></details></div></header>
    <div className="gpost-persistent-context"><span><small>Machine</small>{machine.model}</span><span><small>Controller</small>{machine.controller_model || machine.controller_name}</span><span><small>Draft Version</small>G-POST v{draft.version}</span><span><small>Status</small><GPostStatusBadge status={draft.status} /></span></div>
    <div className="gpost-progress-strip"><span><strong>{metrics.required}</strong> required</span><span><strong>{metrics.reviewed}</strong> reviewed</span><span className={metrics.needsReview ? "warning" : ""}><strong>{metrics.needsReview}</strong> needs review</span><span className={metrics.blocking ? "warning" : ""}><strong>{metrics.blocking}</strong> blocking</span><span><strong>{metrics.notApplicable}</strong> N/A</span><div><progress value={metrics.percent} max={100} /><strong>{metrics.reviewed} / {metrics.required} required reviewed · {metrics.percent}%</strong></div></div>
    <nav className="gpost-workflow-nav" aria-label="G-POST workflow">{WORKSPACE_TABS.map((tab) => <button key={tab} aria-current={activeTab === tab ? "page" : undefined} className={activeTab === tab ? "active" : ""} onClick={() => updateParams({ tab, ...(tab !== "mappings" ? {} : { mapping: selectedMapping?.mapping_key ?? null }) })}>{tab.replaceAll("-", " ")}</button>)}</nav>
    {error && <p className="form-error" role="alert">{error}</p>}

    {activeTab === "overview" && <div className="gpost-overview-grid"><section className="panel gpost-overview-machine"><header><h2>Machine</h2><GPostStatusBadge status="inherited" /></header><dl><div><dt>Machine</dt><dd><strong>{machine.name}</strong><small>{draft.machine_type.replaceAll("_", " ")} · Inherited from Machine Profile v{revision?.revision_number}</small></dd></div><div><dt>Controller</dt><dd><strong>{revision?.controller_manufacturer || revision?.controller_name} {revision?.controller_model || ""}</strong><small>Inherited from Machine Profile v{revision?.revision_number}</small></dd></div><div><dt>Axes</dt><dd><strong>{axes}</strong><small>Inherited from Machine Profile v{revision?.revision_number}</small></dd></div><div><dt>Template Family</dt><dd><strong>{templateFamilyLabel}</strong><small>{familyCompatible ? "Compatible with profile" : "Blocking mismatch"}</small></dd></div></dl></section><section className="panel gpost-overview-readiness"><header><h2>G-POST Readiness</h2><GPostStatusBadge status={setupBlockers ? "blocked" : metrics.needsReview ? "pending" : "accepted"} /></header><ul><li className={revision ? "pass" : "warning"}><span>Approved machine profile revision</span><strong>{revision ? `✓ v${revision.revision_number}` : "Blocked"}</strong></li><li className={familyCompatible && machineTypeMatches ? "pass" : "warning"}><span>Template compatibility</span><strong>{familyCompatible && machineTypeMatches ? "✓ Ready" : "Blocked"}</strong></li><li className={sourceReady ? "pass" : "warning"}><span>Required source</span><strong>{sourceReady ? "✓ Ready" : "Review"}</strong></li><li className={metrics.needsReview ? "warning" : "pass"}><span>Required mappings</span><strong>{metrics.reviewed} / {metrics.required} reviewed</strong></li><li><span>Preview validation</span><strong>{generationStatus}</strong></li><li><span>Optional evidence</span><strong>{selectedReferences.length || approvedStandard ? "Selected" : "Not selected"}</strong></li></ul></section><section className="panel gpost-v1-scope"><header><h2>V1 Scope</h2><span>Core post behavior</span></header><p>This draft targets tooling, spindle, feed, coolant, rapid/feed motion, work coordinates, and program structure.</p><small>Advanced cycles, multiaxis behavior, macros, and special machine functions require separate support.</small></section><section className="panel gpost-open-issues"><header><h2>Open Issues</h2><span>Actionable only</span></header>{!familyCompatible && <button onClick={() => navigate("/gpost")}><strong>Blocking setup issue: {draft.machine_type} machine with {templateFamilyLabel}</strong><span>Change Template →</span></button>}<button onClick={() => updateParams({ tab: "mappings", queue: "needs-review" })}><strong>{countLabel(metrics.needsReview, "required mapping")} need review</strong><span>Open Mappings →</span></button>{metrics.blocking > 0 && <button onClick={() => updateParams({ tab: "mappings", queue: "blocking" })}><strong>{countLabel(metrics.blocking, "required behavior")} unsupported</strong><span>Review blocking →</span></button>}{draft.warnings_json.filter((item) => item.code !== "GPOST_TEMPLATE_FAMILY_MISMATCH").map((item, index) => <button key={index} onClick={() => updateParams({ tab: "validation" })}><strong>{warningText(item)}</strong><span>Inspect warning →</span></button>)}</section></div>}

    {activeTab === "sources" && <div className="gpost-sources-tab"><section className="panel"><header><div><h2>Machine Profile</h2><p>Exact immutable revision used by this G-POST version.</p></div><GPostStatusBadge status="inherited" /></header><div className="gpost-source-summary"><strong>{machine.name}</strong><span>Revision v{revision?.revision_number} · {draft.machine_type.replaceAll("_", " ")} · {axes} · {revision?.controller_model || revision?.controller_name}</span><Link to={`/machines/${machine.id}/revisions`}>View Profile</Link></div></section><section className="panel"><header><div><h2>Reference Documents</h2><p>One relevant document or explicit manual-configuration acknowledgement is required.</p></div><span>{draft.selected_document_ids_json.length} selected</span></header><div className="gpost-source-table"><table><thead><tr><th>Document</th><th>Category</th><th>Status</th><th>Pages</th><th>Actions</th></tr></thead><tbody>{documents.map((document) => { const included = draft.selected_document_ids_json.includes(document.id); return <tr key={document.id}><td><strong>{document.title}</strong></td><td>{document.document_type.replaceAll("_", " ")}</td><td><GPostStatusBadge status={included ? "inherited" : "deferred"} /></td><td>{document.page_count ?? "—"} pages</td><td><div className="gpost-row-actions"><Link to={`/documents/${document.id}`}>View</Link><button onClick={() => void toggleDocument(document.id)}>{included ? "Exclude" : "Include"}</button></div></td></tr>; })}</tbody></table></div>{!draft.selected_document_ids_json.length && <label className="gpost-manual-ack"><input type="checkbox" checked={draft.manual_configuration_acknowledged} onChange={(event) => void api.updateGPostDraft(draft.id, { manual_configuration_acknowledged: event.target.checked }).then(setDraft)} /> I acknowledge this draft uses explicit manual configuration without a selected reference document.</label>}</section><section className="gpost-sources-split"><article className="panel"><header><h2>Approved Programs</h2><span>Optional evidence · {selectedReferences.length} selected</span></header>{selectedReferences.length ? selectedReferences.map((program) => <div className="gpost-evidence-row" key={program.id}><strong>{program.name}</strong><span>Post {program.post_processor_revision || "unspecified"}</span><small>{program.approval_status.replaceAll("_", " ")}</small></div>) : <div className="gpost-compact-empty"><p>Optional evidence not selected.</p><Link className="button secondary" to={`/machines/${machine.id}/reference-programs`}>Select Programs</Link></div>}</article><article className="panel"><header><h2>Programming Standards</h2><span>Optional evidence</span></header>{approvedStandard ? <div className="gpost-evidence-row"><strong>{approvedStandard.name} v{approvedStandard.revision_number}</strong><span>{approvedStandard.conventions.filter((item) => item.review_status === "accepted").length} accepted conventions</span><small>Organizational evidence—not controller documentation</small></div> : <div className="gpost-compact-empty"><p>Optional evidence not selected.</p><Link className="button secondary" to={`/machines/${machine.id}/reference-programs`}>Select Standard</Link></div>}</article></section></div>}

    {activeTab === "configuration" && <section className="gpost-configuration-tab"><header><div><h2>Shared Output Templates</h2><p>Mappings reference these templates unless a mapping-specific override is configured.</p></div><button className="button primary" disabled={busy} onClick={() => void saveConfiguration()}>Save Configuration</button></header>{TEMPLATE_GROUPS.map(([group, fields]) => <details className="panel" key={group} open={group === "Program Structure" || group === "Spindle"}><summary><div><strong>{group}</strong><small>{fields.filter(([key]) => Boolean(templates[key])).length}/{fields.length} configured</small></div><GPostStatusBadge status={fields.every(([key]) => Boolean(templates[key])) ? "accepted" : group === "Advanced / Future" ? "not_implemented" : "pending"} /></summary><div>{fields.map(([key, label]) => { const consumers = mappings.filter((item) => item.template_key === key); return <label key={key}><span>{label}<GPostStatusBadge status={consumers.some((item) => item.required_for_v1) ? "pending" : consumers.length ? "accepted" : "deferred"} /></span><textarea rows={templates[key]?.includes("\n") ? 3 : 2} value={templates[key] ?? ""} placeholder="Not configured" onChange={(event) => setTemplates((current) => ({ ...current, [key]: event.target.value }))} /><small>Applicability: {consumers.some((item) => item.required_for_v1) ? "Required for V1" : "Optional / advanced"} · Source: {key === "safe_start" || key === "tool_change" || key === "program_end" ? `Machine Profile v${revision?.revision_number}` : "Base configuration"}</small><small>Used by: {consumers.length ? consumers.map(mappingDisplayName).join(", ") : "No V1 mappings"}</small></label>; })}</div></details>)}</section>}

    {activeTab === "mappings" && <div className="gpost-mapping-workspace"><aside className="gpost-mapping-filters panel"><h2>Mappings</h2><nav>{MAPPING_QUEUES.map(([key, label]) => <button key={key} className={queue === key ? "active" : ""} onClick={() => updateParams({ queue: key, mapping: null })}><span>{label}</span><strong>{mappings.filter((item) => key === "all" || key === "required" && item.required_for_v1 || key === "needs-review" && item.required_for_v1 && item.review_status === "pending" || key === "accepted" && item.review_status.startsWith("accepted") || key === "not-applicable" && item.support_status === "not_applicable" || key === "blocking" && item.support_status === "unsupported_required" || key === "advanced" && item.support_status === "not_implemented").length}</strong></button>)}</nav><h3>Categories</h3><nav><button className={category === "All" ? "active" : ""} onClick={() => updateParams({ category: null, mapping: null })}>All categories</button>{MAPPING_CATEGORIES.map((item) => <button key={item} className={category === item ? "active" : ""} onClick={() => updateParams({ category: item, mapping: null })}>{item}</button>)}</nav></aside><section className="gpost-mapping-list panel"><header><div><h2>{queue.replaceAll("-", " ")}</h2><p>{visibleMappings.length} mappings shown</p></div><label className="auto-advance-toggle"><input type="checkbox" checked={autoAdvance} onChange={(event) => updateParams({ auto: event.target.checked ? null : "0" })} /> Auto-advance</label></header><div>{visibleMappings.map((mapping) => <button key={mapping.id} className={selectedMapping?.id === mapping.id ? "selected" : ""} onClick={() => selectMapping(mapping)}><div><strong>{mappingDisplayName(mapping)}</strong><small>{mapping.description || mappingCategory(mapping)}</small></div><span><small>Template</small><code>{mapping.effective_output_template || "No generated pattern"}</code></span><GPostStatusBadge status={mappingVisualStatus(mapping)} large /></button>)}</div></section><aside className="gpost-mapping-detail panel">{selectedMapping ? <><header><div><span className="eyebrow">Selected Mapping</span><h2>{mappingDisplayName(selectedMapping)}</h2><p>{selectedMapping.description}</p></div><GPostStatusBadge status={mappingVisualStatus(selectedMapping)} large /></header><section><h3>Generated Pattern</h3><textarea aria-label="Generated Pattern" rows={3} disabled={selectedMapping.support_status !== "supported"} value={reviewTemplate} onChange={(event) => setReviewTemplate(event.target.value)} /><p className="gpost-template-source"><strong>Source</strong>{selectedMapping.uses_override ? "Mapping Override" : `Configuration → ${mappingCategory(selectedMapping)} → ${selectedMapping.template_key?.replaceAll("_", " ") || "State behavior"}`}</p>{selectedMapping.uses_override && <div className="variant-warning"><strong>Mapping Override</strong><p>This mapping overrides the shared configuration template.</p><button onClick={() => void resetOverride()}>Reset to Configuration Template</button></div>}</section><dl><div><dt>Support</dt><dd><GPostStatusBadge status={selectedMapping.support_status} /></dd></div><div><dt>Review</dt><dd><GPostStatusBadge status={selectedMapping.review_status} /></dd></div><div><dt>Applicability</dt><dd>{selectedMapping.required_for_v1 ? "Required for V1" : "Optional / advanced"}</dd></div></dl><section className="gpost-evidence-block"><h3>Source Evidence</h3>{selectedDocument ? <button onClick={() => updateParams({ source: "1" })}><strong>{selectedDocument.title}</strong><span>Page {selectedMapping.source_page ?? "—"} · {selectedMapping.source_section || "Section not recorded"}</span><small>View Source →</small></button> : <p>Shared configuration / capability registry</p>}</section><label>Review note<textarea rows={3} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} /></label><div className="gpost-review-actions"><button disabled={busy || selectedMapping.support_status !== "supported"} className="button primary" onClick={() => void reviewMapping("accepted")}>Accept</button><button disabled={busy || selectedMapping.support_status !== "supported"} onClick={() => void reviewMapping("accepted_with_edit")}>Edit &amp; Accept</button><button disabled={busy} onClick={() => void reviewMapping("rejected")}>Reject</button><button disabled={busy} onClick={() => void reviewMapping("deferred")}>Defer</button><button disabled={busy || selectedMapping.support_status === "unsupported_required"} onClick={() => void markNotApplicable()}>Mark Not Applicable</button></div></> : <p>Select a mapping to review.</p>}</aside></div>}

    {activeTab === "test" && <section className="gpost-test-tab"><header><h2>Test G-POST Draft</h2><p>Run known Creo CL/NCL through the current draft and inspect traceable R&amp;D output.</p></header><section className="panel gpost-preflight"><header><h3>Preflight</h3><GPostStatusBadge status={setupBlockers ? "blocked" : metrics.needsReview ? "pending" : "accepted"} /></header><dl><div><dt>Machine</dt><dd>{machine.model}</dd></div><div><dt>Template</dt><dd>{templateFamilyLabel}</dd></div><div><dt>Required mappings</dt><dd>{metrics.reviewed} / {metrics.required} reviewed</dd></div><div><dt>Blocking setup issues</dt><dd>{setupBlockers}</dd></div><div><dt>Unsupported required mappings</dt><dd>{metrics.blocking}</dd></div></dl>{metrics.needsReview > 0 && !setupBlockers && <p className="variant-warning">Preview includes unreviewed mappings.</p>}{!familyCompatible && <div className="variant-warning"><strong>BLOCKING SETUP ISSUE</strong><p>Machine type: {draft.machine_type}. Selected template: {templateFamilyLabel}. Choose a compatible post template before continuing.</p><button onClick={() => navigate("/gpost")}>Change Template</button></div>}</section><div className="gpost-test-inputs"><section className="panel"><header><h3>CL / NCL Input</h3><label className="button secondary">Upload CL File<input aria-label="Upload CL File" type="file" accept=".cl,.ncl,.txt" onChange={(event) => { const file = event.target.files?.[0]; if (file) void file.text().then(setClSource); }} /></label></header><textarea aria-label="CL / NCL Input" rows={18} value={clSource} onChange={(event) => setClSource(event.target.value)} /></section><section className="panel"><header><h3>Generated G-code</h3><span>R&amp;D preview</span></header>{preview ? <GPostCodeViewer code={preview.generated_gcode} /> : <div className="gpost-test-placeholder"><span>⌁</span><strong>No preview generated</strong><p>Generate a preview after reviewing preflight.</p></div>}</section></div><div className="gpost-generate-bar"><p>Existing CL parser → template-referenced mappings → G-code parser → deterministic rules</p><button className="button primary" disabled={busy || !clSource.trim() || setupBlockers > 0} onClick={() => void generatePreview()}>{busy ? "Generating…" : "Generate Preview"}</button></div>{preview && <><nav className="gpost-result-tabs">{RESULT_TABS.map((tab) => <button key={tab} className={resultTab === tab ? "active" : ""} onClick={() => updateParams({ result: tab })}>{tab.replaceAll("-", " ")}</button>)}</nav><div className="gpost-test-results">{resultTab === "generated-code" && <GPostCodeViewer code={preview.generated_gcode} title="Generated Code" />}{resultTab === "cl-trace" && <div className="gpost-trace-table-layout"><table><thead><tr><th>CL Line</th><th>CL Command</th><th>Mapping</th><th>Template</th><th>Generated Block</th><th>Status</th></tr></thead><tbody>{preview.traceability_json.map((item, index) => <tr key={index} className={traceIndex === index ? "selected" : ""} onClick={() => setTraceIndex(index)}><td>{String(item.source_cl_line)}</td><td><code>{String(item.source_cl_text)}</code></td><td>{String(item.cl_command)} · #{String(item.mapping_id)}</td><td><code>{String(item.template_key ?? (item.uses_override ? "Override" : "State"))}</code></td><td><code>{String(item.generated_gcode)}</code></td><td>✓</td></tr>)}</tbody></table>{selectedTrace && <aside><h3>Trace rationale</h3><dl><div><dt>Mapping version</dt><dd>v{String(selectedTrace.mapping_version)}</dd></div><div><dt>Template source</dt><dd><code>{String(selectedTrace.uses_override ? "Mapping Override" : selectedTrace.template_key ?? "State behavior")}</code></dd></div><div><dt>Template</dt><dd><code>{String(selectedTrace.template_used ?? "State transition")}</code></dd></div><div><dt>State before</dt><dd><code>{JSON.stringify(selectedTrace.state_before)}</code></dd></div><div><dt>State after</dt><dd><code>{JSON.stringify(selectedTrace.state_after)}</code></dd></div></dl></aside>}</div>}{resultTab === "validation" && <ValidationSummary preview={preview} />}{resultTab === "warnings" && <div className="gpost-warning-list">{[...draft.warnings_json, ...preview.warnings_json, ...preview.unsupported_commands_json, ...preview.missing_mappings_json].map((item, index) => <article key={index}><strong>{String(item.category ?? item.command ?? "Warning")}</strong><p>{warningText(item)}</p></article>)}</div>}{resultTab === "reference-diff" && <ReferenceDifference programs={selectedReferences} preview={preview} />}</div></>}</section>}

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
    ["Generation", preview.status === "blocked" ? `Blocked — ${String(preview.summary_json.blocking_cause ?? "Review Required")}` : preview.warnings_json.length ? "Warning" : "Pass"],
    ["Parser", preview.parser_diagnostics_json.length ? "Warnings" : "Pass"],
    ["Machine Limits", limits.length ? "Findings" : "Pass"],
    ["Supported Commands", commands.length || preview.unsupported_commands_json.length ? "Findings" : "Pass"],
    ["Reference Comparison", "Not Run"],
  ];
  return <div className="gpost-validation-summary"><div className="gpost-validation-cards">{summary.map(([label, status]) => <article key={label}><span>{label}</span>{label === "Generation" && preview.status === "blocked" ? <strong>{status}</strong> : <GPostStatusBadge status={status.toLowerCase().replaceAll(" ", "_")} large />}</article>)}</div><section className="panel"><h2>Detailed Findings</h2>{!findings.length && !preview.parser_diagnostics_json.length ? <p>No parser or deterministic findings.</p> : <>{preview.parser_diagnostics_json.map((item) => <article className="gpost-finding" key={item}><GPostStatusBadge status="pending" /><div><strong>Parser diagnostic</strong><p>{item}</p></div></article>)}{findings.map((item, index) => <article className={`gpost-finding ${String(item.severity)}`} key={index}><GPostStatusBadge status={String(item.severity)} /><div><small>{String(item.category).toUpperCase()} · {String(item.rule_id)}</small><strong>{String(item.title)}</strong><p>{String(item.description)}</p>{item.line_number != null && <small>Line {String(item.line_number)}</small>}</div></article>)}</>}</section></div>;
}

function ReferenceDifference({ programs, preview }: { programs: ReferenceProgram[]; preview: GPostPreview }) {
  return <div className="gpost-reference-diff"><header><div><h2>Reference Difference</h2><p>Historical program evidence remains separate from deterministic validation.</p></div><GPostStatusBadge status={programs.length ? "pending" : "deferred"} /></header>{programs.length ? programs.map((program) => <article key={program.id}><strong>{program.name}</strong><span>Post revision {program.post_processor_revision || "unspecified"}</span><small>{String(program.validation_summary_json.blocking_count ?? 0)} historical blocking findings · comparison not automatically authoritative</small></article>) : <p>No approved reference program is selected for this draft.</p>}<p className="field-help">Preview #{preview.id} generated {String(preview.summary_json.generated_block_count)} mapped blocks. A structural reference comparison is not run automatically.</p></div>;
}
