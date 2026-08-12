import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { TranslationDetailPage } from "./TranslationDetailPage";
import { TranslationExamplesPage } from "./TranslationExamplesPage";

vi.mock("../api/client", () => ({ api: {
  listTranslations: vi.fn(), listProfiles: vi.fn(), getTranslationSummary: vi.fn(),
  getTranslationExplorer: vi.fn(), listProfileRevisions: vi.fn(), importTranslation: vi.fn(), createTranslation: vi.fn(),
  getTranslation: vi.fn(), createTranslationAlignment: vi.fn(), confirmTranslationLink: vi.fn(),
  rejectTranslationLink: vi.fn(), transitionTranslation: vi.fn(),
  getTranslationToolpath: vi.fn(), getTranslationHistory: vi.fn(),
  getTranslationAIProviderStatus: vi.fn(), retrieveTranslationExamples: vi.fn(), explainTranslation: vi.fn(),
  setTranslationAIConsent: vi.fn(),
} }));

const machine = { id: 1, name: "Fictional KLS", controller_name: "FANUC", manufacturer: "Fictional", model: "KLS", machine_type: "lathe", axis_count: 2 };
const link = { id: 8, alignment_id: 4, cl_record_start: 0, cl_record_end: 0, gcode_block_start: 0, gcode_block_end: 0, link_type: "one_to_one", confidence: .9, review_status: "proposed", match_reasons_json: ["same_spindle_speed"], notes: null, reviewed_by_label: null, created_at: "", updated_at: "" };
const example = { id: 3, machine_profile_id: 1, machine_profile_revision_id: 2, reference_program_id: null, name: "Fictional spindle pair", description: null, controller_name: "FANUC", controller_version: null, post_processor_name: "Site Post", post_processor_revision: "R12", operation_type: "turning", operation_name: null, cl_source_text: "SPINDL/RPM,1200", cl_source_hash: "a".repeat(64), cl_original_filename: "demo.cl", gcode_source_text: "S1200 M03", gcode_source_hash: "b".repeat(64), gcode_original_filename: "demo.nc", verification_status: "candidate", part_identifier: "DEMO", program_identifier: null, project_identifier: null, tooling_context_json: {}, setup_context_json: {}, machine_context_snapshot_json: {}, source_system: "Controlled archive", source_repository: null, work_order_reference: null, imported_by_label: null, source_provenance: "Fictional evidence", verification_basis: null, verification_note: null, cl_parse_summary_json: { cl_record_count: 1 }, gcode_parse_summary_json: { gcode_block_count: 1 }, parsed_cl_records_json: [{ text: "SPINDL/RPM,1200" }], parsed_gcode_blocks_json: [{ text: "S1200 M03" }], validation_summary_json: { blocking_count: 0, warning_count: 0 }, ai_processing_allowed: false, created_at: "", updated_at: "", reviewed_at: null, verified_at: null, deprecated_at: null, alignments: [{ id: 4, translation_example_id: 3, status: "proposed", algorithm_version: "v1", summary_json: { coverage_percent: 100, proposed: 1 }, created_at: "", updated_at: "", links: [link] }], advisory_only: true, safety_notice: "R&D" };

beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.listTranslations).mockResolvedValue([example] as never); vi.mocked(api.listProfiles).mockResolvedValue([machine] as never); vi.mocked(api.getTranslationSummary).mockResolvedValue({ total: 1, candidates: 1, reviewed: 0, verified: 0, deprecated: 0, invalid: 0, by_machine: [], by_post_revision: [], by_operation: [] }); vi.mocked(api.getTranslationExplorer).mockResolvedValue([{ machine_profile_id: 1, machine: "Fictional KLS", controller: "FANUC", post_revision: "R12", operation: "turning", cl_command: "SPINDL", cl_pattern: "SPINDL/RPM,{rpm}", gcode_pattern: "S{rpm} M03", count: 2 }]); vi.mocked(api.getTranslation).mockResolvedValue(example as never); vi.mocked(api.confirmTranslationLink).mockResolvedValue({ ...link, review_status: "confirmed" } as never); vi.mocked(api.getTranslationHistory).mockResolvedValue([]); vi.mocked(api.getTranslationAIProviderStatus).mockResolvedValue({ provider: "mock", configured: true, reachable: true, authentication_mode: "none", deployment: "fixture", model: "mock", external_processing: false, public_web: false, data_source: "Verified Internal Translation Examples Only", mode: "R&D", error_code: null }); vi.mocked(api.retrieveTranslationExamples).mockResolvedValue({ retrieval_scope: "exact_machine_exact_post", eligible_count: 1, public_web: false, ai_called: false, warnings: [], examples: [{ example_id: 3, name: "Fictional spindle pair", machine_profile_id: 1, machine: "Fictional KLS", machine_profile_revision_id: 2, controller: "FANUC", post_revision: "R12", operation: "turning", cl_excerpt: "SPINDL/RPM,1200", gcode_excerpt: "S1200 M03", cl_pattern_match: "strong", alignment_coverage: 100, verification_status: "verified_successful", retrieval_reasons: ["exact_machine", "exact_post_revision"], ai_processing_allowed: true }] }); vi.mocked(api.explainTranslation).mockResolvedValue({ status: "advisory_interpretation", input_cl: "SPINDL/RPM,1200,CLW", interpreted_operation: "clockwise_spindle_start", suggested_mapping_pattern: "S{rpm} M03", short_rationale: "Observed verified pattern.", example_ids: [3], uncertainties: ["Low"], unsupported_features: [], warnings: [], provider_metadata: { provider: "mock" }, invocation_id: 4, advisory_only: true, safety_notice: "R&D ADVISORY INTERPRETATION ONLY" }); vi.mocked(api.setTranslationAIConsent).mockResolvedValue({ ...example, ai_processing_allowed: true } as never); vi.mocked(api.getTranslationToolpath).mockResolvedValue({ source: "both", machine_type: "lathe", default_view: "XZ", coordinate_context: "work", bounds: { min_x: 0, max_x: 1, min_y: 0, max_y: 0, min_z: 0, max_z: 1 }, summary: { segments: 1, rapid: 0, feed: 1, arcs: 0, tools: 0, operations: 0, unresolved_geometry: 0, visualization_simplified: false }, warnings: [], comparison_summary: { aligned_motion_pairs: 1, matching_geometry: 1 }, advisory_only: true, safety_notice: "TOOLPATH VISUALIZATION ONLY", segments: [{ id: "cl-1", source_type: "cl", source_record_id: 1, source_line_start: 1, source_line_end: 1, operation_id: null, tool_number: null, motion_type: "linear", start_point: { x: 0, y: 0, z: 0 }, end_point: { x: 1, y: 0, z: 1 }, center_point: null, radius: null, path_points: [], plane: null, feed_rate: null, spindle_speed: 1200, rapid: false, arc_direction: null, helical: false, tool_axis: null, alignment_link_id: 8, aligned_segment_ids: [], finding_ids: [], sequence_index: 0, visualizable: true, unmatched: false, geometry_status: "matching_geometry", metadata_json: {} }] } as never); });

test("translation library shows governed pairs and isolated verified patterns", async () => {
  const user = userEvent.setup(); render(<MemoryRouter><TranslationExamplesPage /></MemoryRouter>);
  expect(await screen.findByText("Fictional spindle pair")).toBeInTheDocument();
  expect(screen.getByText("Historical evidence, not production authorization")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Pattern Explorer" }));
  expect(screen.getByText("SPINDL/RPM,{rpm}")).toBeInTheDocument();
  expect(screen.getByText("S{rpm} M03")).toBeInTheDocument();
});

test("detail workspace exposes alignment rationale and reviewer actions", async () => {
  const user = userEvent.setup(); render(<MemoryRouter initialEntries={["/translations/3"]}><Routes><Route path="/translations/:exampleId" element={<TranslationDetailPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Pair alignment")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /one to one/i }));
  expect(screen.getByText(/same_spindle_speed/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Confirm" }));
  await waitFor(() => expect(api.confirmTranslationLink).toHaveBeenCalledWith(8));
});

test("translation detail loads a paired CL and G-code toolpath", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/translations/3"]}><Routes><Route path="/translations/:exampleId" element={<TranslationDetailPage />} /></Routes></MemoryRouter>);
  await screen.findByText("Pair alignment");
  await user.click(screen.getByRole("button", { name: /toolpath/i }));
  expect(await screen.findByText("TOOLPATH VISUALIZATION ONLY")).toBeInTheDocument();
  expect(api.getTranslationToolpath).toHaveBeenCalledWith(3);
  expect(screen.getByRole("table")).toBeInTheDocument();
  await user.click(screen.getByRole("row", { name: /1 linear/i }));
  expect(screen.getByRole("heading", { name: "Selected relationship" })).toBeInTheDocument();
});

test("guided create flow binds an exact revision and accepts pasted paired sources", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listProfileRevisions).mockResolvedValue([{ id: 2, machine_profile_id: 1, revision_number: 4, status: "approved" }] as never);
  vi.mocked(api.createTranslation).mockResolvedValue(example as never);
  render(<MemoryRouter><TranslationExamplesPage /></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: /Import paired example/ }));
  const form = screen.getByRole("heading", { name: "Import paired translation evidence" }).closest("form") as HTMLFormElement;
  await user.selectOptions(within(form).getByLabelText("Machine"), "1");
  await waitFor(() => expect(within(form).getByLabelText("Machine profile revision")).toHaveValue("2"));
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await user.type(screen.getByLabelText("Paste Creo CL/NCL"), "SPINDL/RPM,1200,CLW");
  await user.type(screen.getByLabelText("Paste historical G-code"), "S1200 M03");
  await user.click(screen.getByRole("button", { name: "Continue" }));
  await user.type(screen.getByLabelText("Example name"), "New controlled pair");
  await user.type(screen.getByLabelText("Source provenance"), "Fictional controlled test archive");
  await user.click(screen.getByRole("button", { name: "Create candidate" }));
  await waitFor(() => expect(api.createTranslation).toHaveBeenCalledWith(expect.objectContaining({ machine_profile_revision_id: 2, verification_status: "candidate", ai_processing_allowed: false, cl_source_text: "SPINDL/RPM,1200,CLW", gcode_source_text: "S1200 M03" })));
});

test("AI retrieval is inspectable and never invokes the provider until requested", async () => {
  const user = userEvent.setup(); vi.mocked(api.listProfileRevisions).mockResolvedValue([{ id: 2, machine_profile_id: 1, revision_number: 4, status: "approved" }] as never);
  render(<MemoryRouter><TranslationExamplesPage /></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: "AI Retrieval Preview" }));
  await user.selectOptions(screen.getByLabelText("Machine"), "1");
  await user.type(screen.getByLabelText("CL segment"), "SPINDL/RPM,1200,CLW");
  await user.click(screen.getByRole("button", { name: "Find Similar Verified Examples" }));
  expect(await screen.findByText(/AI called: No/)).toBeInTheDocument();
  expect(screen.getByText("Fictional spindle pair #3")).toBeInTheDocument();
  expect(api.explainTranslation).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Generate AI Interpretation" }));
  expect(await screen.findByText("S{rpm} M03")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "#3" })).toHaveAttribute("href", "/translations/3");
});

test("AI panel exposes provider boundaries and a loading state for explicit generation", async () => {
  const user = userEvent.setup(); vi.mocked(api.listProfileRevisions).mockResolvedValue([{ id: 2, machine_profile_id: 1, revision_number: 4, status: "approved" }] as never);
  let resolveExplanation!: (value: Awaited<ReturnType<typeof api.explainTranslation>>) => void;
  vi.mocked(api.explainTranslation).mockReturnValue(new Promise((resolve) => { resolveExplanation = resolve; }));
  render(<MemoryRouter><TranslationExamplesPage /></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: "AI Retrieval Preview" }));
  expect(await screen.findByText("mock")).toBeInTheDocument();
  expect(screen.getByText("External Processing").parentElement).toHaveTextContent("Disabled");
  expect(screen.getByText("Public Web").parentElement).toHaveTextContent("Disabled");
  await user.selectOptions(screen.getByLabelText("Machine"), "1");
  await user.type(screen.getByLabelText("CL segment"), "SPINDL/RPM,1200,CLW");
  await user.click(screen.getByRole("button", { name: "Find Similar Verified Examples" }));
  await user.click(await screen.findByRole("button", { name: "Generate AI Interpretation" }));
  expect(screen.getByRole("button", { name: "Generating…" })).toBeDisabled();
  resolveExplanation({ status: "advisory_interpretation", input_cl: "SPINDL/RPM,1200,CLW", interpreted_operation: "clockwise_spindle_start", suggested_mapping_pattern: "S{rpm} M03", short_rationale: "Observed verified pattern.", example_ids: [3], uncertainties: ["Low"], unsupported_features: [], warnings: [], provider_metadata: { provider: "mock" }, invocation_id: 4, advisory_only: true, safety_notice: "R&D ADVISORY INTERPRETATION ONLY" });
  expect(await screen.findByText("S{rpm} M03")).toBeInTheDocument();
});

test.each([
  ["provider failure", "Azure OpenAI request failed."],
  ["policy block", "Every selected example must come from the current verified retrieval result."],
  ["content filter", "Azure content filtering prevented a response."],
])("AI panel renders a safe %s response", async (_label, message) => {
  const user = userEvent.setup(); vi.mocked(api.listProfileRevisions).mockResolvedValue([{ id: 2, machine_profile_id: 1, revision_number: 4, status: "approved" }] as never);
  vi.mocked(api.explainTranslation).mockRejectedValue(new Error(message));
  render(<MemoryRouter><TranslationExamplesPage /></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: "AI Retrieval Preview" }));
  await user.selectOptions(screen.getByLabelText("Machine"), "1");
  await user.type(screen.getByLabelText("CL segment"), "SPINDL/RPM,1200,CLW");
  await user.click(screen.getByRole("button", { name: "Find Similar Verified Examples" }));
  await user.click(await screen.findByRole("button", { name: "Generate AI Interpretation" }));
  expect((await screen.findByText(message)).closest('[role="alert"]')).toHaveTextContent(message);
});

test("AI permission requires an explicit record-level acknowledgement", async () => {
  const user = userEvent.setup(); render(<MemoryRouter initialEntries={["/translations/3"]}><Routes><Route path="/translations/:exampleId" element={<TranslationDetailPage />} /></Routes></MemoryRouter>);
  await screen.findByText("AI Processing Permission");
  await user.type(screen.getByLabelText("Reviewer label"), "Reviewer");
  await user.click(screen.getByLabelText(/explicitly allow eligible excerpts/i));
  await user.click(screen.getByRole("button", { name: "Enable AI Processing" }));
  await waitFor(() => expect(api.setTranslationAIConsent).toHaveBeenCalledWith(3, true, "Reviewer", true));
});
