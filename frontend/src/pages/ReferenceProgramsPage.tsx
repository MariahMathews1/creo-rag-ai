import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type {
  MachineProfileRevision, ReferenceProgram, StandardExtractionRun,
  StandardProfile,
} from "../types";

const PROGRAM_TYPES = [
  "turning", "milling", "drilling", "threading", "boring", "facing",
  "grooving", "parting", "mill_turn", "setup", "test", "other",
];

export function ReferenceProgramsPage() {
  const machineId = Number(useParams().machineId);
  const [programs, setPrograms] = useState<ReferenceProgram[]>([]);
  const [revisions, setRevisions] = useState<MachineProfileRevision[]>([]);
  const [runs, setRuns] = useState<StandardExtractionRun[]>([]);
  const [standards, setStandards] = useState<StandardProfile[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [showImport, setShowImport] = useState(false);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [form, setForm] = useState({
    name: "", source_text: "", original_filename: "reference.nc",
    machine_profile_revision_id: 0, program_type: "turning",
    controller_name: "", controller_version: "", post_processor_name: "",
    post_processor_revision: "", part_identifier: "",
    approval_status: "unreviewed", ai_processing_allowed: false,
  });

  async function load() {
    try {
      const [programData, revisionData, runData, standardData] = await Promise.all([
        api.listReferencePrograms(machineId), api.listProfileRevisions(machineId),
        api.listStandardExtractions(machineId), api.listStandards(machineId),
      ]);
      setPrograms(programData); setRevisions(revisionData);
      setRuns(runData); setStandards(standardData);
      if (!form.machine_profile_revision_id && revisionData.length) {
        const approved = revisionData.find((item) => item.status === "approved");
        setForm((current) => ({
          ...current,
          machine_profile_revision_id: (approved ?? revisionData[0]).id,
          controller_name: (approved ?? revisionData[0]).controller_name ?? "",
          controller_version: (approved ?? revisionData[0]).controller_version ?? "",
        }));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load reference programs");
    }
  }
  useEffect(() => { void load(); }, [machineId]);

  async function importProgram(event: FormEvent) {
    event.preventDefault(); setError(""); setNotice("");
    try {
      await api.createReferenceProgram(machineId, form);
      setShowImport(false);
      setForm((current) => ({ ...current, name: "", source_text: "" }));
      setNotice("Reference imported as unreviewed and ineligible by default.");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Import failed");
    }
  }

  async function act(program: ReferenceProgram, action: "parse" | "eligible" | "ineligible") {
    setBusy(program.id); setError(""); setNotice("");
    try {
      if (action === "parse") await api.parseReferenceProgram(program.id);
      else if (action === "eligible") {
        await api.markReferenceEligible(
          program.id,
          "Explicitly reviewed for organizational-pattern analysis.",
        );
      } else {
        await api.markReferenceIneligible(
          program.id,
          "Explicitly excluded from organizational-pattern analysis.",
        );
      }
      setNotice(`${program.name}: ${action} action recorded.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  const selectedPrograms = useMemo(
    () => programs.filter((item) => selected.has(item.id)),
    [programs, selected],
  );
  const incompatible = new Set(selectedPrograms.map(
    (item) => `${item.machine_profile_revision_id}|${item.post_processor_revision ?? "unspecified"}|${item.controller_version ?? "unspecified"}`,
  )).size > 1;

  async function extract() {
    if (!selectedPrograms.length) return;
    setError(""); setNotice("");
    try {
      const first = selectedPrograms[0];
      const run = await api.startStandardExtraction(machineId, {
        machine_profile_revision_id: first.machine_profile_revision_id,
        reference_program_ids: selectedPrograms.map((item) => item.id),
        post_processor_revision: first.post_processor_revision ?? undefined,
      });
      setNotice(`Standard extraction #${run.id} created. Frequency remains evidence, not authority.`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Standard extraction failed");
    }
  }

  return <section className="page phase6-page">
    <PageHeader
      eyebrow="Phase 6 · Historical evidence"
      title="Approved-program library"
      description="Associate externally reviewed programs with an exact machine revision, then explicitly control whether they may inform organizational patterns."
      action={<button className="button primary" onClick={() => setShowImport(true)}>
        + Import reference program
      </button>}
    />
    <SafetyBanner
      title="Historical similarity is not certification"
      message="Previously reviewed programs are evidence of prior practice only. Qualified review and simulation remain required."
    />
    {error && <p className="form-error" role="alert">{error}</p>}
    {notice && <p className="success-message" role="status">{notice}</p>}

    {showImport && <form className="panel phase6-import-form" onSubmit={importProgram}>
      <header><div><span className="eyebrow">Source integrity</span><h2>Import reference program</h2></div>
        <button type="button" aria-label="Close import" onClick={() => setShowImport(false)}>×</button>
      </header>
      <div className="form-grid">
        <label>Name<input required value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label>Machine revision<select required value={form.machine_profile_revision_id}
          onChange={(e) => setForm({ ...form, machine_profile_revision_id: Number(e.target.value) })}>
          <option value={0}>Select revision</option>
          {revisions.map((item) => <option key={item.id} value={item.id}>
            v{item.revision_number} · {item.status} · {item.model}
          </option>)}
        </select></label>
        <label>Program type<select value={form.program_type}
          onChange={(e) => setForm({ ...form, program_type: e.target.value })}>
          {PROGRAM_TYPES.map((item) => <option key={item}>{item}</option>)}
        </select></label>
        <label>Approval status<select value={form.approval_status}
          onChange={(e) => setForm({ ...form, approval_status: e.target.value })}>
          <option value="unreviewed">Unreviewed</option>
          <option value="externally_reviewed">Externally reviewed</option>
          <option value="approved_reference">Approved reference</option>
          <option value="unknown">Unknown</option>
        </select></label>
        <label>Controller<input value={form.controller_name}
          onChange={(e) => setForm({ ...form, controller_name: e.target.value })} /></label>
        <label>Controller version<input value={form.controller_version}
          onChange={(e) => setForm({ ...form, controller_version: e.target.value })} /></label>
        <label>Post processor<input value={form.post_processor_name}
          onChange={(e) => setForm({ ...form, post_processor_name: e.target.value })} /></label>
        <label>Post revision<input value={form.post_processor_revision}
          onChange={(e) => setForm({ ...form, post_processor_revision: e.target.value })} /></label>
        <label>Part/project identifier<input value={form.part_identifier}
          onChange={(e) => setForm({ ...form, part_identifier: e.target.value })} /></label>
        <label>Program file<input type="file" accept=".nc,.tap,.gcode,.cnc,.txt,.mpf"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            file.text().then((text) => setForm((current) => ({
              ...current, source_text: text, original_filename: file.name,
              name: current.name || file.name,
            })));
          }} /></label>
      </div>
      <label>Or paste G-code<textarea required rows={12} value={form.source_text}
        onChange={(e) => setForm({ ...form, source_text: e.target.value })} /></label>
      <label className="checkbox-label"><input type="checkbox"
        checked={form.ai_processing_allowed}
        onChange={(e) => setForm({ ...form, ai_processing_allowed: e.target.checked })} />
        External AI processing permitted for this program (off by default)
      </label>
      <p className="field-help">Import does not mark this program eligible or approved. It is parsed as text and never executed.</p>
      <button className="button primary">Import as ineligible pending review</button>
    </form>}

    <section className="panel phase6-dataset">
      <header><div><span className="eyebrow">Governed dataset</span><h2>Reference programs</h2></div>
        <div><strong>{programs.filter((item) => item.eligibility_status === "eligible").length}</strong> eligible · {programs.length} total</div>
      </header>
      {programs.length === 0 ? <p>No reference programs have been imported.</p> :
        <div className="reference-program-table-wrap"><table className="reference-program-table">
          <thead><tr><th>Select</th><th>Program</th><th>Applicability</th><th>Integrity and validation</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>{programs.map((program) => <tr key={program.id}>
            <td><input aria-label={`Select ${program.name}`} type="checkbox"
              disabled={program.eligibility_status !== "eligible"}
              checked={selected.has(program.id)}
              onChange={() => setSelected((items) => {
                const next = new Set(items);
                if (next.has(program.id)) next.delete(program.id); else next.add(program.id);
                return next;
              })} /></td>
            <td><strong>{program.name}</strong><small>{program.program_type} · {program.part_identifier || "No part ID"}</small></td>
            <td><span>Machine rev {program.machine_profile_revision_id}</span>
              <small>{program.controller_name || "Controller unspecified"} {program.controller_version || ""}</small>
              <small>Post {program.post_processor_revision || "unspecified"}</small></td>
            <td><code>{program.file_hash.slice(0, 12)}…</code>
              <small>{program.parsing_status} · {String(program.validation_summary_json.blocking_count ?? 0)} blocking</small>
              {!program.ai_processing_allowed && <small>Restricted from external AI</small>}</td>
            <td><span className={`strong-status ${program.approval_status}`}>{program.approval_status.replaceAll("_", " ")}</span>
              <span className={`strong-status ${program.eligibility_status}`}>{program.eligibility_status.replaceAll("_", " ")}</span>
              {program.eligibility_reason && <small>{program.eligibility_reason}</small>}</td>
            <td><button disabled={busy === program.id} onClick={() => void act(program, "parse")}>Parse + validate</button>
              <button disabled={busy === program.id || !program.parsing_status.startsWith("parsed")}
                onClick={() => void act(program, "eligible")}>Mark eligible</button>
              <button disabled={busy === program.id}
                onClick={() => void act(program, "ineligible")}>Mark ineligible</button></td>
          </tr>)}</tbody>
        </table></div>}
    </section>

    <section className="panel standard-extraction-launcher">
      <header><div><span className="eyebrow">Deterministic preprocessing</span><h2>Extract programming conventions</h2></div>
        <button className="button primary" disabled={!selected.size || incompatible}
          onClick={() => void extract()}>Extract from {selected.size} eligible programs</button>
      </header>
      {incompatible && <p className="form-error">Selected programs have different machine or post-revision applicability. Split the dataset before extraction.</p>}
      <p>Programs must be explicitly eligible and scope-compatible. Recurrence proposes review work; it does not create a requirement.</p>
      <div className="run-links">{runs.map((run) => <Link key={run.id}
        to={`/machines/${machineId}/standards/extraction/${run.id}`}>
        Extraction #{run.id} · {String(run.summary_json.proposal_count ?? 0)} proposals · {run.status}
      </Link>)}</div>
    </section>

    <section className="panel">
      <header><div><span className="eyebrow">Versioned governance</span><h2>Programming standards</h2></div></header>
      <div className="standard-card-grid">{standards.map((standard) => <article key={standard.id}>
        <strong>{standard.name} · v{standard.revision_number}</strong>
        <span className={`strong-status ${standard.status}`}>{standard.status}</span>
        <p>{standard.conventions.length} accepted conventions · machine revision {standard.machine_profile_revision_id}</p>
        {standard.stale && <p className="form-error">Stale: {standard.stale_reasons_json.join(", ")}</p>}
        <a href={api.standardReportUrl(standard.id)}>Export report</a>
      </article>)}</div>
    </section>
  </section>;
}
