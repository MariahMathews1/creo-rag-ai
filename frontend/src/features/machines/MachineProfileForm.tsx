import { useEffect, useState, type FormEvent } from "react";
import type { MachineProfile, MachineProfileInput, MachineType } from "../../types";

type FormState = {
  name: string;
  manufacturer: string;
  model: string;
  controller_name: string;
  controller_manufacturer: string;
  controller_model: string;
  controller_version: string;
  machine_type: MachineType;
  axis_count: string;
  x_min: string;
  x_max: string;
  y_min: string;
  y_max: string;
  z_min: string;
  z_max: string;
  max_spindle_rpm: string;
  max_feed_rate: string;
  rapid_z_review_threshold: string;
  supported_work_offsets: string;
  approved_g_codes: string;
  approved_m_codes: string;
  restricted_commands: string;
  safe_start_template: string;
  tool_change_template: string;
  program_end_template: string;
  notes: string;
};

const blank: FormState = {
  name: "",
  manufacturer: "",
  model: "",
  controller_name: "",
  controller_manufacturer: "",
  controller_model: "",
  controller_version: "",
  machine_type: "mill",
  axis_count: "3",
  x_min: "",
  x_max: "",
  y_min: "",
  y_max: "",
  z_min: "",
  z_max: "",
  max_spindle_rpm: "",
  max_feed_rate: "",
  rapid_z_review_threshold: "0",
  supported_work_offsets: "G54, G55, G56, G57, G58, G59",
  approved_g_codes: "",
  approved_m_codes: "",
  restricted_commands: "",
  safe_start_template: "G17 G40 G49 G80 G90",
  tool_change_template: "T# M6",
  program_end_template: "M5 M9 G49 M30",
  notes: "",
};

const list = (value: string) =>
  value
    .split(/[,\s]+/)
    .map((item) => item.trim().toUpperCase())
    .filter(Boolean);
const numberOrNull = (value: string) => (value.trim() ? Number(value) : null);

function initialState(profile?: MachineProfile | null): FormState {
  if (!profile) return blank;
  const text = (value: string | number | null) => (value == null ? "" : String(value));
  return {
    name: profile.name,
    manufacturer: profile.manufacturer,
    model: profile.model,
    controller_name: profile.controller_name,
    controller_manufacturer: profile.controller_manufacturer ?? "",
    controller_model: profile.controller_model ?? "",
    controller_version: profile.controller_version ?? "",
    machine_type: profile.machine_type,
    axis_count: String(profile.axis_count),
    x_min: text(profile.x_min),
    x_max: text(profile.x_max),
    y_min: text(profile.y_min),
    y_max: text(profile.y_max),
    z_min: text(profile.z_min),
    z_max: text(profile.z_max),
    max_spindle_rpm: text(profile.max_spindle_rpm),
    max_feed_rate: text(profile.max_feed_rate),
    rapid_z_review_threshold: text(profile.rapid_z_review_threshold),
    supported_work_offsets: profile.supported_work_offsets.join(", "),
    approved_g_codes: profile.approved_g_codes.join(", "),
    approved_m_codes: profile.approved_m_codes.join(", "),
    restricted_commands: profile.restricted_commands.join(", "),
    safe_start_template: profile.safe_start_template ?? "",
    tool_change_template: profile.tool_change_template ?? "",
    program_end_template: profile.program_end_template ?? "",
    notes: profile.notes ?? "",
  };
}

export function MachineProfileForm({
  profile,
  onSubmit,
  onCancel,
}: {
  profile?: MachineProfile | null;
  onSubmit: (value: MachineProfileInput) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<FormState>(() => initialState(profile));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setForm(initialState(profile)), [profile]);

  const change = (key: keyof FormState, value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const value: MachineProfileInput = {
      name: form.name.trim(),
      manufacturer: form.manufacturer.trim(),
      model: form.model.trim(),
      controller_name: form.controller_name.trim(),
      controller_manufacturer: form.controller_manufacturer.trim() || null,
      controller_model: form.controller_model.trim() || null,
      controller_version: form.controller_version.trim() || null,
      machine_type: form.machine_type,
      axis_count: Number(form.axis_count),
      x_min: numberOrNull(form.x_min),
      x_max: numberOrNull(form.x_max),
      y_min: numberOrNull(form.y_min),
      y_max: numberOrNull(form.y_max),
      z_min: numberOrNull(form.z_min),
      z_max: numberOrNull(form.z_max),
      max_spindle_rpm: numberOrNull(form.max_spindle_rpm),
      max_feed_rate: numberOrNull(form.max_feed_rate),
      rapid_z_review_threshold: numberOrNull(form.rapid_z_review_threshold),
      supported_work_offsets: list(form.supported_work_offsets),
      approved_g_codes: list(form.approved_g_codes),
      approved_m_codes: list(form.approved_m_codes),
      restricted_commands: list(form.restricted_commands),
      safe_start_template: form.safe_start_template.trim() || null,
      tool_change_template: form.tool_change_template.trim() || null,
      program_end_template: form.program_end_template.trim() || null,
      notes: form.notes.trim() || null,
    };
    try {
      await onSubmit(value);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save the profile.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="profile-form" onSubmit={submit}>
      <div className="form-section">
        <div className="section-heading">
          <span>01</span>
          <div><h2>Machine identity</h2><p>Identify the machine and controller configuration.</p></div>
        </div>
        <div className="form-grid">
          <label>Profile name<input required value={form.name} onChange={(e) => change("name", e.target.value)} /></label>
          <label>Machine type<select value={form.machine_type} onChange={(e) => change("machine_type", e.target.value)}>
            <option value="mill">Mill</option><option value="lathe">Lathe</option>
            <option value="mill-turn">Mill-turn</option><option value="turning_center">Turning center</option>
            <option value="machining_center">Machining center</option><option value="vertical_mill">Vertical mill</option>
            <option value="horizontal_mill">Horizontal mill</option><option value="vertical_lathe">Vertical lathe</option>
            <option value="other">Other</option>
          </select></label>
          <label>Manufacturer<input required value={form.manufacturer} onChange={(e) => change("manufacturer", e.target.value)} /></label>
          <label>Model<input required value={form.model} onChange={(e) => change("model", e.target.value)} /></label>
          <label>Controller family<input aria-label="Controller name" required value={form.controller_name} onChange={(e) => change("controller_name", e.target.value)} /></label>
          <label>Controller manufacturer<input value={form.controller_manufacturer} onChange={(e) => change("controller_manufacturer", e.target.value)} /></label>
          <label>Controller model<input value={form.controller_model} onChange={(e) => change("controller_model", e.target.value)} /></label>
          <label>Controller version<input value={form.controller_version} onChange={(e) => change("controller_version", e.target.value)} /></label>
          <label>Axis count<input type="number" min="2" max="12" required value={form.axis_count} onChange={(e) => change("axis_count", e.target.value)} /></label>
        </div>
      </div>
      <div className="form-section">
        <div className="section-heading">
          <span>02</span>
          <div><h2>Travel and operating limits</h2><p>Values are interpreted in the program’s configured units.</p></div>
        </div>
        <div className="limit-grid">
          {(["x", "y", "z"] as const).map((axis) => (
            <div className="axis-group" key={axis}>
              <strong>{axis.toUpperCase()} axis</strong>
              <label>Minimum<input aria-label={`${axis.toUpperCase()} minimum`} type="number" step="any" value={form[`${axis}_min`]} onChange={(e) => change(`${axis}_min`, e.target.value)} /></label>
              <label>Maximum<input aria-label={`${axis.toUpperCase()} maximum`} type="number" step="any" value={form[`${axis}_max`]} onChange={(e) => change(`${axis}_max`, e.target.value)} /></label>
            </div>
          ))}
        </div>
        <div className="form-grid three">
          <label>Maximum spindle RPM<input type="number" min="0" value={form.max_spindle_rpm} onChange={(e) => change("max_spindle_rpm", e.target.value)} /></label>
          <label>Maximum feed rate<input type="number" min="0" value={form.max_feed_rate} onChange={(e) => change("max_feed_rate", e.target.value)} /></label>
          <label>Rapid Z review threshold<input type="number" step="any" value={form.rapid_z_review_threshold} onChange={(e) => change("rapid_z_review_threshold", e.target.value)} /></label>
        </div>
      </div>

      <details className="form-section advanced-machine-details">
        <summary><div className="section-heading"><span>03</span><div><h2>Advanced Machine Details</h2><p>Command policy, review thresholds, and supporting metadata.</p></div></div></summary>
      <div>
        <div className="section-heading">
          <span>A</span>
          <div><h2>Programming command policy</h2><p>Separate codes with spaces or commas.</p></div>
        </div>
        <div className="form-grid">
          <label>Supported work offsets<input value={form.supported_work_offsets} onChange={(e) => change("supported_work_offsets", e.target.value)} /></label>
          <label>Restricted commands<input value={form.restricted_commands} onChange={(e) => change("restricted_commands", e.target.value)} placeholder="e.g. G91, M0" /></label>
          <label>Approved G-codes<textarea rows={3} value={form.approved_g_codes} onChange={(e) => change("approved_g_codes", e.target.value)} /></label>
          <label>Approved M-codes<textarea rows={3} value={form.approved_m_codes} onChange={(e) => change("approved_m_codes", e.target.value)} /></label>
        </div>
      </div>
      </details>

      <div className="form-section">
        <div className="section-heading">
          <span>04</span>
          <div><h2>Approved templates</h2><p>Used by deterministic sequence checks.</p></div>
        </div>
        <div className="form-grid">
          <label>Safe-start template<textarea rows={3} value={form.safe_start_template} onChange={(e) => change("safe_start_template", e.target.value)} /></label>
          <label>Tool-change template<textarea rows={3} value={form.tool_change_template} onChange={(e) => change("tool_change_template", e.target.value)} /></label>
          <label>Program-end template<textarea rows={3} value={form.program_end_template} onChange={(e) => change("program_end_template", e.target.value)} /></label>
          <label>Notes<textarea rows={3} value={form.notes} onChange={(e) => change("notes", e.target.value)} /></label>
        </div>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions">
        <button type="button" className="button secondary" onClick={onCancel}>Cancel</button>
        <button className="button primary" disabled={saving}>{saving ? "Saving…" : profile ? "Update profile" : "Create profile"}</button>
      </div>
    </form>
  );
}
