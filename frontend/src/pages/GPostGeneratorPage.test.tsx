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
  updateGPostDraft: vi.fn(), updateGPostMapping: vi.fn(), previewGPost: vi.fn(),
  createGPostVersion: vi.fn(), compareGPostVersions: vi.fn(), archiveGPostDraft: vi.fn(),
  getDocumentContent: vi.fn(), gpostExportUrl: vi.fn((id, format) => `/export-${id}.${format}`),
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
  uploaded_at: "2026-08-01", processed_at: "2026-08-01",
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
  reference_program_ids_json: [7], capability_snapshot_json: {
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
}];
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
  vi.mocked(api.listGPostMappings).mockResolvedValue(mappings as never);
  vi.mocked(api.getGPostDraft).mockResolvedValue(draft as never);
  vi.mocked(api.updateGPostDraft).mockImplementation(async (_id, payload) => ({ ...draft, ...payload, selected_document_ids_json: payload.selected_document_ids ?? draft.selected_document_ids_json }) as never);
  vi.mocked(api.updateGPostMapping).mockImplementation(async (_id, payload) => ({ ...mappings[0], ...payload }) as never);
  vi.mocked(api.previewGPost).mockResolvedValue(preview as never);
  vi.mocked(api.getDocumentContent).mockResolvedValue({ document, pages: [{ page_number: 84, text: "T codes select a turret station.", character_count: 32 }], extracted_text: "T codes select a turret station.", chunks: [] } as never);
  vi.mocked(api.createGPostDraft).mockResolvedValue(draft as never);
});

test("primary navigation uses the G-POST Generator identity", () => {
  render(<MemoryRouter><Routes><Route element={<Layout />}><Route index element={<div>Home</div>} /></Route></Routes></MemoryRouter>);
  expect(screen.getByRole("link", { name: /G-POST Generator/ })).toHaveAttribute("href", "/gpost");
  expect(screen.queryByText("Post Processor Lab")).not.toBeInTheDocument();
});

test("landing page shows existing drafts instead of the CL test harness", async () => {
  render(<MemoryRouter><GPostGeneratorPage /></MemoryRouter>);
  expect(await screen.findByText("KLS-1840N FANUC Post")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Mappings" })).toBeInTheDocument();
  expect(screen.getByText("Under Review")).toBeInTheDocument();
  expect(screen.queryByLabelText("CL / NCL Input")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Open/ })).toHaveAttribute("href", "/gpost/4");
});

test("landing page provides the specified empty state", async () => {
  vi.mocked(api.listGPostDrafts).mockResolvedValue([] as never);
  render(<MemoryRouter><GPostGeneratorPage /></MemoryRouter>);
  expect(await screen.findByText("No G-POST configurations yet")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Create G-POST" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View Machine Profiles" })).toHaveAttribute("href", "/machines");
});

test("guided creation presents machine context, readiness, and draft identity", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost"]}><Routes><Route path="/gpost" element={<GPostGeneratorPage />} /><Route path="/gpost/:draftId" element={<div>Created workspace</div>} /></Routes></MemoryRouter>);
  await user.click(await screen.findByRole("button", { name: /Create G-POST/ }));
  expect(await screen.findByText("Select Machine", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByText("Profile coverage")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Select" }));
  expect(screen.getByText("G-POST Readiness", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByText("✓ 1 reference documents")).toBeInTheDocument();
  expect(screen.getByText("⚠ 1 machine profile fields unresolved")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Continue Setup" }));
  expect(screen.getByDisplayValue("KLS-1840N 0i-Mate TF Post")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Create Draft" }));
  expect(await screen.findByText("Created workspace")).toBeInTheDocument();
  expect(api.createGPostDraft).toHaveBeenCalledWith(1, expect.objectContaining({ machine_profile_revision_id: 2, controller_family: "fanuc_lathe", selected_document_ids: [3] }));
});

test("workspace overview, sources, and configuration progressively disclose context", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4"]}><Routes><Route path="/gpost/:draftId" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("KLS-1840N FANUC Post", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 1, name: "KLS-1840N FANUC Post" })).toHaveClass("gpost-draft-title");
  expect(screen.getByText("G-POST v3")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "overview" })).toHaveAttribute("aria-current", "page");
  expect(screen.getAllByLabelText("Status: Under Review").length).toBeGreaterThan(0);
  expect(screen.getByText("Machine Configuration")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "sources" }));
  expect(screen.getByText("FANUC 0i-Mate TF Programming Manual")).toBeInTheDocument();
  expect(screen.getByText("342 pages")).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Category" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Actions" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Exclude" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "configuration" }));
  expect(screen.getByText("Program Structure")).toBeInTheDocument();
  expect(screen.getByText("Motion")).toBeInTheDocument();
  expect(screen.queryByText(/\{"/)).not.toBeInTheDocument();
});

test("mapping filters, acceptance, auto-advance, and source drawer preserve URL state", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4?tab=mappings&queue=needs-review&mapping=loadtl"]}><Routes><Route path="/gpost/:draftId" element={<><GPostWorkspacePage /><LocationProbe /></>} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Selected Mapping")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "LOADTL" })).toBeInTheDocument();
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
  await waitFor(() => expect(screen.getByRole("heading", { name: "SPINDL" })).toBeInTheDocument());
  expect(screen.getByLabelText("location")).toHaveTextContent("mapping=spindl");
});

test("Test tab generates a line-numbered preview, CL trace, validation, warnings, and reference diff", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/gpost/4?tab=test"]}><Routes><Route path="/gpost/:draftId" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { level: 2, name: "Test G-POST Draft" })).toBeInTheDocument();
  expect(screen.getByLabelText("Upload CL File")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Generate Preview" }));
  expect(await screen.findByLabelText("Generated Code")).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 3, name: "Generated Code" })).toBeInTheDocument();
  expect(screen.getAllByText("T0101").length).toBeGreaterThan(0);
  await user.click(screen.getByRole("button", { name: "cl trace" }));
  expect(screen.getByRole("columnheader", { name: "CL Line" })).toBeInTheDocument();
  expect(screen.getByText("Trace rationale")).toBeInTheDocument();
  await user.click(screen.getAllByRole("button", { name: "validation" })[1]);
  expect(screen.getByText("Supported Commands")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "warnings" }));
  expect(screen.getByText("2-axis machine")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "reference diff" }));
  expect(screen.getByText("Approved KLS turning example")).toBeInTheDocument();
});

test("version workspace exposes history and technical comparison", async () => {
  const user = userEvent.setup();
  const older = { ...draft, id: 10, version: 2, status: "superseded" };
  vi.mocked(api.listGPostDrafts).mockResolvedValue([draft, older] as never);
  vi.mocked(api.compareGPostVersions).mockResolvedValue({ left_draft_id: 4, right_draft_id: 10, mappings_added: [], mappings_removed: [], templates_changed: ["loadtl"], conditions_changed: [], evidence_changed: [], warnings_added: [], warnings_resolved: [] } as never);
  render(<MemoryRouter initialEntries={["/gpost/4?tab=versions"]}><Routes><Route path="/gpost/:draftId" element={<GPostWorkspacePage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Version History")).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Compare version"), "10");
  await user.click(screen.getByRole("button", { name: "Compare" }));
  expect(await screen.findByText("loadtl")).toBeInTheDocument();
});
