import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SafetyBanner } from "../components/SafetyBanner";
import { SeverityBadge } from "../components/SeverityBadge";
import type { AnalysisFinding, AnalysisProject, MachineProfile, Severity } from "../types";

const severities: Severity[] = ["blocking", "warning", "informational"];

export function AnalysisResultsPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const [project, setProject] = useState<AnalysisProject | null>(null);
  const [machine, setMachine] = useState<MachineProfile | null>(null);
  const [findings, setFindings] = useState<AnalysisFinding[]>([]);
  const [selected, setSelected] = useState<Set<Severity>>(new Set(severities));
  const [category, setCategory] = useState("all");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const [selectedFindingId, setSelectedFindingId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.getProject(id), api.getFindings(id), api.listProfiles()])
      .then(([projectData, findingData, profiles]) => {
        setProject(projectData);
        setFindings(findingData);
        setMachine(
          profiles.find((profile) => profile.id === projectData.machine_profile_id) ?? null,
        );
      })
      .catch((cause) => setError(cause.message));
    api.explain(id, "findings").then((value) => setSummary(value.explanation)).catch(() => {});
  }, [id]);

  const counts = Object.fromEntries(severities.map((severity) => [severity, findings.filter((item) => item.severity === severity).length])) as Record<Severity, number>;
  const categories = Array.from(new Set(findings.map((item) => item.category)));
  const visible = findings.filter((item) => selected.has(item.severity) && (category === "all" || item.category === category));
  const selectedFinding = findings.find((item) => item.id === selectedFindingId);
  const byLine = useMemo(() => {
    const map = new Map<number, AnalysisFinding[]>();
    findings.forEach((finding) => {
      if (finding.line_number) map.set(finding.line_number, [...(map.get(finding.line_number) ?? []), finding]);
    });
    return map;
  }, [findings]);

  const toggle = (severity: Severity) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(severity)) next.delete(severity); else next.add(severity);
      return next;
    });

  function selectFinding(finding: AnalysisFinding) {
    setSelectedFindingId(finding.id);
    if (finding.line_number) {
      window.requestAnimationFrame(() => {
        document
          .getElementById(`line-${finding.line_number}`)
          ?.scrollIntoView?.({ behavior: "smooth", block: "center" });
      });
    }
  }

  const statusLabel = {
    draft: "Not yet run",
    passed: "No configured rule violations detected",
    review_required: "Manual review required",
    blocked: "Blocking issues detected",
  }[project?.status ?? "draft"];

  if (error) return <section className="page"><p className="form-error" role="alert">{error}</p></section>;
  if (!project) return <section className="page"><p className="loading">Loading analysis…</p></section>;

  return (
    <section className="page results-page">
      <PageHeader
        eyebrow={`Analysis #${project.id}`}
        title={project.name}
        description={`${machine?.name ?? "Machine profile unavailable"} · ${statusLabel} · Reviewed ${new Date(project.updated_at).toLocaleString()}`}
        action={<div className="header-actions"><Link className="button secondary" to={`/analyses/${project.id}/traceability`}>Open traceability</Link><Link className="button secondary" to="/analysis/new">New analysis</Link></div>}
      />
      <SafetyBanner />
      <div className="result-metrics">
        <div className="overall-card"><small>Overall review status</small><strong>{statusLabel}</strong><span className={project.status === "blocked" ? "indicator red" : project.status === "review_required" ? "indicator amber" : "indicator green"} /></div>
        {severities.map((severity) => <div className={`metric metric-${severity}`} key={severity}><span>{counts[severity]}</span><div><strong>{severity}</strong><small>findings</small></div></div>)}
      </div>
      <div className="advisory-card">
        <span>AI</span><div><strong>Advisory mock summary</strong><p>{summary || "Preparing local advisory summary…"}</p></div>
      </div>
      <div className="results-toolbar">
        <div className="filter-group" aria-label="Severity filters">
          {severities.map((severity) => <button className={selected.has(severity) ? "selected" : ""} key={severity} onClick={() => toggle(severity)}><i className={`dot ${severity}`} />{severity} <b>{counts[severity]}</b></button>)}
        </div>
        <label>Category<select aria-label="Finding category" value={category} onChange={(e) => setCategory(e.target.value)}><option value="all">All categories</option>{categories.map((item) => <option key={item}>{item}</option>)}</select></label>
      </div>
      <div className="manual-context-action">
        <div><strong>Manual-Based Explanation</strong><p>{selectedFinding ? `Retrieve documentation for: ${selectedFinding.title}` : "Select a deterministic finding, then retrieve relevant machine documentation."}</p></div>
        <Link
          className="button secondary"
          aria-disabled={!selectedFinding}
          to={selectedFinding ? `/manual-assistant?machine=${project.machine_profile_id}&question=${encodeURIComponent(`What do the uploaded manuals state about ${selectedFinding.rule_id} and this line: ${selectedFinding.source_line ?? ""}?`)}` : "#"}
        >Explain using machine manuals →</Link>
      </div>
      <div className="results-grid">
        <section className="code-viewer" aria-label="Original G-code">
          <header><div><span className="file-dot" />Program source</div><small>{project.gcode_source?.split("\n").length ?? 0} lines</small></header>
          <ol>
            {(project.gcode_source ?? "").split("\n").map((line, index) => {
              const lineFindings = byLine.get(index + 1) ?? [];
              const selectedOnLine = lineFindings.some((finding) => finding.id === selectedFindingId);
              const className = selectedOnLine
                ? "line-selected"
                : lineFindings.some((finding) => finding.severity === "blocking")
                  ? "line-blocking"
                  : lineFindings.length
                    ? "line-flagged"
                    : "";
              return <li id={`line-${index + 1}`} className={className} key={index}><code>{line || " "}</code>{lineFindings.length > 0 && <span className="line-count">{lineFindings.length}</span>}</li>;
            })}
          </ol>
        </section>
        <section className="finding-panel" aria-label="Validation findings">
          <header><strong>Validation findings</strong><small>{visible.length} shown</small></header>
          <div className="finding-list">
            {visible.length === 0 && <div className="no-findings">No findings match the selected filters.</div>}
            {severities.map((severity) => {
              const severityFindings = visible.filter((finding) => finding.severity === severity);
              if (!severityFindings.length) return null;
              return <section className="finding-group" key={severity} aria-label={`${severity} findings`}>
                <h3><span aria-hidden="true">{severity === "blocking" ? "✕" : severity === "warning" ? "▲" : "●"}</span>{severity} <small>{severityFindings.length}</small></h3>
                {severityFindings.map((finding) => (
                  <button
                    type="button"
                    aria-pressed={selectedFindingId === finding.id}
                    className={`finding finding-${finding.severity} ${selectedFindingId === finding.id ? "finding-selected" : ""}`}
                    key={finding.id}
                    onClick={() => selectFinding(finding)}
                  >
                    <div className="finding-top"><SeverityBadge severity={finding.severity} /><code>{finding.rule_id}</code>{finding.line_number && <span className="line-link">Line {finding.line_number}</span>}</div>
                    <h4>{finding.title}</h4>
                    <p>{finding.description}</p>
                    {finding.source_line && <pre>{finding.source_line}</pre>}
                    <div className="recommendation"><strong>Review action</strong><p>{finding.recommendation}</p></div>
                  </button>
                ))}
              </section>;
            })}
          </div>
        </section>
      </div>
    </section>
  );
}
