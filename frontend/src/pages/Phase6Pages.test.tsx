import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { ReferenceProgramsPage } from "./ReferenceProgramsPage";
import { StandardExtractionReviewPage } from "./StandardExtractionReviewPage";
import { ApprovedProgramComparisonPage } from "./ApprovedProgramComparisonPage";

vi.mock("../api/client", () => ({ api: {
  listReferencePrograms: vi.fn(), listProfileRevisions: vi.fn(),
  listStandardExtractions: vi.fn(), listStandards: vi.fn(),
  parseReferenceProgram: vi.fn(), markReferenceEligible: vi.fn(),
  markReferenceIneligible: vi.fn(), createReferenceProgram: vi.fn(),
  startStandardExtraction: vi.fn(), getStandardExtraction: vi.fn(),
  listStandardConventions: vi.fn(), reviewStandardConvention: vi.fn(),
  batchReviewConventions: vi.fn(), createStandardDraft: vi.fn(),
  submitStandard: vi.fn(), approveStandard: vi.fn(),
  standardReportUrl: vi.fn((id) => `/standard-${id}.md`),
  getStandardComparison: vi.fn(), getSideBySideComparison: vi.fn(),
  listSimilarPrograms: vi.fn(), classifyComparisonException: vi.fn(),
  comparisonReportUrl: vi.fn((id) => `/comparison-${id}.md`),
} }));

const safety = {
  advisory_only: true, historical_similarity_is_not_certification: true,
  qualified_review_required: true, safety_notice: "Similarity is not certification.",
};
const program = {
  ...safety, id: 1, machine_profile_id: 2, machine_profile_revision_id: 3,
  source_document_id: 4, name: "Eligible turning example", description: null,
  original_filename: "eligible.nc", file_hash: "a".repeat(64), program_number: "8101",
  program_type: "turning", controller_name: "FANUC", controller_version: "0i-TF",
  controller_variant: null, post_processor_name: "Creo post",
  post_processor_version: null, post_processor_revision: "POST-A",
  part_identifier: "DEMO", operation_identifier: "OP10", material: null,
  units: "inch", machine_variant: "KLS-1840N", installed_options_json: [],
  approval_status: "approved_reference", eligibility_status: "eligible",
  eligibility_reason: "Reviewed", approved_by_label: "QA", parsing_status: "parsed",
  parser_version: "gcode-parser-v1", rule_set_version: "validation-v1",
  validation_summary_json: { blocking_count: 0 }, source_integrity_json: {},
  ai_processing_allowed: false, imported_at: "", updated_at: "",
};
const convention = {
  ...safety, id: 10, standard_profile_id: null, extraction_run_id: 5,
  convention_key: "m30_end", category: "program_ending", title: "Program ends with M30",
  description: "Observed in 5 of 6 eligible programs. Frequency is not authority.",
  convention_type: "required_presence", expected_pattern_json: { codes: ["M30"] },
  condition_json: {}, expected_behavior_json: {}, applicability_json: {
    post_processor_versions: ["POST-A"],
  }, severity: "review_recommended", confidence: .83, support_count: 5,
  eligible_program_count: 6, support_percentage: 83.3,
  frequency_classification: "common", proposal_status: "conflicting",
  review_status: "pending", review_note: null, safety_relevant: true,
  evidence: [{
    id: 20, reference_program_id: 1, gcode_block_id: 30, line_start: 14,
    line_end: 14, excerpt: "N110 M30", evidence_type: "supporting",
    match_context_json: { post_processor_revision: "POST-A" },
    program_name: "Eligible turning example",
  }],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listReferencePrograms).mockResolvedValue([program] as never);
  vi.mocked(api.listProfileRevisions).mockResolvedValue([{
    id: 3, revision_number: 1, status: "approved", model: "KLS-1840N",
    controller_name: "FANUC", controller_version: "0i-TF",
  }] as never);
  vi.mocked(api.listStandardExtractions).mockResolvedValue([] as never);
  vi.mocked(api.listStandards).mockResolvedValue([] as never);
  vi.mocked(api.getStandardExtraction).mockResolvedValue({
    ...safety, id: 5, machine_profile_id: 2, machine_profile_revision_id: 3,
    status: "review_required", selected_reference_program_ids_json: [1],
    algorithm_version: "standards-v1",
    settings_json: {}, summary_json: { eligible_program_count: 6 },
    completed_at: "",
  } as never);
  vi.mocked(api.listStandardConventions).mockResolvedValue([convention] as never);
  vi.mocked(api.reviewStandardConvention).mockResolvedValue({
    ...convention, review_status: "accepted",
  } as never);
});

test("reference library shows explicit approval, eligibility, integrity, and AI controls", async () => {
  render(<MemoryRouter initialEntries={["/machines/2/reference-programs"]}><Routes>
    <Route path="/machines/:machineId/reference-programs" element={<ReferenceProgramsPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Eligible turning example")).toBeInTheDocument();
  expect(screen.getByText("approved reference")).toBeInTheDocument();
  expect(screen.getByText("eligible")).toBeInTheDocument();
  expect(screen.getByText("Restricted from external AI")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Mark eligible" })).toBeInTheDocument();
});

test("standard workspace shows frequency, program-line evidence, and individual review", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/machines/2/standards/extraction/5"]}><Routes>
    <Route path="/machines/:machineId/standards/extraction/:runId"
      element={<StandardExtractionReviewPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Program ends with M30", { selector: "h2" })).toBeInTheDocument();
  expect(screen.getByText(/5 \/ 6/)).toBeInTheDocument();
  expect(screen.getByText("N110 M30")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Accept as scoped convention" }));
  expect(api.reviewStandardConvention).toHaveBeenCalledWith(
    10, expect.objectContaining({ review_status: "accepted" }),
  );
});

test("comparison keeps evidence layers separate and supports exception classification", async () => {
  const finding = {
    id: 40, comparison_run_id: 8, standard_convention_id: 10,
    severity: "review_recommended", status: "open", title: "Coolant off before end",
    description: "The current program omits a pattern.", line_number: null,
    source_line: null, expected_pattern_json: { codes: ["M09"] },
    observed_pattern_json: {}, comparison_type: "missing",
    recommendation: "Review applicability.", exception_classification: null,
    exception_note: null,
  };
  vi.mocked(api.getStandardComparison).mockResolvedValue({
    ...safety, id: 8, analysis_project_id: 7, machine_profile_revision_id: 3,
    standard_profile_id: 6, reference_program_id: 1, status: "completed",
    summary_json: { matches: 3, missing: 1, unexpected: 1, not_applicable: 1 },
    parser_version: "gcode-parser-v1", algorithm_version: "comparison-v1",
    stale: false, stale_reasons_json: [], findings: [finding],
  } as never);
  vi.mocked(api.getSideBySideComparison).mockResolvedValue({
    ...safety, comparison_id: 8, current_program: "M02", reference_program: "M30",
    sections: [{ type: "changed", reference_line_start: 1, current_line_start: 1,
      reference_lines: ["M30"], current_lines: ["M02"] }],
    source_metadata: { reference_program_name: "Eligible", post_processor_revision: "POST-A" },
    deterministic_findings: [{ title: "Restricted command" }],
    convention_findings: [finding],
  } as never);
  vi.mocked(api.listSimilarPrograms).mockResolvedValue([{
    program, similarity_score: 84, match_reasons: ["Same machine"],
    differences: ["Only in reference: M30"],
  }] as never);
  vi.mocked(api.classifyComparisonException).mockResolvedValue({
    ...finding, status: "classified_exception",
  } as never);
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/analyses/7/approved-program-comparison/8"]}><Routes>
    <Route path="/analyses/:analysisId/approved-program-comparison/:comparisonId"
      element={<ApprovedProgramComparisonPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Deterministic validation")).toBeInTheDocument();
  expect(screen.getByText("Organizational conventions")).toBeInTheDocument();
  expect(screen.getByText("84% structural similarity")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Coolant off before end/ }));
  await user.type(screen.getByLabelText("Required note"), "Reason unknown.");
  await user.click(screen.getByRole("button", { name: "Save classification" }));
  expect(api.classifyComparisonException).toHaveBeenCalledWith(
    40, "requires_investigation", "Reason unknown.",
  );
});
