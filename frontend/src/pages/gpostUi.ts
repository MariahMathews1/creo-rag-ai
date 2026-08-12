import type { GPostDraft, GPostMapping, MachineProfile, MachineProfileRevision } from "../types";

export const WORKSPACE_TABS = ["overview", "sources", "configuration", "mappings", "test", "validation", "versions"] as const;
export type GPostTab = typeof WORKSPACE_TABS[number];

export const MAPPING_QUEUES = [
  ["all", "All"], ["needs-review", "Needs Review"], ["accepted", "Accepted"],
  ["conflicts", "Conflicts"], ["unsupported", "Unsupported"], ["deferred", "Deferred"],
] as const;

export const MAPPING_CATEGORIES = ["Tooling", "Spindle", "Motion", "Coolant", "Coordinates", "Cycles", "Program Control"];

export function mappingCategory(mapping: GPostMapping) {
  if (["LOADTL", "CUTTER", "TLAXIS"].includes(mapping.cl_command)) return "Tooling";
  if (mapping.cl_command === "SPINDL") return "Spindle";
  if (["RAPID", "GOTO", "FROM", "CIRCLE", "ARC"].includes(mapping.cl_command)) return "Motion";
  if (mapping.cl_command === "COOLNT") return "Coolant";
  if (["GOHOME", "CUTCOM"].includes(mapping.cl_command)) return "Coordinates";
  if (mapping.cl_command === "CYCLE") return "Cycles";
  return "Program Control";
}

export function mappingVisualStatus(mapping: GPostMapping) {
  if (!mapping.supported || mapping.mapping_type === "unsupported") return "unsupported";
  if (mapping.conditions_json.conflict === true) return "conflict";
  return mapping.review_status;
}

export function profileCoverage(machine: MachineProfile, revision?: MachineProfileRevision) {
  const values = [machine.manufacturer, machine.model, machine.controller_name,
    machine.controller_manufacturer, machine.controller_model, machine.machine_type,
    machine.axis_count, machine.max_spindle_rpm, machine.max_feed_rate,
    machine.supported_work_offsets.length, revision?.approved_g_codes_json?.length,
    revision?.approved_m_codes_json?.length];
  return Math.round(values.filter((value) => value != null && value !== "" && value !== 0).length / values.length * 100);
}

export function draftReviewMetrics(draft: GPostDraft, mappings: GPostMapping[]) {
  const reviewed = mappings.filter((item) => item.review_status !== "pending").length;
  return {
    total: mappings.length, reviewed,
    percent: Math.round(reviewed / Math.max(1, mappings.length) * 100),
    unsupported: mappings.filter((item) => !item.supported).length,
    warnings: draft.warnings_json.length,
  };
}
