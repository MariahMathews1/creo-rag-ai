import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { ActionMenu } from "../components/ActionMenu";
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
        <PageHeader eyebrow="Machine configuration" title={editing ? "Edit machine" : "Add machine"} description="Enter the machine, controller, motion limits, and post-related behavior used for generation and review." />
        <MachineProfileForm profile={editing} onSubmit={save} onCancel={() => { setShowForm(false); setEditing(null); }} />
      </section>
    );
  }

  return (
    <section className="page">
      <PageHeader
        eyebrow="Configuration"
        title="Machines"
        description="Everything starts with the CNC machine. Store the controller, travel, limits, and post-related behavior here."
        action={<button className="button primary" onClick={() => setShowForm(true)}>+ Add Machine</button>}
      />
      {error && <p className="form-error" role="alert">{error}</p>}
      {loading ? <p className="loading" role="status">Loading machine profiles…</p> : profiles.length === 0 ? (
        <div className="empty-state"><span>◆</span><h2>No machines yet</h2><p>Add a machine before generating or reviewing G-code.</p><button className="button primary" onClick={() => setShowForm(true)}>Add Machine</button></div>
      ) : (
        <div className="profile-list">
          {profiles.map((profile) => (
            <article className="profile-card" key={profile.id}>
              {(() => { const missing = [{ label: "X travel", absent: profile.x_min == null || profile.x_max == null }, { label: "Z travel", absent: profile.z_min == null || profile.z_max == null }, { label: "Spindle limit", absent: profile.max_spindle_rpm == null }].filter((item) => item.absent).map((item) => item.label); return <>
              <div className="profile-card-head">
                <div><span className="machine-type">{profile.machine_type}</span><h2>{profile.name}</h2><p>{profile.manufacturer} {profile.model} · {profile.controller_name}</p><div className={`machine-completeness ${missing.length ? "needs-info" : "complete"}`}><strong>{missing.length ? "Needs Information" : "Complete"}</strong>{missing.length > 0 && <small>Missing: {missing.join(" · ")}</small>}</div></div>
                <div className="card-actions"><Link className="button primary" to={`/gpost?machine=${profile.id}`}>Generate G-POST Draft</Link><Link className="button secondary" to={`/machines/${profile.id}/profile-extraction/new`}>{missing.length ? "Find in Documents" : "Find More Information"}</Link><button className="button secondary" onClick={() => { setEditing(profile); setShowForm(true); }}>Open Machine</button><ActionMenu label="More" items={[{ label: "Edit Machine", onSelect: () => { setEditing(profile); setShowForm(true); } }, { label: "Configuration History", to: `/machines/${profile.id}/revisions` }, { label: "Reference Programs", to: `/machines/${profile.id}/reference-programs` }, { label: "Delete Machine", danger: true, divider: true, onSelect: () => void remove(profile) }]} /></div>
              </div>
              <div className="limits-row">
                <span><small>X travel</small>{profile.x_min ?? "—"} to {profile.x_max ?? "—"}</span>
                <span><small>Y travel</small>{profile.y_min ?? "—"} to {profile.y_max ?? "—"}</span>
                <span><small>Z travel</small>{profile.z_min ?? "—"} to {profile.z_max ?? "—"}</span>
                <span><small>Spindle</small>{profile.max_spindle_rpm?.toLocaleString() ?? "—"} RPM</span>
                <span><small>Max feed</small>{profile.max_feed_rate?.toLocaleString() ?? "—"}</span>
              </div>
              </>; })()}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
