const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  under_review: "Under Review",
  review_required: "Under Review",
  validated_for_rnd: "R&D Validated",
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
  return <span aria-label={`Status: ${STATUS_LABELS[status] ?? status.replaceAll("_", " ")}`} className={`gpost-status ${normalized}${large ? " large" : ""}`}>
    {STATUS_LABELS[status] ?? status.replaceAll("_", " ")}
  </span>;
}
