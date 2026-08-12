import type { GPostDraft, GPostMapping, MachineProfile, MachineProfileRevision } from "../types";

export const WORKSPACE_TABS = ["overview", "sources", "configuration", "mappings", "test", "validation", "versions"] as const;
export type GPostTab = typeof WORKSPACE_TABS[number];

export const MAPPING_QUEUES = [
  ["required", "Required for V1"], ["needs-review", "Needs Review"], ["accepted", "Accepted"],
  ["not-applicable", "Not Applicable"], ["blocking", "Blocking"],
  ["advanced", "Advanced / Not Implemented"], ["all", "All"],
] as const;

export const MAPPING_CATEGORIES = ["Tooling", "Spindle", "Motion", "Coolant", "Coordinates", "Program Control", "Advanced"];

export function mappingCategory(mapping: GPostMapping) {
  if (typeof mapping.conditions_json.category === "string") return mapping.conditions_json.category;
  if (["LOADTL", "CUTTER", "TLAXIS"].includes(mapping.cl_command)) return "Tooling";
  if (mapping.cl_command === "SPINDL") return "Spindle";
  if (["RAPID", "GOTO", "FROM", "CIRCLE", "ARC"].includes(mapping.cl_command)) return "Motion";
  if (mapping.cl_command === "COOLNT") return "Coolant";
  if (["GOHOME"].includes(mapping.cl_command)) return "Coordinates";
  if (["CUTCOM", "CYCLE", "MULTAX", "TLAXIS", "CIRCLE", "ARC"].includes(mapping.cl_command)) return "Advanced";
  return "Program Control";
}

export function mappingVisualStatus(mapping: GPostMapping) {
  if (mapping.support_status !== "supported") return mapping.support_status.replaceAll("_", "-");
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
  const requiredMappings = mappings.filter((item) => item.required_for_v1 && item.support_status !== "not_applicable");
  const reviewed = requiredMappings.filter((item) => ["accepted", "accepted_with_edit"].includes(item.review_status)).length;
  return {
    total: mappings.length, required: requiredMappings.length, reviewed,
    needsReview: requiredMappings.length - reviewed,
    percent: Math.round(reviewed / Math.max(1, requiredMappings.length) * 100),
    notApplicable: mappings.filter((item) => item.support_status === "not_applicable").length,
    notImplemented: mappings.filter((item) => item.support_status === "not_implemented").length,
    blocking: mappings.filter((item) => item.support_status === "unsupported_required").length,
    unsupported: mappings.filter((item) => item.support_status !== "supported").length,
    warnings: draft.warnings_json.length,
  };
}

export function templateFamilyCompatible(machineType: string, family: string) {
  const normalized = machineType.toLowerCase().replaceAll("-", "_").replaceAll(" ", "_");
  const lathe = normalized.includes("lathe") || ["turning", "turning_center", "vertical_turning_center"].includes(normalized);
  if (family === "fanuc_lathe") return lathe;
  if (["fanuc_mill", "haas_mill"].includes(family)) return !lathe && normalized !== "mill_turn";
  return true;
}

export function controllerFamilyCompatible(revision: MachineProfileRevision | null, family: string) {
  if (!revision) return false;
  const controller = [revision.controller_manufacturer, revision.controller_name, revision.controller_model]
    .filter(Boolean).join(" ").toLowerCase();
  if (family.startsWith("fanuc_")) return controller.includes("fanuc");
  if (family === "haas_mill") return controller.includes("haas");
  return true;
}
