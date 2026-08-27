import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { PostRecordWorkspacePage } from "./PostRecordWorkspacePage";

vi.mock("../api/client", () => ({ api: {
  getGPostDraft: vi.fn(), listProfiles: vi.fn(), getPostRecordSummary: vi.fn(), listMachineKnowledge: vi.fn(),
  listOFGSettings: vi.fn(), listSiteStandards: vi.fn(), listPostStandards: vi.fn(), listCustomLogic: vi.fn(),
  listPostQuestions: vi.fn(), listPostValidations: vi.fn(), listGPostVersions: vi.fn(), listDocuments: vi.fn(),
  listValidationFindings: vi.fn(), listGPostDiagnostics: vi.fn(), getValidationPolicy: vi.fn(), getValidationTimeline: vi.fn(), getValidationHandoff: vi.fn(),
  updateMachineKnowledge: vi.fn(), updateOFGSetting: vi.fn(), createSiteStandard: vi.fn(), applySiteStandard: vi.fn(),
  updatePostStandard: vi.fn(), createCustomLogic: vi.fn(), createPostQuestion: vi.fn(), updatePostQuestion: vi.fn(),
  createPostValidation: vi.fn(), createGPostVersion: vi.fn(), updateGPostDraft: vi.fn(), archiveGPostDraft: vi.fn(),
  parseGPostDiagnostics: vi.fn(), updateValidationFinding: vi.fn(), findingToOpenQuestion: vi.fn(),
  deleteGPostDraft: vi.fn(), postDevelopmentPackageUrl: vi.fn((id, format) => `/package/${id}.${format}`),
} }));

const draft = { id: 4, machine_profile_id: 1, machine_profile_revision_id: 2, created_from_draft_id: null, name: "KLS-1840N FANUC Post", version: 1, status: "review_required", controller_family: "fanuc_lathe", machine_type: "lathe", selected_document_ids_json: [3], standard_profile_id: null, reference_program_ids_json: [], manual_configuration_acknowledged: false, capability_snapshot_json: {}, machine_profile_snapshot_json: {}, templates_json: {}, unsupported_features_json: [], warnings_json: [], review_summary_json: {}, created_at: "2026-08-18", updated_at: "2026-08-19", superseded_at: null, advisory_only: true, safety_notice: "R&D" };
const machine = { id: 1, name: "KENT KLS-1840N", manufacturer: "KENT", model: "KLS-1840N", machine_type: "lathe", axis_count: 2, controller_name: "FANUC", controller_model: null };
const fact = { id: 10, post_record_id: 4, category: "Spindle", fact_key: "max_spindle_rpm", name: "Maximum Spindle RPM", value_json: 2000, unit: "RPM", status: "confirmed", source_document_id: 3, source_label: "KLS Machine Specification", source_location: "p. 4", reviewer: "Mariah", reviewed_at: "2026-08-19", review_note: null, created_at: "2026-08-18", updated_at: "2026-08-19", used_by: [{ type: "ofg_setting", id: 20, label: "Maximum Spindle Speed" }] };
const proposedFact = { ...fact, id: 11, fact_key: "g74_behavior", name: "G74 Behavior", value_json: "Requires review", unit: null, status: "needs_review", reviewed_at: null, used_by: [] };
const setting = { id: 20, post_record_id: 4, category: "Spindle", subsection: "Direct RPM", setting_key: "maximum_spindle_speed", display_name: "Maximum Spindle Speed", description: "Records the reviewed maximum spindle speed.", value_json: 2000, unit: "RPM", status: "needs_review", source_machine_fact_ids_json: [10], source_document_evidence_ids_json: [], site_standard_ids_json: [30], requires_custom_logic: false, custom_logic_id: null, ofg_menu_path: "Spindle → Direct RPM", ofg_menu_path_status: "verified_from_reference", relevance_class: "core", relevance_label: "required_for_post", is_applicable: true, user_selected: false, source_type: "Machine Knowledge", source_reference: null, structured_value_json: null, code_status: null, reviewer: null, review_note: null, reviewed_at: null, created_at: "2026-08-18", updated_at: "2026-08-19", source_machine_facts: [{ id: 10, name: fact.name, value: 2000, status: "confirmed", source: fact.source_label, source_location: fact.source_location }] };
const standard = { id: 30, name: "Tool Change Safe Retract", description: null, scope: "controller_family", applicable_machine_types_json: ["lathe"], applicable_controller_families_json: ["fanuc_lathe"], applicable_machine_ids_json: [], category: "Tooling", rule: "Retract before turret index.", source: "Site SOP", status: "reviewed", reviewer: "Engineer", version: 1, effective_date: null, notes: null, created_at: "2026-08-18", updated_at: "2026-08-19" };
const application = { id: 31, post_record_id: 4, site_standard_id: 30, status: "applied", conflict_status: "requires_review", conflict_note: "Manual conflicts with site standard.", reviewer: null, review_note: null, created_at: "2026-08-18", updated_at: "2026-08-19", standard };
const logic = { id: 40, post_record_id: 4, name: "G74 Grooving Output", category: "Cycles", reason: "Standard OFG configuration does not represent required behavior.", implementation_type: "FIL / CIMFIL", status: "needs_draft", evidence_ids_json: [8], site_standard_ids_json: [30], source_format: "Site verification required", source_reference: null, reviewer: null, review_note: null, created_at: "2026-08-18", updated_at: "2026-08-19" };
const question = { id: 50, post_record_id: 4, question_type: "machine_knowledge", title: "Controller option unclear", description: null, severity: "blocking", related_type: "ofg_setting", related_id: 20, source_context: "Manual p.210", owner: "NC Programmer", status: "open", resolution: null, created_at: "2026-08-18", updated_at: "2026-08-19" };
const validation = { id: 60, post_record_id: 4, post_version_id: null, validation_type: "Configuration Review", performed_by: "NC Engineer", performed_at: "2026-08-19", environment: "Local G-POST", result: "passed_with_findings", notes: null, references_json: [], ai_used: false, created_at: "2026-08-19" };
const summary = { post_record_id: 4, status: "needs_information", machine_knowledge: { reviewed: 18, total: 20 }, ofg_configuration: { reviewed: 32, total: 45 }, site_standards: { applied: 1, total: 1, conflicts: 1 }, custom_logic: { identified: 1, reviewed: 0 }, open_questions: { open: 1, total: 1 }, validation: { count: 1, status: "passed_with_findings" }, blockers: [{ type: "machine_fact", id: 10, title: "Maximum Spindle RPM", reason: "needs_review" }], next_action: { label: "Continue Machine Knowledge Review", path: "machine-knowledge" }, native_gpost_integration: { status: "not_verified", label: "Not Verified", explanation: "Native behavior requires site verification." } };
const document = { id: 3, machine_profile_id: 1, title: "KLS Machine Specification", document_type: "specification_document", processing_status: "ready", ai_post_builder_allowed: true, page_count: 8 };

function renderAt(path: string) { return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/gpost/:draftId/*" element={<PostRecordWorkspacePage />} /></Routes></MemoryRouter>); }
beforeEach(() => {
  vi.clearAllMocks(); vi.mocked(api.getGPostDraft).mockResolvedValue(draft as never); vi.mocked(api.listProfiles).mockResolvedValue([machine] as never);
  vi.mocked(api.getPostRecordSummary).mockResolvedValue(summary as never); vi.mocked(api.listMachineKnowledge).mockResolvedValue([fact, proposedFact] as never);
  vi.mocked(api.listOFGSettings).mockResolvedValue([setting] as never); vi.mocked(api.listSiteStandards).mockResolvedValue([standard] as never);
  vi.mocked(api.listPostStandards).mockResolvedValue([application] as never); vi.mocked(api.listCustomLogic).mockResolvedValue([logic] as never);
  vi.mocked(api.listPostQuestions).mockResolvedValue([question] as never); vi.mocked(api.listPostValidations).mockResolvedValue([validation] as never);
  vi.mocked(api.listGPostVersions).mockResolvedValue([draft] as never); vi.mocked(api.listDocuments).mockResolvedValue([document] as never);
  vi.mocked(api.listValidationFindings).mockResolvedValue([]); vi.mocked(api.listGPostDiagnostics).mockResolvedValue([]);
  vi.mocked(api.getValidationPolicy).mockResolvedValue({ id: 1, post_record_id: 4, name: "FANUC Lathe R&D", required_validation_types_json: ["Configuration Review", "G-POST Compilation", "NC Programmer Review"], optional_validation_types_json: ["VERICUT Simulation"], source: "Site", reviewer: "Engineer", updated_at: "2026-08-19" });
  vi.mocked(api.getValidationTimeline).mockResolvedValue({ post_record_id: 4, version: 1, events: [{ id: 60, type: "Configuration Review", name: "Review", result: "PASS_WITH_FINDINGS", performed_by: "NC Engineer", performed_at: "2026-08-19", findings_count: 0 }] });
  vi.mocked(api.getValidationHandoff).mockResolvedValue({ post_record_id: 4, post_version: 1, machine: machine.name, controller: "FANUC", current_validation_status: "NEEDS_REVIEW", outstanding_configuration_issues: 1, custom_fil_status: "Review required", development_package_url: "/package/4.md", does_not_run_vericut: true, checklist: [{ key: "ready", label: "ready for VERICUT", complete: false }] });
});

test("Post Record navigation is workflow-oriented and moves specialist tools out", async () => {
  renderAt("/gpost/4"); expect(await screen.findByRole("heading", { name: draft.name })).toBeInTheDocument();
  const workflow = screen.getByRole("navigation", { name: "Post Record workflow" });
  for (const label of ["Overview", "Machine Knowledge", "OFG Configuration", "Custom Logic", "Review & Export", "History & Sources"]) expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
  expect(workflow.querySelectorAll("a")).toHaveLength(6);
  expect(screen.queryByRole("link", { name: "Historical Post Examples" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Advanced Tools" })).not.toBeInTheDocument();
  expect(screen.getByText("Technical Details", { selector: "summary" })).toBeInTheDocument();
});
test("overview reports engineering counts and one contextual action", async () => {
  renderAt("/gpost/4"); expect(await screen.findByRole("heading", { name: "Post Development Progress" })).toBeInTheDocument();
  expect(screen.getByText("18 confirmed · 2 unresolved")).toBeInTheDocument(); expect(screen.getByText("32 reviewed · 13 remaining")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Continue Machine Knowledge Review" }).length).toBeGreaterThan(0);
});
test("Machine Knowledge shows source and OFG usage traceability", async () => {
  renderAt("/gpost/4/machine-knowledge/10"); expect(await screen.findByRole("heading", { name: fact.name })).toBeInTheDocument();
  expect(screen.getByText("KLS Machine Specification")).toBeInTheDocument(); expect(screen.getByText("p. 4")).toBeInTheDocument();
  expect(screen.getByText("OFG Configuration → Maximum Spindle Speed")).toBeInTheDocument();
});
test("OFG setting detail qualifies reference-backed locations without claiming site verification", async () => {
  renderAt("/gpost/4/ofg-configuration/20"); expect(await screen.findByRole("heading", { name: setting.display_name })).toBeInTheDocument();
  expect(screen.getByText("Source Machine Facts")).toBeInTheDocument(); expect(screen.getByText(/Verified From OFG Reference:/)).toBeInTheDocument();
  expect(screen.getByText(/not verification in the installed site environment/)).toBeInTheDocument(); expect(screen.getByText(/Controller Document \/ Machine Knowledge \/ Site Standard → OFG Engineering Choice/)).toBeInTheDocument();
  expect(screen.getByText("Site Standard Applied")).toBeInTheDocument(); expect(screen.getByRole("link", { name: "View Standard" })).toHaveAttribute("href", "/gpost/4/ofg-configuration");
  expect(screen.getByLabelText("Engineer Notes")).toBeInTheDocument();
  const status = screen.getByLabelText("Status");
  expect(Array.from(status.querySelectorAll("option")).map((option) => option.textContent)).toEqual(["Unmapped", "Mapped", "Needs Review", "Needs Information", "Reviewed", "Not Applicable", "Custom Logic Required"]);
});
test("OFG custom logic callout explains the reason without claiming a certain implementation", async () => {
  vi.mocked(api.listOFGSettings).mockResolvedValue([{ ...setting, status: "custom_logic_required", requires_custom_logic: true, custom_logic_id: 40 }] as never);
  renderAt("/gpost/4/ofg-configuration/20"); expect(await screen.findByText("Custom Logic Required", { selector: "strong" })).toBeInTheDocument();
  expect(screen.getByText("Standard OFG configuration does not represent required behavior.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open Custom Logic" })).toHaveAttribute("href", "/gpost/4/custom-logic");
  expect(screen.getByText(/Implementation may use FIL\/CIMFIL; site verification is required/)).toBeInTheDocument();
});
test("OFG checklist uses machine relevance, domain filters, reference paths, and advanced disclosure", async () => {
  const user = userEvent.setup();
  const advanced = { ...setting, id: 21, category: "Advanced / Custom", subsection: "MULTAX", setting_key: "multax", display_name: "MULTAX Motion", value_json: null, relevance_class: "advanced", relevance_label: "not_applicable", is_applicable: false, source_type: "OFG Reference", ofg_menu_path: "Motion → Cycles → MULTAX", source_machine_facts: [] };
  vi.mocked(api.listOFGSettings).mockResolvedValue([setting, advanced] as never);
  renderAt("/gpost/4/ofg-configuration");
  expect(await screen.findByText(/This checklist represents the Option File Generator settings believed relevant/)).toBeInTheDocument();
  for (const label of ["Search", "Category", "Status", "Relevance", "Custom Logic"]) expect(screen.getByLabelText(label)).toBeInTheDocument();
  for (const heading of ["Setting", "Value", "Source", "Status", "OFG Location", "Custom Logic", "Action"]) expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
  expect(screen.getByText("Required for this Post")).toBeInTheDocument();
  expect(screen.queryByText("MULTAX Motion")).not.toBeInTheDocument();
  await user.click(screen.getByLabelText("Show Advanced settings"));
  const advancedRow = screen.getByText("MULTAX Motion").closest("tr")!;
  expect(advancedRow).toHaveTextContent("Not Applicable");
});
test("structured OFG address rows preserve formats, order, source, and unknown code state", async () => {
  const address = { ...setting, id: 22, category: "File Formats", subsection: "MCD File", setting_key: "mcd_address_format", display_name: "MCD Address Format", value_json: null, structured_value_json: [{ address: "X", description: "X axis", output_order: 3, before_alias: null, after_alias: null, metric_format: "3.3", inch_format: "3.4", status: "unknown", source: "OFG Reference" }], code_status: "unknown" };
  vi.mocked(api.listOFGSettings).mockResolvedValue([address] as never);
  renderAt("/gpost/4/ofg-configuration/22");
  expect(await screen.findByRole("heading", { name: "MCD Address Format" })).toBeInTheDocument();
  for (const heading of ["Address", "Description", "Output Order", "Before Alias", "After Alias", "Metric Format", "Inch Format", "Status", "Source"]) expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
  expect(screen.getByLabelText("Code Status")).toHaveValue("unknown");
});
test("Machine Knowledge separates proposed and confirmed facts with review actions and traceability", async () => {
  const user = userEvent.setup(); vi.mocked(api.updateMachineKnowledge).mockResolvedValue({ ...proposedFact, status: "confirmed" } as never);
  renderAt("/gpost/4/machine-knowledge"); expect(await screen.findByRole("heading", { name: "Needs Review" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Confirmed" })).toBeInTheDocument();
  expect(screen.getByText("G74 Behavior")).toBeInTheDocument(); expect(screen.getByText("OFG → Spindle")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Review →" }));
  expect(screen.getByRole("dialog", { name: "Review G74 Behavior" })).toBeInTheDocument(); expect(screen.getByRole("link", { name: "View Source" })).toHaveAttribute("href", "/documents/3");
  await user.click(screen.getByRole("button", { name: "Confirm" }));
  expect(api.updateMachineKnowledge).toHaveBeenCalledWith(4, 11, expect.objectContaining({ status: "confirmed" }));
});
test("proposed fact drawer supports edit and confirm", async () => {
  const user = userEvent.setup(); vi.mocked(api.updateMachineKnowledge).mockResolvedValue({ ...proposedFact, value_json: "Reviewed G74", status: "confirmed" } as never);
  renderAt("/gpost/4/machine-knowledge"); await user.click(await screen.findByRole("button", { name: "Review →" }));
  await user.click(screen.getByRole("button", { name: "Edit & Confirm" })); const input = screen.getByLabelText("Edit proposed value"); await user.clear(input); await user.type(input, "Reviewed G74"); await user.click(screen.getByRole("button", { name: "Save & Confirm" }));
  expect(api.updateMachineKnowledge).toHaveBeenCalledWith(4, 11, expect.objectContaining({ value_json: "Reviewed G74", status: "confirmed" }));
});
test("proposed fact drawer supports reject", async () => {
  const user = userEvent.setup(); vi.mocked(api.updateMachineKnowledge).mockResolvedValue({ ...proposedFact, status: "not_applicable" } as never);
  renderAt("/gpost/4/machine-knowledge"); await user.click(await screen.findByRole("button", { name: "Review →" })); await user.click(screen.getByRole("button", { name: "Reject" }));
  expect(api.updateMachineKnowledge).toHaveBeenCalledWith(4, 11, expect.objectContaining({ status: "not_applicable" }));
});
test("machine configuration source labels are cleaned up in the primary UI", async () => {
  vi.mocked(api.listMachineKnowledge).mockResolvedValue([{ ...fact, source_document_id: null, source_label: "Machine configuration revision 4", source_location: "Reviewed machine profile" }] as never);
  renderAt("/gpost/4/machine-knowledge"); expect(await screen.findByText("Existing Machine Configuration")).toBeInTheDocument();
  expect(screen.queryByText("Machine configuration revision 4")).not.toBeInTheDocument();
});
test("export explains package contents and the native-post boundary", async () => {
  renderAt("/gpost/4/review-export"); expect(await screen.findByRole("heading", { name: "Post Development Package" })).toBeInTheDocument();
  const packagePanel = screen.getByRole("heading", { name: "Post Development Package" }).closest("section")!;
  for (const item of ["Machine Summary", "Confirmed Machine Knowledge", "OFG Configuration Checklist", "Applied Site Standards", "Custom Logic Summary", "Open Questions", "Review Summary", "Validation Records", "Sources", "Version Metadata"]) expect(within(packagePanel).getByText(item)).toBeInTheDocument();
  expect(screen.getByText(/not currently a compiled or native G-POST postprocessor file/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Engineering Report" })).toHaveAttribute("href", "/package/4.markdown");
});
test("workflow concepts expose concise demo tooltips", async () => {
  renderAt("/gpost/4"); await screen.findByRole("heading", { name: draft.name });
  expect(screen.getByTitle("Reviewed machine/controller facts extracted from manuals or entered by an engineer.")).toBeInTheDocument();
  expect(screen.getByTitle("A checklist of reviewed values/settings intended to guide configuration in G-POST Option File Generator.")).toBeInTheDocument();
  expect(screen.getByTitle("Machine/site-specific behavior that may require post customization beyond the standard OFG checklist.")).toBeInTheDocument();
});
test("first Post Record version has a purposeful empty state", async () => {
  renderAt("/gpost/4/history-sources"); expect(await screen.findByText("No prior versions yet.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Version History" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Source Documents" })).toBeInTheDocument();
  expect(screen.getByText("Create a version when the current Post Development Package reaches a meaningful review point.")).toBeInTheDocument();
});
test("Site Standards surfaces conflicts and Custom Logic links to specialist editor", async () => {
  renderAt("/gpost/4/site-standards"); expect(await screen.findByText("CONFLICT / SITE OVERRIDE REQUIRES REVIEW")).toBeInTheDocument();
  renderAt("/gpost/4/custom-logic"); expect(await screen.findByText(logic.name)).toBeInTheDocument();
  await userEvent.click(screen.getByText("Open", { selector: "summary" }));
  expect(screen.getByRole("link", { name: "Open FIL Workspace" })).toHaveAttribute("href", "/gpost/4/advanced/fil-editor?item=40");
});
test("Review has one completion summary, outstanding queue, and compact validation stages", async () => {
  renderAt("/gpost/4/review-export"); expect(await screen.findByRole("heading", { name: "Review & Export" })).toBeInTheDocument();
  for (const heading of ["Completion", "Outstanding Items", "Validation"]) expect(screen.getByRole("heading", { name: heading })).toBeInTheDocument();
  expect(screen.getByText(question.title)).toBeInTheDocument(); expect(screen.getByText("G-POST Test")).toBeInTheDocument();
  expect(screen.queryByText(/Validation Policy/)).not.toBeInTheDocument(); expect(screen.queryByText(/Listing Diagnostics/)).not.toBeInTheDocument();
});
test("Add Validation uses the reduced manual record form", async () => {
  const user = userEvent.setup(); renderAt("/gpost/4/review-export");
  await user.click(await screen.findByRole("button", { name: "Add Validation Record" }));
  for (const label of ["Type", "Result", "Performed By", "Date", "Notes", "Reference"]) expect(screen.getByLabelText(label)).toBeInTheDocument();
  expect(screen.getByText(/does not run external tools/)).toBeInTheDocument();
});
test("technical view contains audit metadata without exposing research navigation", async () => {
  renderAt("/gpost/4/advanced/technical"); expect(await screen.findByRole("heading", { name: "Technical Details" })).toBeInTheDocument();
  expect(screen.getByText("Not verified")).toBeInTheDocument(); expect(screen.getByText("FANUC Lathe R&D")).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Research Tools" })).not.toBeInTheDocument();
});
test("fact review remains manual and works with AI disabled", async () => {
  const user = userEvent.setup(); vi.mocked(api.updateMachineKnowledge).mockResolvedValue(fact as never);
  renderAt("/gpost/4/machine-knowledge/10"); await user.click(await screen.findByRole("button", { name: "Confirm" }));
  expect(api.updateMachineKnowledge).toHaveBeenCalledWith(4, 10, expect.objectContaining({ status: "confirmed", reviewer: "Mariah" }));
});
