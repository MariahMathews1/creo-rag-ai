import type {
  MachineProfileRevision,
  ProfileProposal,
  ProfileReviewSummary,
} from "../types";

export const REVIEW_QUEUES = [
  ["needs-review", "Needs review"],
  ["conflicts", "Conflicts"],
  ["high-confidence", "High confidence"],
  ["medium-confidence", "Medium confidence"],
  ["low-confidence", "Low confidence"],
  ["not-found", "Not found"],
  ["deferred", "Deferred"],
  ["accepted", "Accepted"],
  ["rejected", "Rejected"],
  ["manual-entries", "Manual entries"],
  ["not-applicable", "Not applicable"],
  ["all", "All fields"],
] as const;

export type ReviewQueue = (typeof REVIEW_QUEUES)[number][0];
export type ReviewView = "detailed" | "compact" | "checklist";

export const REVIEW_STATUS_META: Record<string, { icon: string; label: string }> = {
  pending: { icon: "○", label: "Pending" },
  accepted: { icon: "✓", label: "Accepted" },
  accepted_with_edit: { icon: "✎", label: "Accepted with edit" },
  rejected: { icon: "×", label: "Rejected" },
  deferred: { icon: "↷", label: "Deferred" },
  manually_entered: { icon: "+", label: "Manual entry" },
  not_applicable: { icon: "—", label: "Not applicable" },
};

export const PROPOSAL_STATUS_META: Record<string, { icon: string; label: string }> = {
  found: { icon: "●", label: "Found" },
  derived: { icon: "◆", label: "Derived" },
  conflicting: { icon: "!", label: "Conflict" },
  ambiguous: { icon: "?", label: "Ambiguous" },
  not_found: { icon: "—", label: "Not found" },
};

export function showValue(value: unknown): string {
  if (value == null || value === "") return "Not found";
  if (typeof value === "boolean") return value ? "Present" : "Not present";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export function currentValue(
  proposal: ProfileProposal,
  revision?: MachineProfileRevision,
): unknown {
  if (!revision) return null;
  const direct = (revision as unknown as Record<string, unknown>)[proposal.field_key];
  if (direct != null) return direct;
  if (proposal.field_key === "machine_model") return revision.model;
  if (proposal.field_category === "capabilities") {
    return revision.capabilities_json[proposal.field_key] ?? null;
  }
  return revision.machine_configuration_json[proposal.field_key] ?? null;
}

export function matchesQueue(
  proposal: ProfileProposal,
  queue: ReviewQueue,
  high: number,
  medium: number,
): boolean {
  if (queue === "all") return true;
  if (queue === "needs-review") return proposal.review_status === "pending";
  if (queue === "conflicts") {
    return proposal.review_status === "pending"
      && proposal.proposal_status === "conflicting";
  }
  if (queue === "high-confidence") {
    return proposal.review_status === "pending"
      && proposal.proposal_status === "found"
      && proposal.confidence >= high;
  }
  if (queue === "medium-confidence") {
    return proposal.review_status === "pending"
      && proposal.proposal_status === "found"
      && proposal.confidence >= medium
      && proposal.confidence < high;
  }
  if (queue === "low-confidence") {
    return proposal.review_status === "pending"
      && proposal.proposal_status === "found"
      && proposal.confidence < medium;
  }
  if (queue === "not-found") {
    return proposal.review_status === "pending"
      && proposal.proposal_status === "not_found";
  }
  const status = {
    deferred: "deferred",
    accepted: "accepted",
    rejected: "rejected",
    "manual-entries": "manually_entered",
    "not-applicable": "not_applicable",
  }[queue];
  return proposal.review_status === status;
}

export function queueCounts(
  proposals: ProfileProposal[],
  summary: ProfileReviewSummary | null,
): Record<ReviewQueue, number> {
  const high = summary?.confidence_high_threshold ?? .9;
  const medium = summary?.confidence_medium_threshold ?? .7;
  return Object.fromEntries(REVIEW_QUEUES.map(([key]) => [
    key,
    proposals.filter((item) => matchesQueue(item, key, high, medium)).length,
  ])) as Record<ReviewQueue, number>;
}

export interface ReviewFilters {
  category: string;
  proposalStatus: string;
  reviewStatus: string;
  confidence: string;
  safetyOnly: boolean;
  verificationOnly: boolean;
  evidence: string;
  sourceDocument: string;
  sourceAuthority: string;
  claimScope: string;
  variant: string;
  optionalOnly: boolean;
  search: string;
  sort: string;
  direction: "asc" | "desc";
}

export function filtersFromParams(params: URLSearchParams): ReviewFilters {
  return {
    category: params.get("category") ?? "all",
    proposalStatus: params.get("proposal") ?? "all",
    reviewStatus: params.get("review") ?? "all",
    confidence: params.get("confidence") ?? "all",
    safetyOnly: params.get("safety") === "1",
    verificationOnly: params.get("verification") === "1",
    evidence: params.get("evidence") ?? "all",
    sourceDocument: params.get("document") ?? "all",
    sourceAuthority: params.get("authority") ?? "all",
    claimScope: params.get("scope") ?? "all",
    variant: params.get("variant") ?? "all",
    optionalOnly: params.get("optional") === "1",
    search: params.get("q") ?? "",
    sort: params.get("sort") ?? "priority",
    direction: params.get("direction") === "desc" ? "desc" : "asc",
  };
}

export function filterProposals(
  proposals: ProfileProposal[],
  queue: ReviewQueue,
  filters: ReviewFilters,
  summary: ProfileReviewSummary | null,
  revision?: MachineProfileRevision,
): ProfileProposal[] {
  const high = summary?.confidence_high_threshold ?? .9;
  const medium = summary?.confidence_medium_threshold ?? .7;
  const search = filters.search.trim().toLocaleLowerCase();
  const priority: Record<string, number> = {
    conflicting: 0, ambiguous: 1, found: 2, derived: 2, not_found: 3,
  };
  const result = proposals.filter((proposal) => {
    if (!matchesQueue(proposal, queue, high, medium)) return false;
    if (filters.category !== "all" && proposal.field_category !== filters.category) return false;
    if (filters.proposalStatus !== "all" && proposal.proposal_status !== filters.proposalStatus) return false;
    if (filters.reviewStatus !== "all" && proposal.review_status !== filters.reviewStatus) return false;
    if (filters.confidence === "high" && proposal.confidence < high) return false;
    if (filters.confidence === "medium" && (
      proposal.confidence < medium || proposal.confidence >= high
    )) return false;
    if (filters.confidence === "low" && proposal.confidence >= medium) return false;
    if (filters.safetyOnly && !proposal.safety_relevant) return false;
    if (filters.verificationOnly && !proposal.requires_exact_machine_verification) return false;
    if (filters.optionalOnly && !proposal.requires_exact_machine_verification) return false;
    if (filters.evidence === "has" && !proposal.evidence.length) return false;
    if (filters.evidence === "none" && proposal.evidence.length) return false;
    if (filters.evidence === "conflicting" && !proposal.evidence.some(
      (item) => item.evidence_type === "conflicting",
    )) return false;
    if (filters.sourceDocument !== "all" && !proposal.evidence.some(
      (item) => item.document_id === Number(filters.sourceDocument),
    )) return false;
    if (filters.sourceAuthority !== "all" && !proposal.evidence.some(
      (item) => item.document_type === filters.sourceAuthority,
    )) return false;
    if (filters.claimScope !== "all" && proposal.field_category !== filters.claimScope) return false;
    if (filters.variant !== "all" && proposal.variant_applicability_json.length
      && !proposal.variant_applicability_json.includes(filters.variant)) return false;
    if (!search) return true;
    const searchable = [
      proposal.field_label, proposal.field_key, proposal.field_category,
      showValue(proposal.proposed_value_json), showValue(currentValue(proposal, revision)),
      proposal.review_note ?? "",
      ...proposal.evidence.flatMap((item) => [item.document_title, item.excerpt]),
    ].join(" ").toLocaleLowerCase();
    return searchable.includes(search);
  });
  const value = (proposal: ProfileProposal): string | number => {
    if (filters.sort === "field") return proposal.field_label.toLocaleLowerCase();
    if (filters.sort === "category") return proposal.field_category;
    if (filters.sort === "confidence") return proposal.confidence;
    if (filters.sort === "proposal") return proposal.proposal_status;
    if (filters.sort === "review") return proposal.review_status;
    if (filters.sort === "evidence") return proposal.evidence.length;
    return priority[proposal.proposal_status] ?? 4;
  };
  result.sort((left, right) => {
    const a = value(left); const b = value(right);
    const compared = typeof a === "number" && typeof b === "number"
      ? a - b : String(a).localeCompare(String(b));
    return (filters.direction === "desc" ? -1 : 1) * (
      compared || left.field_label.localeCompare(right.field_label)
    );
  });
  return result;
}

export function batchAcceptBlockReason(
  proposal: ProfileProposal,
  summary: ProfileReviewSummary | null,
): string | null {
  const high = summary?.confidence_high_threshold ?? .9;
  if (proposal.review_status !== "pending") return "Already reviewed";
  if (proposal.proposal_status === "conflicting") return "Unresolved conflict";
  if (proposal.proposal_status === "ambiguous") return "Ambiguous proposal";
  if (proposal.proposal_status !== "found") return "No found value";
  if (proposal.confidence < high) return "Below high-confidence threshold";
  if (proposal.normalized_value_json == null) return "Normalized value missing";
  if (!proposal.evidence.some((item) => item.evidence_type === "supporting")) {
    return "Supporting citation missing";
  }
  if (proposal.evidence.some((item) => item.evidence_type === "conflicting")) {
    return "Conflicting evidence";
  }
  if (proposal.requires_exact_machine_verification) return "Exact-machine verification required";
  if (proposal.safety_relevant) return "Safety-relevant field needs individual review";
  return null;
}

export function activeFilterEntries(filters: ReviewFilters): Array<[string, string]> {
  const entries: Array<[string, string]> = [];
  if (filters.category !== "all") entries.push(["category", filters.category]);
  if (filters.proposalStatus !== "all") entries.push(["proposal", filters.proposalStatus]);
  if (filters.reviewStatus !== "all") entries.push(["review", filters.reviewStatus]);
  if (filters.confidence !== "all") entries.push(["confidence", filters.confidence]);
  if (filters.safetyOnly) entries.push(["safety", "Safety relevant"]);
  if (filters.verificationOnly) entries.push(["verification", "Verification required"]);
  if (filters.evidence !== "all") entries.push(["evidence", filters.evidence]);
  if (filters.sourceDocument !== "all") entries.push(["document", "Source document"]);
  if (filters.sourceAuthority !== "all") entries.push(["authority", filters.sourceAuthority]);
  if (filters.claimScope !== "all") entries.push(["scope", filters.claimScope]);
  if (filters.variant !== "all") entries.push(["variant", filters.variant]);
  if (filters.optionalOnly) entries.push(["optional", "Optional capability"]);
  return entries;
}

