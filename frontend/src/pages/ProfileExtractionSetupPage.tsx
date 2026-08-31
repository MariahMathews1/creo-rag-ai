import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { MachineProfile, SourceDocument } from "../types";

const categories = ["identity","controller","axis_limits","spindle","feed_and_motion","tooling","programming","capabilities"];
const additionalCategories = ["workholding", "machine_geometry", "safety_and_setup"];
const categoryLabels: Record<string, string> = { identity: "Identity", controller: "Controller", axis_limits: "Axes / Kinematics", spindle: "Spindle", feed_and_motion: "Feed / Motion", tooling: "Tooling", programming: "Programming / Codes", capabilities: "Cycles / Capabilities", workholding: "Workholding", machine_geometry: "Physical Capacity", safety_and_setup: "General Setup / Safety" };

export function ProfileExtractionSetupPage() {
  const { machineId } = useParams(); const id = Number(machineId);
  const navigate = useNavigate();
  const [machine, setMachine] = useState<MachineProfile | null>(null);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [selectedCategories, setSelectedCategories] = useState(categories);
  const [typeFilter, setTypeFilter] = useState("all");
  const [targetType, setTargetType] = useState("other");
  const [variant, setVariant] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([api.listProfiles(), api.listDocuments(id)]).then(([machines, docs]) => {
      const selectedMachine = machines.find((item) => item.id === id) ?? null;
      setMachine(selectedMachine); setTargetType(selectedMachine?.machine_type ?? "other");
      setDocuments(docs);
    }).catch((cause) => setError(cause.message));
  }, [id]);
  const visible = useMemo(() => documents.filter((item) => typeFilter === "all" || item.document_type === typeFilter), [documents, typeFilter]);
  async function start() {
    setBusy(true); setError("");
    try {
      const run = await api.startProfileExtraction(id, {
        document_ids: selected, target_machine_type: targetType,
        selected_machine_variant: variant.trim() || null, field_categories: selectedCategories,
      });
      navigate(`/machines/${id}/profile-extraction/${run.id}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Extraction failed"); }
    finally { setBusy(false); }
  }
  return <section className="page">
    <PageHeader eyebrow="Machine information" title="Extract Machine Information" description={`${machine?.name ?? "Machine"} · choose the machine documents to review`} />
    <aside className="safety-banner" role="alert"><span className="safety-icon">!</span><div><strong>Draft proposals only</strong><p>Extracted values require review against the exact machine, controller version, installed options, and controlled documentation.</p></div></aside>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="extraction-setup-grid">
      <section className="panel"><header><div><span className="eyebrow">Step 1</span><h2>Select documents</h2></div><label>Type<select aria-label="Document type filter" value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}><option value="all">All types</option>{Array.from(new Set(documents.map((item) => item.document_type))).map((value) => <option key={value}>{value}</option>)}</select></label></header>
        <div className="document-choice-list">{visible.map((document) => <label key={document.id} className={document.processing_status !== "ready" ? "disabled" : ""}><input type="checkbox" disabled={document.processing_status !== "ready"} checked={selected.includes(document.id)} onChange={() => setSelected((current) => current.includes(document.id) ? current.filter((value) => value !== document.id) : [...current, document.id])} /><div><strong>{document.title}</strong><small>{document.document_type.replaceAll("_", " ")} · {document.original_filename} · {document.page_count ?? "—"} pages</small><span>{document.processing_status}</span></div></label>)}</div>
      </section>
      <section className="panel"><header><div><span className="eyebrow">Step 2</span><h2>Target and fields</h2></div></header><div className="panel-body"><label>Target machine type<select aria-label="Target machine type" value={targetType} onChange={(event) => setTargetType(event.target.value)}><option value="mill">Mill</option><option value="lathe">Lathe</option><option value="mill-turn">Mill-turn</option><option value="turning_center">Turning center</option><option value="machining_center">Machining center</option><option value="vertical_mill">Vertical mill</option><option value="horizontal_mill">Horizontal mill</option><option value="vertical_lathe">Vertical lathe</option><option value="other">Other</option></select></label><label>Known exact variant (optional)<input aria-label="Known exact variant" value={variant} onChange={(event) => setVariant(event.target.value)} placeholder="For example LT-200" /></label></div><div className="category-choice-list">{categories.map((category) => <label key={category}><input type="checkbox" checked={selectedCategories.includes(category)} onChange={() => setSelectedCategories((current) => current.includes(category) ? current.filter((value) => value !== category) : [...current, category])} />{categoryLabels[category]}</label>)}</div><details className="additional-machine-information"><summary>Additional Machine Information</summary><div className="category-choice-list">{additionalCategories.map((category) => <label key={category}><input type="checkbox" checked={selectedCategories.includes(category)} onChange={() => setSelectedCategories((current) => current.includes(category) ? current.filter((value) => value !== category) : [...current, category])} />{categoryLabels[category]}</label>)}</div></details><div className="panel-body"><p className="field-note">Multiple models or variants will be flagged before variant-dependent proposals can be accepted.</p><button className="button primary large" disabled={busy || !selected.length || !selectedCategories.length} onClick={() => void start()}>{busy ? "Extracting synchronously…" : "Start extraction"}</button></div></section>
    </div>
  </section>;
}
