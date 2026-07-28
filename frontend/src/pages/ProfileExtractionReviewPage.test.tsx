import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { ProfileExtractionReviewPage } from "./ProfileExtractionReviewPage";

vi.mock("../api/client", () => ({ api: {
  getProfileExtraction: vi.fn(), listProfileProposals: vi.fn(),
  reviewProfileProposal: vi.fn(), applyProfileDraft: vi.fn(),
  approveProfileRevision: vi.fn(), listProfileRevisions: vi.fn(),
  rerunProfileExtraction: vi.fn(),
} }));

const run = {
  id: 11, machine_profile_id: 2, target_revision_id: 1,
  status: "review_required", provider_name: "mock",
  selected_document_ids_json: [7], settings_json: {},
  summary_json: { field_count: 3, found_count: 1, conflict_count: 1, not_found_count: 1 },
  detected_variants_json: ["LT-200", "LT-200Y"], selected_machine_variant: null,
  started_at: "2026-01-01", completed_at: "2026-01-01", failure_message: null,
  advisory_only: true, machine_profile_is_draft: true, qualified_review_required: true,
  safety_notice: "Extracted values require exact-machine review.",
};
const proposal = {
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
const draft = {
  id: 51, machine_profile_id: 2, revision_number: 2, status: "draft",
  source_type: "document_extraction", name: "LT-200", manufacturer: "Northstar",
  model: "LT-200", controller_name: "Orion 30T", controller_version: "4.8",
  machine_type: "lathe", axis_count: 2, x_min: null, x_max: null, y_min: null,
  y_max: null, z_min: null, z_max: null, max_spindle_rpm: 4000,
  max_feed_rate: null, rapid_traverse_rate: null, supported_work_offsets_json: [],
  restricted_commands_json: [], safe_start_template: null, program_end_template: null,
  capabilities_json: {}, machine_configuration_json: {},
  review_summary: "Reviewed", approved_at: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getProfileExtraction).mockResolvedValue(run as never);
  vi.mocked(api.listProfileProposals).mockResolvedValue([proposal] as never);
  vi.mocked(api.listProfileRevisions).mockResolvedValue([{
    ...draft, id: 1, revision_number: 1, status: "approved",
    max_spindle_rpm: 3500,
  }] as never);
  vi.mocked(api.reviewProfileProposal).mockResolvedValue({
    ...proposal, review_status: "rejected",
  } as never);
  vi.mocked(api.applyProfileDraft).mockResolvedValue({
    revision: draft, comparison: [{
      field_key: "max_spindle_rpm", current: 3500, proposed: 4000, changed: true,
    }], applied_field_keys: [],
  } as never);
  vi.mocked(api.approveProfileRevision).mockResolvedValue({
    ...draft, status: "approved",
  } as never);
});

function renderPage() {
  return render(<MemoryRouter initialEntries={["/machines/2/profile-extraction/11"]}><Routes>
    <Route path="/machines/:machineId/profile-extraction/:runId" element={<ProfileExtractionReviewPage />} />
  </Routes></MemoryRouter>);
}

test("shows variant, confidence, supporting and conflicting evidence and review actions", async () => {
  const user = userEvent.setup();
  renderPage();
  expect(await screen.findByText("Multiple machine variants detected")).toBeInTheDocument();
  expect(screen.getByText("Maximum spindle speed: 4,000 rpm")).toBeInTheDocument();
  expect(screen.getByText("Maximum spindle speed: 4,500 rpm")).toBeInTheDocument();
  expect(screen.getAllByText("35%")).toHaveLength(2);
  await user.click(screen.getByRole("button", { name: "Reject" }));
  expect(api.reviewProfileProposal).toHaveBeenCalledWith(21, expect.objectContaining({
    review_status: "rejected",
  }));
});

test("creates a non-active draft, compares it, and requires acknowledgment to approve", async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByRole("heading", { name: "Maximum spindle RPM" });
  await user.click(screen.getByRole("button", { name: "Create reviewed draft" }));
  expect((await screen.findByText(/Revision v2/)).closest("p")).toHaveTextContent("draft");
  expect(screen.getByText("3500 → 4000")).toBeInTheDocument();
  const approve = screen.getByRole("button", { name: "Approve as active revision" });
  expect(approve).toBeDisabled();
  await user.click(screen.getByRole("checkbox"));
  await user.click(approve);
  expect(api.approveProfileRevision).toHaveBeenCalledWith(
    51, "Exact machine applicability reviewed and acknowledged.",
  );
  expect(await screen.findByRole("button", { name: "Explicitly approved" })).toBeDisabled();
});

test("enables variant rerun only for a changed selection and creates a new run", async () => {
  const user = userEvent.setup();
  vi.mocked(api.rerunProfileExtraction).mockResolvedValue({
    ...run, id: 12, selected_machine_variant: "LT-200",
  } as never);
  renderPage();
  const rerun = await screen.findByRole("button", {
    name: "Re-run for selected variant",
  });
  expect(rerun).toBeDisabled();
  await user.selectOptions(screen.getByLabelText("Exact machine variant"), "LT-200");
  expect(rerun).toBeEnabled();
  await user.click(rerun);
  expect(api.rerunProfileExtraction).toHaveBeenCalledWith(11, "LT-200");
});
