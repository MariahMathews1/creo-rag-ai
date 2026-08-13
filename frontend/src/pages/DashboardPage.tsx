import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type { AnalysisFinding, AnalysisProject, GPostDraft, MachineProfile, Severity, SourceDocument, TranslationDatasetSummary } from "../types";

export function DashboardPage() {
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [projects, setProjects] = useState<AnalysisProject[]>([]);
  const [findings, setFindings] = useState<AnalysisFinding[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [translationSummary, setTranslationSummary] = useState<TranslationDatasetSummary | null>(null);
  const [drafts, setDrafts] = useState<GPostDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.listProfiles(), api.listProjects()])
      .then(async ([profileData, projectData]) => {
        setProfiles(profileData); setProjects(projectData);
        const [allFindings, allDocuments, allDrafts, translations] = await Promise.all([
          Promise.all(projectData.map((project) => api.getFindings(project.id))),
          Promise.all(profileData.map((profile) => api.listDocuments(profile.id))),
          Promise.all(profileData.map((profile) => api.listGPostDrafts(profile.id))),
          api.getTranslationSummary(),
        ]);
        setFindings(allFindings.flat()); setDocuments(allDocuments.flat()); setDrafts(allDrafts.flat()); setTranslationSummary(translations);
      })
      .catch((cause) =>
        setError(
          cause instanceof Error ? cause.message : "Unable to load dashboard data.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const count = (severity: Severity) => findings.filter((item) => item.severity === severity).length;
  return (
    <section className="page">
      <PageHeader
        eyebrow="NC programmer workspace"
        title="Dashboard"
        description="Start with a machine, add its references and known translation examples, then generate or review R&D G-code."
        action={<Link to="/gpost" className="button primary">Generate G-POST Draft</Link>}
      />
      <SafetyBanner />
      {loading && <p className="loading" role="status">Loading dashboard…</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="dashboard-stats">
        <div><small>Machines</small><strong>{profiles.length}</strong><Link to="/machines">View machines →</Link></div>
        <div><small>Documents</small><strong>{documents.length}</strong><Link to="/documents">View documents →</Link></div>
        <div><small>Verified Translation Examples</small><strong>{translationSummary?.verified ?? 0}</strong><Link to="/translations">View examples →</Link></div>
        <div><small>G-POST Drafts</small><strong>{drafts.length}</strong><Link to="/gpost">View drafts →</Link></div>
        <div><small>Recent G-code Reviews</small><strong>{projects.length}</strong><Link to="/g-code-review">Start review →</Link></div>
        <div className="blocking-stat"><small>Open Blocking Findings</small><strong>{count("blocking")}</strong><span>Require review</span></div>
      </div>
      <section className="dashboard-actions panel" aria-label="Quick actions"><h2>Quick Actions</h2><div><Link className="button secondary" to="/machines">+ Add Machine</Link><Link className="button secondary" to="/documents">Upload Documents</Link><Link className="button secondary" to="/translations">Add Translation Pair</Link><Link className="button secondary" to="/g-code-review">Review Existing G-code</Link></div></section>
      <div className="dashboard-grid">
        <section className="panel recent-panel">
          <header><div><span className="eyebrow">Recent activity</span><h2>Recent G-code Reviews</h2></div><Link to="/g-code-review">New review</Link></header>
          {projects.length === 0 ? <div className="compact-empty"><p>No analyses have been run.</p><Link to="/analysis/new">Start the first review →</Link></div> :
            projects.slice(0, 6).map((project) => <Link className="project-row" to={`/analysis/${project.id}`} key={project.id}><span className={`project-status ${project.status}`} /><div><strong>{project.name}</strong><small>{new Date(project.updated_at).toLocaleDateString()} · {project.status.replaceAll("_", " ")}</small></div><span>→</span></Link>)}
        </section>
        <section className="panel distribution-panel">
          <header><div><span className="eyebrow">All projects</span><h2>Finding distribution</h2></div></header>
          {(["blocking", "warning", "informational"] as Severity[]).map((severity) => {
            const value = count(severity);
            const percent = findings.length ? (value / findings.length) * 100 : 0;
            return <div className="distribution-row" key={severity}><div><span className={`dot ${severity}`} />{severity}<strong>{value}</strong></div><div className="bar"><i className={severity} style={{ width: `${percent}%` }} /></div></div>;
          })}
          <p className="rule-note"><strong>Deterministic first.</strong> Findings come from configured rules. AI explanations are always labeled advisory and never change results.</p>
        </section>
      </div>
    </section>
  );
}
