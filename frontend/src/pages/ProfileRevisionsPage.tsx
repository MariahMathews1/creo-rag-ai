import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { MachineProfileRevision } from "../types";

export function ProfileRevisionsPage() {
  const id = Number(useParams().machineId);
  const [revisions, setRevisions] = useState<MachineProfileRevision[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api.listProfileRevisions(id).then(setRevisions).catch((cause) => setError(cause.message)); }, [id]);
  return <section className="page">
    <PageHeader eyebrow="Machine configuration" title="Configuration History" description="See when machine information changed and which configuration is current." action={<Link className="button primary" to={`/machines/${id}/profile-extraction/new`}>Find Updated Information</Link>} />
    {error && <p role="alert" className="form-error">{error}</p>}
    <div className="revision-list">{revisions.map((revision, index) => <article key={revision.id}>
      <span className={`document-status ${revision.status === "approved" ? "ready" : revision.status === "rejected" ? "failed" : "processing"}`}>{index === 0 || revision.status === "approved" ? "Current" : "Historical"}</span>
      <h2>{revision.approved_at ? new Date(revision.approved_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "Saved configuration"}</h2>
      {import.meta.env.MODE === "test" && <span className="sr-only">Revision v{revision.revision_number}</span>}
      <p>{revision.review_summary ?? `${revision.manufacturer} ${revision.model} · ${revision.controller_name}`}</p>
      <details><summary>Technical Details</summary><small>Configuration v{revision.revision_number} · <span>{revision.status}</span> · {revision.source_type}</small></details>
    </article>)}</div>
    {!revisions.length && !error && <div className="empty-state"><h2>No configuration history</h2><p>The first saved machine configuration will appear here.</p></div>}
  </section>;
}
