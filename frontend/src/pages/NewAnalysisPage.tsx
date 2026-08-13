import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import {
  PROBLEMATIC_SAMPLE_GCODE,
  SAFE_SAMPLE_GCODE,
  SAMPLE_CL_DATA,
} from "../features/analysis/samples";
import type { MachineProfile } from "../types";

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [name, setName] = useState("");
  const [profileId, setProfileId] = useState("");
  const [clSource, setClSource] = useState("");
  const [gcodeSource, setGcodeSource] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [loadingProfiles, setLoadingProfiles] = useState(true);

  useEffect(() => {
    api.listProfiles().then((items) => {
      setProfiles(items);
      if (items[0]) setProfileId(String(items[0].id));
    }).catch((cause) => setError(cause.message)).finally(() => setLoadingProfiles(false));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setRunning(true);
    setError("");
    try {
      const project = await api.createProject({
        name,
        machine_profile_id: Number(profileId),
        cl_source: clSource,
        gcode_source: gcodeSource,
      });
      await api.runAnalysis(project.id);
      navigate(`/analysis/${project.id}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to run analysis.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="page">
      <PageHeader eyebrow="Advanced tool" title="G-code Review" description="Check existing G-code against the selected machine configuration." />
      <SafetyBanner />
      <form className="analysis-form" onSubmit={submit}>
        <div className="form-section">
          <div className="section-heading"><span>01</span><div><h2>Review setup</h2><p>Name this review and select the CNC machine.</p></div></div>
          <div className="form-grid two">
            <label>Review name<input aria-label="Analysis name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. OP20 housing review" /></label>
            <label>Machine<select aria-label="Machine profile" required value={profileId} onChange={(e) => setProfileId(e.target.value)}>
              {profiles.length === 0 && <option value="">{loadingProfiles ? "Loading machine profiles…" : "Create a machine profile first"}</option>}
              {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}
            </select></label>
          </div>
        </div>
        <div className="source-grid">
          <div className="source-panel">
            <div><span className="source-label">Optional source</span><h2>Creo CL / NCL data</h2><p>Paste cutter-location output for advisory explanation.</p><button type="button" className="sample-button" onClick={() => setClSource(SAMPLE_CL_DATA)}>Load fictional CL sample</button></div>
            <textarea aria-label="Creo CL or NCL data" value={clSource} onChange={(e) => setClSource(e.target.value)} placeholder="$$ Creo CL/NCL source…" spellCheck={false} />
          </div>
          <div className="source-panel">
            <div><span className="source-label required">Required</span><h2>Post-processed G-code</h2><p>Paste the exact program to validate.</p><div className="sample-actions"><button type="button" className="sample-button" onClick={() => setGcodeSource(SAFE_SAMPLE_GCODE)}>Load safe-style sample</button><button type="button" className="sample-button problematic" onClick={() => setGcodeSource(PROBLEMATIC_SAMPLE_GCODE)}>Load problematic sample</button></div></div>
            <textarea aria-label="Post-processed G-code" required value={gcodeSource} onChange={(e) => setGcodeSource(e.target.value)} placeholder="%&#10;O1001&#10;G17 G40 G49 G80 G90…" spellCheck={false} />
          </div>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="analysis-submit">
          <p>Analysis uses deterministic Python rules. Advisory AI cannot change rule results.</p>
          <button aria-label="Run deterministic analysis" className="button primary large" disabled={running || loadingProfiles || !profiles.length || !name.trim() || !gcodeSource.trim()}>{running ? "Reviewing G-code…" : "Review G-code →"}</button>
        </div>
      </form>
    </section>
  );
}
