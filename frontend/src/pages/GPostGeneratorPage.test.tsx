import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { Layout } from "../components/Layout";
import { GPostGeneratorPage } from "./GPostGeneratorPage";
import { GPostWorkspacePage } from "./GPostWorkspacePage";

vi.mock("../api/client", () => ({ api: {
  listProfiles: vi.fn(), listProfileRevisions: vi.fn(), listDocuments: vi.fn(),
  listReferencePrograms: vi.fn(), listStandards: vi.fn(), listGPostDrafts: vi.fn(),
  listGPostMappings: vi.fn(), createGPostDraft: vi.fn(), getGPostDraft: vi.fn(),
  updateGPostDraft: vi.fn(), updateGPostMapping: vi.fn(), preflightGPost: vi.fn(), previewGPost: vi.fn(),
  createGPostVersion: vi.fn(), compareGPostVersions: vi.fn(), archiveGPostDraft: vi.fn(),
  getAssembledPost: vi.fn(), duplicateGPostDraft: vi.fn(), deleteGPostDraft: vi.fn(),
  getGPostHistoricalTranslationEvidence: vi.fn(),
  getGPostPreviewToolpath: vi.fn(),
  getTranslationAIProviderStatus: vi.fn(), retrieveTranslationExamples: vi.fn(), explainTranslation: vi.fn(),
  getPostRecordSummary: vi.fn(), listSiteStandards: vi.fn(),
  getDocumentContent: vi.fn(), gpostExportUrl: vi.fn((id, format) => `/export-${id}.${format}`),
  postDevelopmentPackageUrl: vi.fn((id, format) => `/package-${id}.${format}`),
} }));

const machine = {
  id: 1, name: "KENT KLS-1840N", manufacturer: "KENT", model: "KLS-1840N",
  controller_name: "FANUC", controller_manufacturer: "FANUC",
  controller_model: "0i-Mate TF", controller_version: "1", machine_type: "lathe",
  axis_count: 2, x_min: -20, x_max: 20, y_min: null, y_max: null,
  z_min: -40, z_max: 5, max_spindle_rpm: 3000, max_feed_rate: 200,
  rapid_z_review_threshold: 0, supported_work_offsets: ["G54"],
  approved_g_codes: ["G00", "G01", "G18"], approved_m_codes: ["M03", "M30"],
  restricted_commands: [], safe_start_template: "G18 G40 G80 G99",
  tool_change_template: "T{tool:04d}", program_end_template: "M30", notes: null,
  active_revision_id: 2, archived_at: null, created_at: "2026-08-01", updated_at: "2026-08-11",
};
const revision = {
  id: 2, machine_profile_id: 1, revision_number: 4, status: "approved",
  source_type: "manual_entry", name: machine.name, manufacturer: machine.manufacturer,
  model: machine.model, controller_name: machine.controller_name,
  controller_manufacturer: "FANUC", controller_model: "0i-Mate TF", controller_version: "1",
  machine_type: "lathe", axis_count: 2, x_min: -20, x_max: 20, y_min: null, y_max: null,
  z_min: -40, z_max: 5, max_spindle_rpm: 3000, max_feed_rate: 200,
  rapid_traverse_rate: null, supported_work_offsets_json: ["G54"],
  approved_g_codes_json: ["G00", "G01", "G18"], approved_m_codes_json: ["M03", "M30"],
  restricted_commands_json: [], safe_start_template: "G18 G40 G80 G99",
  tool_change_template: "T{tool:04d}", program_end_template: "M30",
  capabilities_json: { unresolved_fields: ["turret_behavior"] },
  machine_configuration_json: {}, review_summary: null, approved_at: "2026-08-01",
};
const document = {
  id: 3, machine_profile_id: 1, title: "FANUC 0i-Mate TF Programming Manual",
  document_type: "controller_manual", original_filename: "manual.pdf",
  mime_type: "application/pdf", file_size_bytes: 1, file_hash: "a",
  processing_status: "ready", processing_error: null, page_count: 342,
  uploaded_at: "2026-08-01", processed_at: "2026-08-01", ai_post_builder_allowed: true,
};
const reference = {
  id: 7, machine_profile_id: 1, machine_profile_revision_id: 2,
  source_document_id: null, name: "Approved KLS turning example", description: null,
  original_filename: "approved.nc", file_hash: "a".repeat(64), program_number: "1001",
  program_type: "turning", controller_name: "FANUC", controller_version: "1",
  controller_variant: null, post_processor_name: "Creo", post_processor_version: null,
  post_processor_revision: "POST-3", part_identifier: null, operation_identifier: null,
  material: null, units: "inch", machine_variant: null, installed_options_json: [],
  approval_status: "approved_reference", eligibility_status: "eligible",
  eligibility_reason: "Reviewed", approved_by_label: "QA", parsing_status: "parsed",
  parser_version: "gcode-parser-v1", rule_set_version: "validation-v1",
  validation_summary_json: { blocking_count: 0 }, source_integrity_json: {},
  ai_processing_allowed: false, imported_at: "2026-08-01", updated_at: "2026-08-01",
  advisory_only: true, historical_similarity_is_not_certification: true, safety_notice: "R&D",
};
const draft = {
  id: 4, machine_profile_id: 1, machine_profile_revision_id: 2,
  created_from_draft_id: null, name: "KLS-1840N FANUC Post", version: 3,
  status: "review_required", controller_family: "fanuc_lathe", machine_type: "lathe",
  selected_document_ids_json: [3], standard_profile_id: null,
  reference_program_ids_json: [7], manual_configuration_acknowledged: false, capability_snapshot_json: {
    axis_count: 2, configured_axes: ["X", "Z"], spindle_limits: { max: 3000 },
    feed_limit: 200, work_offsets: ["G54"], restricted_commands: [],
  }, machine_profile_snapshot_json: {}, templates_json: {
    program_header: "%", safe_start: "G18 G40 G80 G99", program_end: "M30",
    footer: "%", rapid_move: "G00 {coordinates}", linear_feed_move: "G01 {coordinates}{feed}",
    arc_cw: "", arc_ccw: "", plane_selection: "G18", tool_selection: "T{tool:04d}",
    tool_change: "T{tool:04d}", spindle_start_cw: "S{rpm:g} M03",
    spindle_start_ccw: "S{rpm:g} M04", spindle_stop: "M05", coolant_on: "M08",
    coolant_off: "M09", units: "G20", distance_mode: "G90", work_offset: "G54",
    reference_return: "G28", canned_cycle: "", cycle_cancel: "G80",
  }, unsupported_features_json: ["MULTAX"], warnings_json: [{ category: "Missing Documentation", message: "Turret behavior not confirmed" }],
  review_summary_json: { pending: 1 }, created_at: "2026-08-01", updated_at: "2026-08-11",
  superseded_at: null, advisory_only: true, safety_notice: "R&D ONLY",
};
const mappings = [{
  id: 5, gpost_draft_id: 4, mapping_key: "loadtl", cl_command: "LOADTL",
  mapping_type: "stateful", output_template: "T{tool:04d}", conditions_json: {},
  required_state_json: {}, resulting_state_json: { active_tool: "{tool}" },
  machine_type_scope: "lathe", dialect_scope: "fanuc_lathe", supported: true,
  confidence: .9, source_type: "document", source_document_id: 3,
  source_chunk_id: 8, source_page: 84, source_section: "Tool Commands",
  source_excerpt: "T codes select a turret station.", source_authority: "controller manufacturer",
  review_status: "pending", review_note: null, evidence: [], created_at: "", updated_at: "",
}, {
  id: 6, gpost_draft_id: 4, mapping_key: "spindl", cl_command: "SPINDL",
  mapping_type: "conditional", output_template: "S{rpm:g} M03", conditions_json: {},
  required_state_json: {}, resulting_state_json: {}, machine_type_scope: "lathe",
  dialect_scope: "fanuc_lathe", supported: true, confidence: .85,
  source_type: "document", source_document_id: 3, source_chunk_id: 9,
  source_page: 92, source_section: "Spindle", source_excerpt: "M03 starts clockwise rotation.",
  source_authority: "controller manufacturer", review_status: "pending", review_note: null,
  evidence: [], created_at: "", updated_at: "",
}, {
  id: 8, gpost_draft_id: 4, mapping_key: "multax", cl_command: "MULTAX",
  mapping_type: "unsupported", output_template: null, conditions_json: {},
  required_state_json: {}, resulting_state_json: {}, machine_type_scope: "lathe",
  dialect_scope: "fanuc_lathe", supported: false, confidence: null,
  source_type: "capability_registry", source_document_id: null, source_chunk_id: null,
  source_page: null, source_section: null, source_excerpt: null, source_authority: null,
  review_status: "deferred", review_note: "2-axis machine", evidence: [], created_at: "", updated_at: "",
}].map((item) => ({
  template_key: item.mapping_key === "loadtl" ? "tool_change" : item.mapping_key === "spindl" ? "spindle_start_cw" : null,
  template_override: null, uses_override: false,
  effective_output_template: item.output_template,
  support_status: item.supported ? "supported" as const : item.cl_command === "MULTAX" ? "not_applicable" as const : "not_implemented" as const,
  required_for_v1: item.supported && ["LOADTL", "SPINDL"].includes(item.cl_command),
  description: item.cl_command === "LOADTL" ? "Tool selection / load" : item.cl_command === "SPINDL" ? "Clockwise spindle start" : "Multiaxis mode",
  ...item,
}));
const preview = {
  id: 9, gpost_draft_id: 4, status: "blocked", generated_gcode: "G20\nG18 G40 G80 G99\nT0101\nS1200 M03\nM30",
  parser_diagnostics_json: [], deterministic_findings_json: [{ title: "Command review", description: "G99 requires review", category: "commands", rule_id: "UNAPPROVED_COMMAND", severity: "warning" }],
  unsupported_commands_json: [{ command: "MULTAX", reason: "2-axis machine" }],
  missing_mappings_json: [], warnings_json: [], traceability_json: [{
    source_cl_line: 1, cl_command: "LOADTL", source_cl_text: "LOADTL/1",
    mapping_id: 5, mapping_version: 3, template_used: "T{tool:04d}", generated_gcode: "T0101",
    state_before: {}, state_after: { active_tool: 1 }, source_evidence: { document_id: 3 },
  }], summary_json: { generated_block_count: 1, traceability_coverage: 100 },
  parser_version: "gcode-parser-v1", rule_set_version: "validation-v1", created_at: "",
  safety_notice: "R&D ONLY",
};

function LocationProbe() { const location = useLocation(); return <output aria-label="location">{location.search}</output>; }

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listProfiles).mockResolvedValue([machine] as never);
  vi.mocked(api.listProfileRevisions).mockResolvedValue([revision] as never);
  vi.mocked(api.listDocuments).mockResolvedValue([document] as never);
  vi.mocked(api.listReferencePrograms).mockResolvedValue([reference] as never);
  vi.mocked(api.listStandards).mockResolvedValue([] as never);
  vi.mocked(api.listGPostDrafts).mockResolvedValue([draft] as never);
  vi.mocked(api.listSiteStandards).mockResolvedValue([] as never);
  vi.mocked(api.getPostRecordSummary).mockRejectedValue(new Error("not used by legacy test fixture"));
  vi.mocked(api.listGPostMappings).mockResolvedValue(mappings as never);
  vi.mocked(api.getGPostDraft).mockResolvedValue(draft as never);
  vi.mocked(api.updateGPostDraft).mockImplementation(async (_id, payload) => ({ ...draft, ...payload, selected_document_ids_json: payload.selected_document_ids ?? draft.selected_document_ids_json }) as never);
  vi.mocked(api.updateGPostMapping).mockImplementation(async (_id, payload) => ({ ...mappings[0], ...payload }) as never);
  vi.mocked(api.previewGPost).mockResolvedValue(preview as never);
  vi.mocked(api.preflightGPost).mockResolvedValue({ machine_ready: true, post_context_ready: true, cl_parse_status: "parsed", cl_record_count: 10, required_behavior_keys: ["loadtl", "spindl_cw", "fedrat", "coolnt_on", "rapid", "goto", "coolnt_off", "spindl_off", "fini"], supported_behavior_keys: ["loadtl", "spindl_cw", "fedrat", "coolnt_on", "rapid", "goto", "coolnt_off", "spindl_off", "fini"], reviewed_behavior_keys: ["loadtl"], unreviewed_behavior_keys: ["spindl_cw"], unsupported_required_behaviors: [], blocking_issues: [], warnings: [{ code: "GPOST_UNREVIEWED_CURRENT_CL", message: "1 supported behavior has not been manually reviewed." }], generation_allowed: true, generation_allowed_with_warning: true } as never);
  vi.mocked(api.getDocumentContent).mockResolvedValue({ document, pages: [{ page_number: 84, text: "T codes select a turret station.", character_count: 32 }], extracted_text: "T codes select a turret station.", chunks: [] } as never);
  vi.mocked(api.createGPostDraft).mockResolvedValue(draft as never);
  vi.mocked(api.getAssembledPost).mockResolvedValue({ draft_id: 4, name: draft.name, status: "building", required_area_count: 8, counts: { reviewed: 0, needs_review: 1, needs_information: 0, not_started: 7, deferred: 1 }, components: [], ready_for_complete_review: false, advisory_only: true, native_gpost_export: "not_configured" } as never);
  vi.mocked(api.duplicateGPostDraft).mockResolvedValue({ ...draft, id: 12, name: `${draft.name} Copy`, version: 1 } as never);
  vi.mocked(api.deleteGPostDraft).mockResolvedValue(undefined);
  vi.mocked(api.archiveGPostDraft).mockResolvedValue({ ...draft, status: "archived" } as never);
  vi.mocked(api.getGPostHistoricalTranslationEvidence).mockResolvedValue({ mapping_id: 5, machine_profile_id: 1, cl_command: "LOADTL", verified_example_count: 2, observations: [], read_only: true, mapping_changed: false } as never);
  vi.mocked(api.getGPostPreviewToolpath).mockResolvedValue({ source: "both", machine_type: "lathe", default_view: "XZ", coordinate_context: "work", bounds: { min_x: 0, max_x: 1, min_y: 0, max_y: 0, min_z: 0, max_z: 1 }, summary: { segments: 1, rapid: 0, feed: 1, arcs: 0, tools: 1, operations: 0, unresolved_geometry: 0, visualization_simplified: false }, warnings: [], comparison_summary: null, advisory_only: true, safety_notice: "TOOLPATH VISUALIZATION ONLY", segments: [{ id: "gcode-1", source_type: "gcode", source_record_id: 1, source_line_start: 3, source_line_end: 3, operation_id: null, tool_number: 1, motion_type: "linear", start_point: { x: 0, y: 0, z: 0 }, end_point: { x: 1, y: 0, z: 1 }, center_point: null, radius: null, path_points: [], plane: "G18", feed_rate: null, spindle_speed: 1200, rapid: false, arc_direction: null, helical: false, tool_axis: null, alignment_link_id: null, aligned_segment_ids: [], finding_ids: [], sequence_index: 0, visualizable: true, unmatched: false, geometry_status: null, metadata_json: {} }] } as never);
  vi.mocked(api.getTranslationAIProviderStatus).mockResolvedValue({ provider: "mock", configured: true, reachable: true, authentication_mode: "none", deployment: "fixture", model: "mock", external_processing: false, public_web: false, data_source: "Verified Internal Translation Examples Only", mode: "R&D", error_code: null });
});

test("primary navigation uses the Post Builder identity", () => {
  render(<MemoryRouter><Routes><Route element={<Layout />}><Route index element={<div>Home</div>} /></Route></Routes></MemoryRouter>);
  expect(screen.getByRole("link", { name: /Post Builder/ })).toHaveAttribute("href", "/gpost");
  expect(screen.getAllByRole("link")).toHaveLength(5);
  expect(screen.queryByText("Post Processor Lab")).not.toBeInTheDocument();
});

test("landing page shows one-post management controls instead of the CL test harness", async () => {
  render(<MemoryRouter><GPostGeneratorPage /></MemoryRouter>);
  expect(await screen.findByText("KLS-1840N FANUC Post")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Post filters" })).toBeInTheDocument();
  expect(screen.getByLabelText("Search")).toBeInTheDocument();
  expect(screen.getByLabelText("Machine")).toBeInTheDocument();
  expect(screen.getAllByText("Needs Information").length).toBeGreaterThan(0);
  expect(screen.queryByLabelText("CL / NCL Input")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("href", "/gpost/4");
  expect(screen.getByRole("button", { name: `More actions for ${draft.name}` })).toBeInTheDocument();
});

test("landing page provides the specified empty state", async () => {
  vi.mocked(api.listGPostDrafts).mockResolvedValue([] as never);
  render(<MemoryRouter><GPostGeneratorPage /></MemoryRouter>);
  expect(await screen.findByText("No Post Records yet.")).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Create Post" }).length).toBeGreaterThan(0);
});

test("guided creation auto-selects a compatible foundation and omits reference programs", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost"]}><Routes><Route path="/gpost" element={<GPostGeneratorPage />} /><Route path="/gpost/:draftId" element={<div>Created workspace</div>} /></Routes></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: "Create Post" }));
  expect(await screen.findByText("Select Machine", { selector: "h1" })).toBeInTheDocument();
  expect(screen.queryByText("Reference Programs")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select" }));
  expect(screen.getByText("Review Post Inputs", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByText("FANUC Lathe")).toBeInTheDocument();
  expect(screen.getByText("Machine Information")).toBeInTheDocument();
  expect(screen.getByText("1 available")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Continue" }));
  expect(screen.getByText("FANUC Lathe")).toBeInTheDocument();
  expect(screen.queryByText(/Revision v/)).not.toBeInTheDocument();
  expect(screen.queryByRole("combobox", { name: /Template Family/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Create Post" }));
  expect(await screen.findByText("Created workspace")).toBeInTheDocument();
  expect(api.createGPostDraft).toHaveBeenCalledWith(1, expect.objectContaining({ machine_profile_revision_id: 2, controller_family: "fanuc_lathe", selected_document_ids: [3], reference_program_ids: [] }));
});

test("machine query preselects the machine in Post creation", async () => {
  render(<MemoryRouter initialEntries={["/gpost?machine=1"]}><Routes><Route path="/gpost" element={<GPostGeneratorPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Review Post Inputs", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByText(machine.name)).toBeInTheDocument();
  expect(screen.getByText("FANUC Lathe")).toBeInTheDocument();
});

test("post list search, filters, archive, rename, and delete are explicit", async () => {
  const user = userEvent.setup(); render(<MemoryRouter><GPostGeneratorPage /></MemoryRouter>);
  await screen.findByText(draft.name);
  await user.type(screen.getByLabelText("Search"), "missing");
  expect(screen.getByText("No Post Records yet.")).toBeInTheDocument();
  await user.clear(screen.getByLabelText("Search")); await user.selectOptions(screen.getByLabelText("Machine"), "1");
  await user.click(screen.getByRole("button", { name: `More actions for ${draft.name}` })); await user.click(screen.getByRole("menuitem", { name: "Rename" }));
  const input = screen.getByLabelText("Post Name"); await user.clear(input); await user.type(input, "Renamed Post"); await user.click(screen.getByRole("button", { name: "Save Name" }));
  await waitFor(() => expect(api.updateGPostDraft).toHaveBeenCalledWith(4, { name: "Renamed Post" }));
});

test("workspace overview, sources, and configuration progressively disclose context", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4"]}><Routes><Route path="/gpost/:draftId/*" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("KLS-1840N FANUC Post", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "KLS-1840N FANUC Post" })).toHaveClass("gpost-draft-title");
  expect(screen.getByText("G-POST v3")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Advanced Post Configuration" })).toBeInTheDocument();
  expect(screen.getAllByLabelText("Status: Needs Configuration").length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "Generate R&D Draft" })).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Evidence" }));
  expect(screen.getByText("FANUC 0i-Mate TF Programming Manual")).toBeInTheDocument();
  expect(screen.getByText("342 pages")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Category" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Actions" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Exclude" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Advanced Post Configuration" }));
  await user.click(screen.getByRole("menuitem", { name: "Templates" }));
  expect(screen.getByRole("heading", { name: "Shared Output Templates" })).toBeInTheDocument();
  expect(screen.getByText("Program Structure")).toBeInTheDocument();
  expect(screen.getByText("Motion")).toBeInTheDocument();
  expect(screen.getAllByText(/Used by:/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/\{"/)).not.toBeInTheDocument();
});

test("mapping filters, acceptance, auto-advance, and source drawer preserve URL state", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4?tab=mappings&queue=needs-review&mapping=loadtl"]}><Routes><Route path="/gpost/:draftId" element={<><GPostWorkspacePage /><LocationProbe /></>} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Selected Mapping")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Tool Selection" })).toBeInTheDocument();
  expect(screen.getAllByText("Tool selection / load").length).toBeGreaterThan(0);
  expect(await screen.findByRole("heading", { name: "Historical Translation Evidence" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Legacy translation-AI experiment disabled" })).toBeInTheDocument();
  expect(api.explainTranslation).not.toHaveBeenCalled();
  expect(screen.getByText("2 verified examples")).toBeInTheDocument();
  expect(screen.getByText("Evidence does not automatically change this mapping.")).toBeInTheDocument();
  expect(screen.getByText(/Configuration → Tooling → tool change/)).toBeInTheDocument();
  await user.click(screen.getByText("FANUC 0i-Mate TF Programming Manual"));
  expect(await screen.findByRole("dialog", { name: "G-POST mapping source" })).toBeInTheDocument();
  expect(screen.getByText("T codes select a turret station.", { selector: "p" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Close source viewer" }));
  expect(screen.getByLabelText("location")).toHaveTextContent("tab=mappings");
  expect(screen.getByLabelText("location")).toHaveTextContent("queue=needs-review");
  await user.click(screen.getByRole("button", { name: "Accept" }));
  const toast = (await screen.findByText("LOADTL marked accepted.")).closest(".gpost-toast") as HTMLElement;
  expect(toast).not.toBeNull();
  expect(toast).toHaveTextContent("LOADTL marked accepted.");
  expect(toast.closest(".gpost-header-actions")).toBeNull();
  expect(screen.getByRole("button", { name: "Dismiss notification" })).toBeInTheDocument();
  expect(api.updateGPostMapping).toHaveBeenCalledWith(5, expect.objectContaining({ review_status: "accepted" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Spindle — Clockwise Start" })).toBeInTheDocument());
  expect(screen.getByLabelText("location")).toHaveTextContent("mapping=spindl");
});

test("Generate preserves its preview across distinct Results and Toolpath routes", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4"]}><Routes><Route path="/gpost/:draftId/*" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { level: 2, name: "Test G-POST Draft" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Preflight" })).toBeInTheDocument();
  expect(screen.getAllByText("Fanuc Lathe").length).toBeGreaterThan(0);
  expect(screen.getByLabelText("Upload CL File")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Generate Preview" }));
  expect(await screen.findByLabelText("Generated Code")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 3, name: "Generated Code" })).toBeInTheDocument();
  expect(screen.getAllByText("T0101").length).toBeGreaterThan(0);
  await user.click(screen.getByRole("link", { name: "Results" }));
  expect(screen.getByRole("heading", { name: "Generation Blocked" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Test G-POST Draft" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Toolpath" }));
  expect(await screen.findByText("TOOLPATH VISUALIZATION ONLY")).toBeInTheDocument();
  expect(api.getGPostPreviewToolpath).toHaveBeenCalledWith(9);
});

test("version workspace exposes history and technical comparison", async () => {
  const user = userEvent.setup();
  const older = { ...draft, id: 10, version: 2, status: "superseded", created_from_draft_id: 4 };
  vi.mocked(api.listGPostDrafts).mockResolvedValue([draft, older] as never);
  vi.mocked(api.compareGPostVersions).mockResolvedValue({ left_draft_id: 4, right_draft_id: 10, mappings_added: [], mappings_removed: [], templates_changed: ["loadtl"], conditions_changed: [], evidence_changed: [], warnings_added: [], warnings_resolved: [] } as never);
  render(<MemoryRouter initialEntries={["/gpost/4?tab=versions"]}><Routes><Route path="/gpost/:draftId" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Version History")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Compare version"), "10");
  await user.click(screen.getByRole("button", { name: "Compare" }));
  expect(await screen.findByText("loadtl")).toBeInTheDocument();
});

test.each([
  ["/gpost/4/toolpath", "No generated toolpath yet", "Toolpath"],
  ["/gpost/4/results", "No R&D result yet", "Results"],
  ["/gpost/4/evidence", "Machine Profile", "Evidence"],
])("direct G-POST route %s renders its distinct workspace", async (path, expected, activeLabel) => {
  render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/gpost/:draftId/*" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText(expected)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: activeLabel })).toHaveAttribute("aria-current", "page");
  if (activeLabel !== "Generate") expect(screen.queryByRole("heading", { name: "Test G-POST Draft" })).not.toBeInTheDocument();
});
