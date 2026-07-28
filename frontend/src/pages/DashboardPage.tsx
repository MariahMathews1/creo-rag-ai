import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import type { AnalysisFinding, AnalysisProject, MachineProfile, Severity } from "../types";

export function DashboardPage() {
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [projects, setProjects] = useState<AnalysisProject[]>([]);
  const [findings, setFindings] = useState<AnalysisFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.listProfiles(), api.listProjects()])
      .then(async ([profileData, projectData]) => {
        setProfiles(profileData);
        setProjects(projectData);
        const all = await Promise.all(
          projectData.map((project) => api.getFindings(project.id)),
        );
        setFindings(all.flat());
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
        eyebrow="Review workspace"
        title="Program assurance dashboard"
        description="A single view of configured machines, active reviews, and unresolved validation signals."
        action={<Link to="/analysis/new" className="button primary">+ Start analysis</Link>}
      />
      <SafetyBanner />
      {loading && <p className="loading" role="status">Loading dashboard…</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="dashboard-stats">
        <div><small>Machine profiles</small><strong>{profiles.length}</strong><Link to="/machines">Manage profiles →</Link></div>
        <div><small>Analysis projects</small><strong>{projects.length}</strong><span>All local reviews</span></div>
        <div className="blocking-stat"><small>Blocking findings</small><strong>{count("blocking")}</strong><span>Require immediate review</span></div>
        <div><small>Warnings</small><strong>{count("warning")}</strong><span>Need qualified review</span></div>
      </div>
      <div className="dashboard-grid">
        <section className="panel recent-panel">
          <header><div><span className="eyebrow">Review queue</span><h2>Recent projects</h2></div><Link to="/analysis/new">New review</Link></header>
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
