import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { MachineProfileForm } from "../features/machines/MachineProfileForm";
import type { MachineProfile, MachineProfileInput } from "../types";

export function MachineProfilesPage() {
  const [profiles, setProfiles] = useState<MachineProfile[]>([]);
  const [editing, setEditing] = useState<MachineProfile | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError("");
    return api
      .listProfiles()
      .then(setProfiles)
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "Unable to load profiles."),
      )
      .finally(() => setLoading(false));
  };
  useEffect(() => { void load(); }, []);

  async function save(value: MachineProfileInput) {
    if (editing) await api.updateProfile(editing.id, value);
    else await api.createProfile(value);
    setShowForm(false);
    setEditing(null);
    await load();
  }

  async function remove(profile: MachineProfile) {
    if (!window.confirm(`Delete “${profile.name}” and its related analyses?`)) return;
    try {
      await api.deleteProfile(profile.id);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete profile.");
    }
  }

  if (showForm) {
    return (
      <section className="page">
        <PageHeader eyebrow="Machine configuration" title={editing ? "Edit machine profile" : "Create machine profile"} description="Define the physical limits and approved controller policy used during deterministic review." />
        <MachineProfileForm profile={editing} onSubmit={save} onCancel={() => { setShowForm(false); setEditing(null); }} />
      </section>
    );
  }

  return (
    <section className="page">
      <PageHeader
        eyebrow="Configuration"
        title="Machine profiles"
        description="Machine-specific limits and controller policies are the source of truth for every analysis."
        action={<button className="button primary" onClick={() => setShowForm(true)}>+ New profile</button>}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      {loading ? <p className="loading" role="status">Loading machine profiles…</p> : profiles.length === 0 ? (
        <div className="empty-state"><span>◆</span><h2>No machine profiles yet</h2><p>Create one before starting an analysis.</p><button className="button primary" onClick={() => setShowForm(true)}>Create profile</button></div>
      ) : (
        <div className="profile-list">
          {profiles.map((profile) => (
            <article className="profile-card" key={profile.id}>
              <div className="profile-card-head">
                <div><span className="machine-type">{profile.machine_type}</span><h2>{profile.name}</h2><p>{profile.manufacturer} {profile.model} · {profile.controller_name}</p></div>
                <div className="card-actions"><Link to={`/machines/${profile.id}/profile-extraction/new`}>Extract from documents</Link><Link to={`/machines/${profile.id}/reference-programs`}>Approved programs</Link><Link to={`/machines/${profile.id}/revisions`}>Revisions</Link><Link to={`/gpost?machine=${profile.id}`}>G-POST</Link><button onClick={() => { setEditing(profile); setShowForm(true); }}>Edit</button><button className="danger-link" onClick={() => void remove(profile)}>Delete</button></div>
              </div>
              <div className="limits-row">
                <span><small>X travel</small>{profile.x_min ?? "—"} to {profile.x_max ?? "—"}</span>
                <span><small>Y travel</small>{profile.y_min ?? "—"} to {profile.y_max ?? "—"}</span>
                <span><small>Z travel</small>{profile.z_min ?? "—"} to {profile.z_max ?? "—"}</span>
                <span><small>Spindle</small>{profile.max_spindle_rpm?.toLocaleString() ?? "—"} RPM</span>
                <span><small>Max feed</small>{profile.max_feed_rate?.toLocaleString() ?? "—"}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
