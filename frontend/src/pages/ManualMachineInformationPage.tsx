import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { ManualMachineInformationField, MachineProfile, ProfileProposal, SourceDocument } from "../types";

const sourceOptions = [
  ["engineer_entry", "Engineer Entry"], ["installed_machine_configuration", "Installed Machine Configuration"],
  ["machine_nameplate", "Machine Nameplate"], ["machine_manual", "Machine Manual"],
  ["controller_manual", "Controller Manual"], ["site_standard", "Site Standard"],
  ["other_approved_source", "Other Approved Source"],
] as const;
const documentSources = new Set(["machine_manual", "controller_manual", "site_standard", "other_approved_source"]);

export function ManualMachineInformationPage() {
  const machineId = Number(useParams().machineId); const [params] = useSearchParams(); const navigate = useNavigate();
  const proposalId = Number(params.get("proposal")) || null; const runId = Number(params.get("run")) || null;
  const [machine, setMachine] = useState<MachineProfile | null>(null); const [fields, setFields] = useState<ManualMachineInformationField[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]); const [proposal, setProposal] = useState<ProfileProposal | null>(null);
  const [factKey, setFactKey] = useState(params.get("field") || ""); const [value, setValue] = useState(""); const [unit, setUnit] = useState("");
  const [sourceBasis, setSourceBasis] = useState("engineer_entry"); const [documentId, setDocumentId] = useState("");
  const [sourceDetail, setSourceDetail] = useState(""); const [notes, setNotes] = useState(""); const [status, setStatus] = useState("needs_review");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  useEffect(() => { void Promise.all([api.getProfile(machineId), api.listManualMachineInformationFields(machineId), api.listDocuments(machineId), proposalId ? api.getProfileProposal(proposalId) : Promise.resolve(null)])
    .then(([nextMachine, nextFields, nextDocuments, nextProposal]) => { setMachine(nextMachine); setFields(nextFields); setDocuments(nextDocuments); setProposal(nextProposal); if (nextProposal) { setFactKey(nextProposal.field_key); setUnit(nextProposal.unit || ""); } else if (!factKey && nextFields.length) setFactKey(nextFields[0].fact_key); })
    .catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load manual entry.")); }, [machineId, proposalId]);
  const field = useMemo(() => fields.find((item) => item.fact_key === factKey), [fields, factKey]);
  useEffect(() => { if (field && !field.units.includes(unit)) setUnit(field.units[0] || ""); }, [field?.fact_key]);
  const cancel = () => navigate(runId ? `/machines/${machineId}/profile-extraction/${runId}?v1=1` : `/machines/${machineId}/machine-knowledge`);
  async function save() {
    if (!field || !value.trim()) return; setBusy(true); setError("");
    try {
      const parsedValue = field.data_type === "list" ? value.split(",").map((item) => item.trim()).filter(Boolean) : value.trim();
      await api.saveManualMachineInformation(machineId, { fact_key: factKey, value: parsedValue, unit: unit || null, source_basis: sourceBasis,
        document_id: documentId ? Number(documentId) : null, source_detail: sourceDetail || null, notes: notes || null,
        review_status: status, proposal_id: proposalId });
      navigate(runId ? `/machines/${machineId}/profile-extraction/${runId}?v1=1&manualSaved=${encodeURIComponent(factKey)}` : `/machines/${machineId}/machine-knowledge?manualSaved=${encodeURIComponent(factKey)}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save Machine Information."); } finally { setBusy(false); }
  }
  return <section className="page manual-machine-information-page"><PageHeader eyebrow="Machine Information" title="Add Machine Information" description="Enter a machine/controller value manually when it is known from engineer review, installed-machine information, a nameplate, site documentation, or another approved source." />
    {machine && <p className="manual-entry-machine"><strong>{machine.name}</strong> · {machine.controller_model || machine.controller_name}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <section className="panel manual-information-form" aria-label="Add Machine Information form">
      <label>Category<input value={field?.category || ""} disabled /></label>
      <label>Information / Fact<select value={factKey} disabled={Boolean(proposal)} onChange={(event) => setFactKey(event.target.value)}><option value="">Select information</option>{fields.map((item) => <option key={item.fact_key} value={item.fact_key}>{item.label}</option>)}</select></label>
      {proposal && <p className="field-note">Resolving: <strong>{proposal.field_label}</strong></p>}
      <label>Value<input autoFocus={!proposal} value={value} inputMode={field?.data_type === "number" || field?.data_type === "integer" ? "decimal" : undefined} onChange={(event) => setValue(event.target.value)} /></label>
      <label>Unit<select value={unit} disabled={!field?.units.length} onChange={(event) => setUnit(event.target.value)}><option value="">No unit</option>{field?.units.map((item) => <option key={item} value={item}>{item === "inch" ? "in" : item}</option>)}</select></label>
      <label>Source / Basis<select value={sourceBasis} onChange={(event) => setSourceBasis(event.target.value)}>{sourceOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      {documentSources.has(sourceBasis) && <label>Document (optional)<select value={documentId} onChange={(event) => setDocumentId(event.target.value)}><option value="">No document selected</option>{documents.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}
      <label>Page / Section (optional)<input value={sourceDetail} onChange={(event) => setSourceDetail(event.target.value)} /></label>
      <label className="manual-entry-notes">Notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <label>Review Status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="needs_review">Needs Review</option><option value="confirmed">Confirmed</option></select></label>
      <footer><button className="button secondary" type="button" onClick={cancel}>Cancel</button><button className="button primary" type="button" disabled={busy || !field || !value.trim() || !sourceBasis} onClick={() => void save()}>{busy ? "Saving…" : "Save"}</button></footer>
    </section>
  </section>;
}
