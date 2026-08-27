import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { GPostDraft, MachineProfile, PostRecordSummary, SourceDocument } from "../types";

export function DashboardPage() {
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [posts, setPosts] = useState<GPostDraft[]>([]);
  const [summaries, setSummaries] = useState<PostRecordSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listProfiles().then(async (machineRows) => {
      setProfiles(machineRows);
      const [documentGroups, postGroups] = await Promise.all([
        Promise.all(machineRows.map((machine) => api.listDocuments(machine.id))),
        Promise.all(machineRows.map((machine) => api.listGPostDrafts(machine.id))),
      ]);
      const currentPosts = postGroups.flat().filter((post) => post.status !== "superseded");
      setDocuments(documentGroups.flat());
      setPosts(currentPosts);
      setSummaries(await Promise.all(currentPosts.map((post) => api.getPostRecordSummary(post.id))));
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load dashboard data."))
      .finally(() => setLoading(false));
  }, []);

  const needsAttention = summaries.filter((summary) => summary.blockers.length > 0 || summary.open_questions.open > 0).length;
  const activePosts = posts.filter((post) => post.status !== "archived");

  return <section className="page">
    <PageHeader eyebrow="NC programmer workspace" title="Dashboard" description="Continue machine setup, source review, and post development." action={<Link to="/gpost" className="button primary">Open Post Builder</Link>} />
    {loading && <p className="loading" role="status">Loading dashboard…</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="dashboard-stats">
      <div><small>Machines</small><strong>{profiles.length}</strong><Link to="/machines">View machines →</Link></div>
      <div><small>Posts in Development</small><strong>{activePosts.length}</strong><Link to="/gpost">Continue work →</Link></div>
      <div><small>Needs Attention</small><strong>{needsAttention}</strong><Link to="/gpost">Resolve issues →</Link></div>
      <div><small>Documents</small><strong>{documents.length}</strong><Link to="/documents">View documents →</Link></div>
    </div>
    <section className="dashboard-actions panel" aria-label="Quick actions"><h2>Quick Actions</h2><div>
      <Link className="button secondary" to="/machines">Add Machine</Link>
      <Link className="button secondary" to="/documents">Upload Documents</Link>
      <Link className="button secondary" to="/gpost">Create Post</Link>
    </div></section>
    <section className="panel recent-panel">
      <header><div><span className="eyebrow">Recent work</span><h2>Recent Post Work</h2></div><Link to="/gpost">All Posts</Link></header>
      {activePosts.length === 0 ? <div className="compact-empty"><p>No posts are in development.</p><Link to="/gpost">Create the first post →</Link></div> : activePosts.sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 6).map((post) => {
        const machine = profiles.find((item) => item.id === post.machine_profile_id);
        const summary = summaries.find((item) => item.post_record_id === post.id);
        return <Link className="project-row" to={`/gpost/${post.id}`} key={post.id}><span className={`project-status ${summary?.status || post.status}`} /><div><strong>{post.name}</strong><small>{machine?.name || "Unknown machine"} · {summary?.next_action.label || "Continue setup"} · {new Date(post.updated_at).toLocaleDateString()}</small></div><span>→</span></Link>;
      })}
    </section>
  </section>;
}
