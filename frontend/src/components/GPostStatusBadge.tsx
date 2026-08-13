const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  under_review: "Ready for R&D Test",
  review_required: "Needs Configuration",
  validated_for_rnd: "R&D Tested",
  superseded: "Superseded",
  archived: "Archived",
  blocked: "Blocked",
  pending: "Needs Review",
  accepted: "Accepted",
  accepted_with_edit: "Accepted",
  rejected: "Rejected",
  deferred: "Deferred",
  conflict: "Conflict",
  unsupported: "Unsupported",
  unsupported_required: "Blocking",
  "unsupported-required": "Blocking",
  not_applicable: "Not Applicable",
  "not-applicable": "Not Applicable",
  not_implemented: "Not Implemented",
  "not-implemented": "Not Implemented",
  inherited: "Inherited",
};

export function GPostStatusBadge({ status, large = false }: { status: string; large?: boolean }) {
  const normalized = status === "review_required" ? "under_review" : status;
  const help: Record<string, string> = { under_review: "Sufficient machine and post configuration for R&D previews of supported CL/NCL. Not approved for machine use.", review_required: "A required machine or post configuration issue needs attention.", validated_for_rnd: "An R&D preview was generated and deterministic checks completed. Not production-approved." };
  return <span title={help[status]} aria-label={`Status: ${STATUS_LABELS[status] ?? status.replaceAll("_", " ")}`} className={`gpost-status ${normalized}${large ? " large" : ""}`}>
    {STATUS_LABELS[status] ?? status.replaceAll("_", " ")}
  </span>;
}
