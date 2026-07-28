import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { MachineProfileRevision } from "../types";

export function ProfileRevisionsPage() {
  const { machineId } = useParams(); const id = Number(machineId);
  const [revisions, setRevisions] = useState<MachineProfileRevision[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.listProfileRevisions(id).then(setRevisions).catch((cause) => setError(cause.message)); }, [id]);
  return <section className="page"><PageHeader eyebrow="Auditable configuration" title="Machine profile revisions" description="Approved, superseded, draft, and rejected revisions remain accessible." action={<Link className="button primary" to={`/machines/${id}/profile-extraction/new`}>Extract new draft</Link>} />{error && <p role="alert" className="form-error">{error}</p>}<div className="revision-list">{revisions.map((revision) => <article key={revision.id}><span className={`document-status ${revision.status === "approved" ? "ready" : revision.status === "rejected" ? "failed" : "processing"}`}>{revision.status}</span><h2>Revision v{revision.revision_number}</h2><p>{revision.manufacturer} {revision.model} · {revision.controller_name}</p><small>{revision.source_type} · {revision.review_summary ?? "No review summary"}</small></article>)}</div>{!revisions.length && !error && <div className="empty-state"><h2>No revisions</h2><p>An initial revision is created when this view opens.</p></div>}</section>;
}
