import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import type { PostSectionDraft, PostSectionKey, PostSectionReadiness } from "../types";
import { PostBuilderWorkspacePage } from "./PostBuilderWorkspacePage";

vi.mock("../api/client", () => ({ api: {
  getGPostDraft: vi.fn(), listProfiles: vi.fn(), listDocuments: vi.fn(), listGPostVersions: vi.fn(), getAssembledPost: vi.fn(),
  getPostBuilderProviderStatus: vi.fn(), getPostSectionReadiness: vi.fn(), listPostSections: vi.fn(),
  getPostSection: vi.fn(), retrievePostBuilderEvidence: vi.fn(), generatePostSection: vi.fn(),
  reviewPostRule: vi.fn(), listPostSectionVersions: vi.fn(), comparePostSectionVersions: vi.fn(),
  setDocumentPostBuilderPolicy: vi.fn(), updateGPostDraft: vi.fn(), createGPostVersion: vi.fn(), archiveGPostDraft: vi.fn(), deleteGPostDraft: vi.fn(),
  gpostExportUrl: vi.fn((id, format) => `/exports/${id}.${format}`),
} }));

const machine = { id: 1, name: "KLS-1840N", manufacturer: "KENT", model: "KLS", machine_type: "lathe", axis_count: 2, controller_name: "FANUC", controller_manufacturer: "FANUC", controller_model: "0i-TF", controller_version: "1" };
const draft = { id: 4, machine_profile_id: 1, machine_profile_revision_id: 2, name: "KLS Post", version: 2, status: "review_required", controller_family: "fanuc_lathe", machine_type: "lathe", templates_json: {}, capability_snapshot_json: {}, selected_document_ids_json: [3], reference_program_ids_json: [], unsupported_features_json: [], warnings_json: [], review_summary_json: {}, created_at: "2026-01-01", updated_at: "2026-01-02" };
const document = { id: 3, machine_profile_id: 1, title: "FANUC Programming Manual", document_type: "controller_manual", processing_status: "ready", page_count: 100, ai_post_builder_allowed: true };
const keys: PostSectionKey[] = ["program_structure", "tooling", "spindle", "coolant", "feed", "motion", "coordinates", "program_end", "cycles"];
const readiness = keys.map((section_key): PostSectionReadiness => ({
  section_key, label: section_key === "spindle" ? "Spindle" : section_key === "cycles" ? "Cycles" : section_key.replaceAll("_", " "),
  readiness: section_key === "cycles" ? "deferred" : "ready", manual_setup_readiness: section_key === "cycles" ? "needs_information" : "ready",
  ai_drafting_readiness: section_key === "cycles" ? "deferred" : "ready", known_machine_facts: [{ key: "controller", label: "Controller", value: "FANUC 0i-TF", status: "known", critical: true, source: "approved profile" }],
  missing_information: section_key === "cycles" ? ["Cycle behavior is deferred"] : [], warnings: [], conflicts: [], evidence_count: 1, reviewed_rule_count: 0,
  current_draft_status: "not_started", draft_allowed: section_key !== "cycles",
}));
const evidence = { evidence_id: 12, document_id: 3, document_title: document.title, document_type: "controller_manual", page_start: 40, page_end: 40, section_title: "Spindle", excerpt: "M03 starts the spindle clockwise.", relevance_score: 3, matched_terms: ["spindle", "M03"], ai_eligible: true, conflict_labels: [] };
const section: PostSectionDraft = {
  id: 20, gpost_draft_id: 4, section_key: "spindle", section_version: 1, status: "needs_review", source_type: "ai_assisted",
  machine_context_snapshot_json: { controller: "FANUC 0i-TF" }, draft_templates_json: [], missing_information_json: [], assumptions_json: [], warnings_json: ["Engineering review required"],
  source_evidence_json: [evidence], ai_generated: true, provider: "mock", model: "deterministic-fixture", prompt_version: "post-section-draft-v2", response_schema_version: "post-section-draft-response-v2", reviewed_at: null,
  created_at: "2026-01-02", updated_at: "2026-01-02", advisory_only: true,
  rules: [{ id: 31, rule_key: "spindle_cw", name: "Clockwise spindle start", description: null, condition: "Clockwise spindle requested", output_behavior: "Emit spindle speed and M03", ai_draft_template: "S{rpm} M03", engineer_template: null, required_machine_facts_json: ["controller"], evidence_ids_json: [12], assumptions_json: [], warnings_json: [], status: "needs_review", review_reason: null, reviewer_label: null, reviewed_at: null, created_at: "2026-01-02", updated_at: "2026-01-02" }],
};
const assembled = {
  draft_id: 4, name: draft.name, status: "building", required_area_count: 8,
  counts: { reviewed: 0, needs_review: 1, needs_information: 0, not_started: 7, deferred: 1 },
  components: keys.map((section_key) => ({ section_key, label: readiness.find((item) => item.section_key === section_key)?.label,
    state: section_key === "spindle" ? "needs_review" : section_key === "cycles" ? "deferred" : "not_started",
    required: section_key !== "cycles", section_version: section_key === "spindle" ? 1 : null,
    rules: section_key === "spindle" ? section.rules.map((item) => ({ rule_key: item.rule_key, name: item.name, condition: item.condition, template: item.ai_draft_template, status: item.status, evidence_ids: item.evidence_ids_json, reviewer: null })) : [],
    missing_information: section_key === "cycles" ? ["Cycle behavior is deferred"] : [], evidence_count: 1 })),
  ready_for_complete_review: false, advisory_only: true, native_gpost_export: "not_configured",
};

function renderAt(path: string) {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/gpost/:draftId/*" element={<PostBuilderWorkspacePage />} /></Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getGPostDraft).mockResolvedValue(draft as never);
  vi.mocked(api.listProfiles).mockResolvedValue([machine] as never);
  vi.mocked(api.listDocuments).mockResolvedValue([document] as never);
  vi.mocked(api.listGPostVersions).mockResolvedValue([draft] as never);
  vi.mocked(api.getAssembledPost).mockResolvedValue(assembled as never);
  vi.mocked(api.getPostBuilderProviderStatus).mockResolvedValue({ provider: "mock", configured: true, reachable: true, external_processing: false, public_web: false } as never);
  vi.mocked(api.getPostSectionReadiness).mockResolvedValue(readiness);
  vi.mocked(api.listPostSections).mockResolvedValue([]);
  vi.mocked(api.retrievePostBuilderEvidence).mockResolvedValue([evidence]);
  vi.mocked(api.listPostSectionVersions).mockResolvedValue([]);
  vi.mocked(api.generatePostSection).mockResolvedValue(section);
  vi.mocked(api.getPostSection).mockResolvedValue(section);
  vi.mocked(api.reviewPostRule).mockResolvedValue({ ...section.rules[0], status: "accepted" });
});

test("overview states the development-only boundary and exposes no CL input", async () => {
  renderAt("/gpost/4");
  expect((await screen.findAllByRole("heading", { name: "KLS Post" })).length).toBeGreaterThan(0);
  expect(screen.getByText("AI ASSISTS POST DEVELOPMENT ONLY")).toBeInTheDocument();
  expect(screen.getByText(/CL\/NCL, part geometry, toolpaths/)).toBeInTheDocument();
  expect(screen.getByText("Post Build Progress")).toBeInTheDocument();
  expect(screen.queryByLabelText(/CL \/ NCL Input/i)).not.toBeInTheDocument();
});

test("Build Post presents components of one assembled configuration and defers cycles", async () => {
  renderAt("/gpost/4/builder");
  expect(await screen.findByRole("heading", { name: "Build Post Configuration" })).toBeInTheDocument();
  expect(screen.getByText("Complete Post Configuration")).toBeInTheDocument();
  expect(screen.getByText(/There is no whole-post AI generation/)).toBeInTheDocument();
  expect(screen.getAllByText("Cycles").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Deferred").length).toBeGreaterThan(0);
  expect(screen.getByRole("link", { name: "View" })).toHaveAttribute("href", "/gpost/4/builder/cycles");
  expect(screen.getAllByTitle(/Sufficient approved machine knowledge/).length).toBeGreaterThan(0);
});

test("explicit section action shows safe context and creates review-only rules", async () => {
  const user = userEvent.setup();
  renderAt("/gpost/4/builder/spindle");
  expect(await screen.findByRole("heading", { name: "Spindle" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Review AI Context" }));
  expect(screen.getAllByText("NOT INCLUDED", { selector: "dd" })).toHaveLength(3);
  await user.click(screen.getByRole("button", { name: "Draft with AI" }));
  expect(await screen.findByText("Clockwise spindle start")).toBeInTheDocument();
  expect(screen.getAllByText(/Status: needs review/).length).toBeGreaterThan(0);
  expect(api.generatePostSection).toHaveBeenCalledWith(4, "spindle", [12], "refresh");
});

test("machine knowledge is a compact checklist with drill-down", async () => {
  renderAt("/gpost/4/machine-knowledge");
  expect(await screen.findByRole("heading", { name: "Machine Knowledge" })).toBeInTheDocument();
  expect(screen.getByRole("columnheader", { name: "Configuration Area" })).toBeInTheDocument();
  expect(screen.queryByText(/Manual Setup:/)).not.toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: "Review" }).length).toBeGreaterThan(0);
});

test("review shows only actionable work and the assembled complete post", async () => {
  renderAt("/gpost/4/review");
  expect(await screen.findByRole("heading", { name: "Post Review" })).toBeInTheDocument();
  expect(screen.getByText("1 areas ready for review")).toBeInTheDocument();
  expect(screen.getAllByRole("heading", { name: draft.name })).toHaveLength(2);
  expect(screen.getAllByRole("link", { name: "Review" }).find((link) => link.getAttribute("href") === "/gpost/4/builder/spindle")).toBeDefined();
});

test("versions are lineage scoped and display monotonic backend numbers", async () => {
  vi.mocked(api.listGPostVersions).mockResolvedValue([{ ...draft, id: 6, version: 3 }, { ...draft, id: 5, version: 2, status: "superseded" }, { ...draft, version: 1, status: "superseded" }] as never);
  renderAt("/gpost/4/versions");
  expect(await screen.findByText("v3")).toBeInTheDocument();
  expect(screen.getByText("v2")).toBeInTheDocument(); expect(screen.getByText("v1")).toBeInTheDocument();
});

test("Sources distinguishes allowed and ineligible source classifications", async () => {
  vi.mocked(api.listDocuments).mockResolvedValue([document, { ...document, id: 9, title: "Shop Notes", document_type: "operator_manual", ai_post_builder_allowed: false }] as never);
  renderAt("/gpost/4/sources");
  expect(await screen.findByRole("heading", { name: "Post Builder Sources" })).toBeInTheDocument();
  expect(screen.getByText("Allowed")).toBeInTheDocument(); expect(screen.getByText("Ineligible")).toBeInTheDocument();
  expect(screen.getByText(/This source cannot be used/)).toBeInTheDocument();
});

test("rule decisions are explicit and preserve reviewer identity", async () => {
  vi.mocked(api.listPostSections).mockResolvedValue([section]);
  vi.mocked(api.listPostSectionVersions).mockResolvedValue([section]);
  const user = userEvent.setup();
  renderAt("/gpost/4/builder/spindle");
  await user.click(await screen.findByRole("button", { name: "Accept" }));
  await waitFor(() => expect(api.reviewPostRule).toHaveBeenCalledWith(4, "spindle", 31, "accept", expect.objectContaining({ reviewer_label: "Local Post Engineer" })));
});
