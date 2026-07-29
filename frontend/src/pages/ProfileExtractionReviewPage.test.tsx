import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter, Route, Routes, useLocation,
} from "react-router-dom";
import { beforeEach, test, expect, vi } from "vitest";
import { api } from "../api/client";
import { ProfileExtractionReviewPage } from "./ProfileExtractionReviewPage";

vi.mock("../api/client", () => ({ api: {
  getProfileExtraction: vi.fn(), listProfileProposals: vi.fn(),
  reviewProfileProposal: vi.fn(), applyProfileDraft: vi.fn(),
  approveProfileRevision: vi.fn(), listProfileRevisions: vi.fn(),
  rerunProfileExtraction: vi.fn(), getProfileReviewSummary: vi.fn(),
  listDocuments: vi.fn(), getDocumentContent: vi.fn(),
  batchReviewProfileProposals: vi.fn(), acceptEligibleHighConfidence: vi.fn(),
  recordProfileReviewEvent: vi.fn(),
} }));

const run = {
  id: 11, machine_profile_id: 2, target_revision_id: 1,
  status: "review_required", provider_name: "mock",
  selected_document_ids_json: [7, 8], settings_json: {},
  summary_json: { field_count: 3, found_count: 1, conflict_count: 1, not_found_count: 1 },
  detected_variants_json: ["LT-200", "LT-200Y"], selected_machine_variant: null,
  started_at: "2026-01-01", completed_at: "2026-01-01", failure_message: null,
  advisory_only: true, machine_profile_is_draft: true, qualified_review_required: true,
  safety_notice: "Extracted values require exact-machine review.",
};

const conflictProposal = {
  id: 21, extraction_run_id: 11, field_key: "max_spindle_rpm",
  field_label: "Maximum spindle RPM", field_category: "spindle",
  proposed_value_json: 4000, normalized_value_json: 4000, unit: "rpm",
  confidence: .35, proposal_status: "conflicting", review_status: "pending",
  reviewed_value_json: null, review_note: null,
  requires_exact_machine_verification: true, safety_relevant: true,
  interpretation_note: "Documents contain different values.",
  variant_applicability_json: ["LT-200", "LT-200Y"],
  evidence: [{
    id: 31, document_id: 7, document_title: "Operator manual",
    document_type: "operator_manual", document_chunk_id: 41, citation_number: 1,
    page_start: 3, page_end: 3, section_title: "Spindle",
    excerpt: "Maximum spindle speed: 4,000 rpm", raw_value_text: "4,000 rpm",
    unit: "rpm", relevance_score: 1, evidence_type: "supporting",
  }, {
    id: 32, document_id: 8, document_title: "Option sheet",
    document_type: "specification_document", document_chunk_id: 42, citation_number: 2,
    page_start: 1, page_end: 1, section_title: "Option spindle",
    excerpt: "Maximum spindle speed: 4,500 rpm", raw_value_text: "4,500 rpm",
    unit: "rpm", relevance_score: 1, evidence_type: "conflicting",
  }],
};

const foundProposal = {
  id: 22, extraction_run_id: 11, field_key: "manufacturer",
  field_label: "Manufacturer", field_category: "identity",
  proposed_value_json: "Northstar", normalized_value_json: "Northstar", unit: null,
  confidence: .96, proposal_status: "found", review_status: "pending",
  reviewed_value_json: null, review_note: null,
  requires_exact_machine_verification: false, safety_relevant: false,
  interpretation_note: null, variant_applicability_json: ["LT-200"],
  evidence: [{
    id: 33, document_id: 7, document_title: "Operator manual",
    document_type: "operator_manual", document_chunk_id: 43, citation_number: 1,
    page_start: 2, page_end: 2, section_title: "Identity",
    excerpt: "Manufacturer: Northstar", raw_value_text: "Northstar",
    unit: null, relevance_score: .98, evidence_type: "supporting",
  }],
};

const missingProposal = {
  id: 23, extraction_run_id: 11, field_key: "controller_version",
  field_label: "Controller version", field_category: "controller",
  proposed_value_json: null, normalized_value_json: null, unit: null,
  confidence: 0, proposal_status: "not_found", review_status: "pending",
  reviewed_value_json: null, review_note: null,
  requires_exact_machine_verification: false, safety_relevant: false,
  interpretation_note: null, variant_applicability_json: [],
  evidence: [],
};

const proposals = [conflictProposal, foundProposal, missingProposal];

const summary = {
  run_id: 11, machine_profile_id: 2, machine_name: "LT-200 review",
  selected_variant: null, run_status: "review_required", documents_analyzed: 2,
  total: 3, found: 1, not_found: 1, conflicting: 1, ambiguous: 0,
  pending: 3, accepted: 0, accepted_with_edit: 0, rejected: 0, deferred: 0,
  manually_entered: 0, not_applicable: 0, found_pending: 1,
  not_found_pending: 1, conflict_pending: 1, ambiguous_pending: 0,
  high_confidence_eligible: 1, safety_low_confidence_pending: 1,
  remaining_required_review: 3, reviewed: 0, review_progress_percent: 0,
  documentation_coverage: 33.3,
  category_summaries: [
    { category: "controller", total: 1, reviewed: 0, pending: 1, conflicts: 0, complete: false },
    { category: "identity", total: 1, reviewed: 0, pending: 1, conflicts: 0, complete: false },
    { category: "spindle", total: 1, reviewed: 0, pending: 1, conflicts: 1, complete: false },
  ],
  draft_ready: false, approval_ready: false, variant_rerun_required: true,
  readiness_reasons: [
    "3 proposals still require intentional review",
    "1 conflicts remain unresolved",
  ],
  recommended_next_queue: "conflicts",
  confidence_high_threshold: .9, confidence_medium_threshold: .7,
};

const draft = {
  id: 51, machine_profile_id: 2, revision_number: 2, status: "draft",
  source_type: "document_extraction", name: "LT-200", manufacturer: "Northstar",
  model: "LT-200", controller_name: "Orion 30T", controller_version: "4.8",
  controller_manufacturer: "Orion", controller_model: "30T",
  machine_type: "lathe", axis_count: 2, x_min: null, x_max: null, y_min: null,
  y_max: null, z_min: null, z_max: null, max_spindle_rpm: 4000,
  max_feed_rate: null, rapid_traverse_rate: null, supported_work_offsets_json: [],
  restricted_commands_json: [], safe_start_template: null, program_end_template: null,
  capabilities_json: {}, machine_configuration_json: {},
  review_summary: "Reviewed", approved_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  vi.mocked(api.getProfileExtraction).mockResolvedValue(run as never);
  vi.mocked(api.listProfileProposals).mockResolvedValue(proposals as never);
  vi.mocked(api.getProfileReviewSummary).mockResolvedValue(summary as never);
  vi.mocked(api.listDocuments).mockResolvedValue([
    { id: 7, title: "Operator manual", document_type: "operator_manual" },
    { id: 8, title: "Option sheet", document_type: "specification_document" },
  ] as never);
  vi.mocked(api.listProfileRevisions).mockResolvedValue([{
    ...draft, id: 1, revision_number: 1, status: "approved",
    max_spindle_rpm: 3500,
  }] as never);
  vi.mocked(api.reviewProfileProposal).mockImplementation(async (proposalId, payload) => ({
    ...(proposals.find((item) => item.id === proposalId) ?? foundProposal),
    review_status: payload.review_status,
    reviewed_value_json: payload.review_status === "accepted"
      ? proposals.find((item) => item.id === proposalId)?.proposed_value_json : null,
  } as never));
  vi.mocked(api.applyProfileDraft).mockResolvedValue({
    revision: draft, comparison: [{
      field_key: "max_spindle_rpm", current: 3500, proposed: 4000, changed: true,
    }], applied_field_keys: [],
  } as never);
  vi.mocked(api.approveProfileRevision).mockResolvedValue({
    ...draft, status: "approved",
  } as never);
  vi.mocked(api.getDocumentContent).mockResolvedValue({
    document: {
      id: 7, title: "Operator manual", document_type: "operator_manual",
    },
    pages: [{ page_number: 3, text: "Maximum spindle speed: 4,000 rpm" }],
    extracted_text: "Maximum spindle speed: 4,000 rpm",
    chunks: [],
  } as never);
  vi.mocked(api.batchReviewProfileProposals).mockResolvedValue({
    succeeded: [22], failed: [], summary: { ...summary, pending: 2, accepted: 1 },
  } as never);
  vi.mocked(api.acceptEligibleHighConfidence).mockResolvedValue({
    succeeded: [22], failed: [], summary: { ...summary, pending: 2, accepted: 1 },
  } as never);
  vi.mocked(api.recordProfileReviewEvent).mockResolvedValue(undefined as never);
});

function LocationProbe() {
  const location = useLocation();
  return <output aria-label="location">{location.pathname}{location.search}</output>;
}

function renderPage(initial = "/machines/2/profile-extraction/11") {
  return render(<MemoryRouter initialEntries={[initial]}><Routes>
    <Route path="/machines/:machineId/profile-extraction/:runId" element={<>
      <ProfileExtractionReviewPage /><LocationProbe />
    </>} />
  </Routes></MemoryRouter>);
}

test("renders the guided dashboard, queue counts, category progress, and strong states", async () => {
  renderPage();
  expect(await screen.findByText("Multiple machine variants detected")).toBeInTheDocument();
  expect(screen.getByText("Review progress: 0 / 3 fields reviewed")).toBeInTheDocument();
  expect(screen.getByText(/33.3% · not a safety score/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Conflicts\s+1/ })).toBeInTheDocument();
  expect(screen.getByLabelText("Proposal status: Conflict")).toBeInTheDocument();
  expect(screen.getAllByLabelText("Review status: Pending").length).toBeGreaterThan(0);
  expect(screen.getByText("0 / 1 reviewed · 1 pending · 1 conflicts")).toBeInTheDocument();
});

test("accepts a high-confidence field, shows confirmation, and auto-advances", async () => {
  const user = userEvent.setup();
  renderPage("/machines/2/profile-extraction/11?queue=high-confidence&field=manufacturer");
  await screen.findByRole("heading", { name: "Manufacturer" });
  await user.click(screen.getByRole("button", { name: "✓ Accept" }));
  expect(api.reviewProfileProposal).toHaveBeenCalledWith(22, expect.objectContaining({
    review_status: "accepted",
  }));
  expect(await screen.findByText(/Manufacturer marked accepted/)).toBeInTheDocument();
  expect(screen.getByLabelText("Review status: Accepted")).toBeInTheDocument();
});

test("persists queue, search, filters, field, and view in the URL", async () => {
  const user = userEvent.setup();
  renderPage("/machines/2/profile-extraction/11?queue=high-confidence&field=manufacturer");
  const search = await screen.findByLabelText("Search profile fields");
  await user.type(search, "north");
  await waitFor(() => expect(screen.getByLabelText("location")).toHaveTextContent("q=north"));
  await user.selectOptions(screen.getByLabelText("Review view"), "compact");
  expect(screen.getByLabelText("location")).toHaveTextContent("view=compact");
  await user.click(screen.getByRole("button", { name: /Filters/ }));
  await user.selectOptions(screen.getByLabelText("Category"), "identity");
  expect(screen.getByLabelText("location")).toHaveTextContent("category=identity");
  expect(screen.getByLabelText("location")).toHaveTextContent("field=manufacturer");
});

test("suppresses review shortcuts while typing and supports keyboard navigation", async () => {
  const user = userEvent.setup();
  renderPage("/machines/2/profile-extraction/11?queue=needs-review&field=max_spindle_rpm");
  const search = await screen.findByLabelText("Search profile fields");
  await user.click(search);
  await user.keyboard("a");
  expect(api.reviewProfileProposal).not.toHaveBeenCalled();
  await user.keyboard("{Escape}");
  await user.keyboard("?");
  expect(screen.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeInTheDocument();
  await user.keyboard("a");
  expect(api.reviewProfileProposal).not.toHaveBeenCalled();
  await user.keyboard("{Escape}");
  await user.keyboard("n");
  await waitFor(() => expect(screen.getByLabelText("location")).toHaveTextContent("field=manufacturer"));
});

test("opens citation in an in-route drawer and browser Back restores the same field", async () => {
  const user = userEvent.setup();
  renderPage("/machines/2/profile-extraction/11?field=max_spindle_rpm");
  await screen.findByRole("heading", { name: "Maximum spindle RPM" });
  await user.click(screen.getAllByRole("button", { name: "Open source in drawer →" })[0]);
  expect(await screen.findByRole("dialog", { name: "Operator manual" })).toBeInTheDocument();
  expect(screen.getByText("Extracted page text")).toBeInTheDocument();
  expect(screen.getByLabelText("location")).toHaveTextContent("source=7");
  await user.click(screen.getByRole("button", { name: "Close source drawer" }));
  await waitFor(() => expect(screen.queryByRole("dialog", { name: "Operator manual" })).not.toBeInTheDocument());
  expect(screen.getByLabelText("location")).toHaveTextContent("field=max_spindle_rpm");
});

test("shows batch eligibility, excluded reasons, and applies protected high-confidence acceptance", async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByText("Multiple machine variants detected");
  await user.click(screen.getByRole("button", {
    name: "Review and accept eligible high-confidence proposals",
  }));
  expect(screen.getByRole("dialog", { name: /Confirm accept for 1 fields/ })).toBeInTheDocument();
  expect(screen.getByText(/Confidence is not proof of safety/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Acknowledge and apply" }));
  expect(api.acceptEligibleHighConfidence).toHaveBeenCalledWith(11, [22]);
  expect(await screen.findByText(/1 fields updated/)).toBeInTheDocument();
});

test("switches to compact table and category checklist views", async () => {
  const user = userEvent.setup();
  renderPage("/machines/2/profile-extraction/11?queue=all");
  await screen.findByText("Multiple machine variants detected");
  await user.selectOptions(screen.getByLabelText("Review view"), "compact");
  expect(await screen.findByRole("table")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Evidence" })).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Review view"), "checklist");
  expect(
    screen.getAllByRole("button", { name: /spindle\s+0\s+\/\s+1 reviewed/i })
      .some((button) => button.classList.contains("category-checklist-heading")),
  ).toBe(true);
});

test("creates an inactive draft, renders human comparison, and requires approval acknowledgment", async () => {
  const user = userEvent.setup();
  vi.mocked(api.getProfileReviewSummary).mockResolvedValue({
    ...summary, pending: 0, reviewed: 3, draft_ready: true,
    readiness_reasons: [], review_progress_percent: 100,
  } as never);
  renderPage("/machines/2/profile-extraction/11?queue=all&field=max_spindle_rpm");
  const create = await screen.findByRole("button", { name: "Create reviewed draft" });
  expect(create).toBeEnabled();
  await user.click(create);
  expect((await screen.findByText("Revision v2", { selector: "strong" })).closest("p"))
    .toHaveTextContent("inactive");
  expect(screen.getByText("3500 → 4000")).toBeInTheDocument();
  const approve = screen.getByRole("button", { name: "Approve as active revision" });
  expect(approve).toBeDisabled();
  await user.click(screen.getByText(/I confirm this draft/).closest("label")!.querySelector("input")!);
  await user.click(approve);
  expect(api.approveProfileRevision).toHaveBeenCalled();
});

test("rolls an optimistic review state back when the mutation fails", async () => {
  const user = userEvent.setup();
  vi.mocked(api.reviewProfileProposal).mockRejectedValueOnce(new Error("Review service failed"));
  renderPage("/machines/2/profile-extraction/11?queue=high-confidence&field=manufacturer");
  await screen.findByRole("heading", { name: "Manufacturer" });
  await user.click(screen.getByRole("button", { name: "✓ Accept" }));
  expect(await screen.findByText("Review service failed")).toBeInTheDocument();
  expect(screen.getAllByLabelText("Review status: Pending").length).toBeGreaterThan(0);
});

test("protects an unsaved manual edit before changing fields", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  renderPage("/machines/2/profile-extraction/11?queue=needs-review&field=max_spindle_rpm");
  await screen.findByRole("heading", { name: "Maximum spindle RPM" });
  await user.click(screen.getByRole("button", { name: "+ Enter manually" }));
  await user.type(screen.getByLabelText("Reviewed value"), "1");
  await user.click(screen.getByRole("button", { name: /^Manufacturer identity/ }));
  expect(confirm).toHaveBeenCalled();
  expect(screen.getByRole("dialog", { name: /Manual entry/ })).toBeInTheDocument();
  confirm.mockRestore();
});

test("enables variant rerun only for a changed selection", async () => {
  const user = userEvent.setup();
  vi.mocked(api.rerunProfileExtraction).mockResolvedValue({
    ...run, id: 12, selected_machine_variant: "LT-200",
  } as never);
  renderPage();
  const rerun = await screen.findByRole("button", { name: "Re-run for selected variant" });
  expect(rerun).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("Exact machine variant"), "LT-200");
  expect(rerun).toBeEnabled();
  await user.click(rerun);
  expect(api.rerunProfileExtraction).toHaveBeenCalledWith(11, "LT-200");
});
