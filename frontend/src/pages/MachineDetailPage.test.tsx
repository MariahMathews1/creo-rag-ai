import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { MachineDetailPage } from "./MachineDetailPage";

vi.mock("../api/client", () => ({ api: { getProfile: vi.fn(), listDocuments: vi.fn(), listGPostDrafts: vi.fn(), listMachineKnowledge: vi.fn(), listPostQuestions: vi.fn(), listManualMachineInformation: vi.fn(), updateMachineKnowledge: vi.fn(), discardMachineInformation: vi.fn(), deleteDocument: vi.fn(), reprocessDocument: vi.fn() } }));

const machine = { id: 1, name: "KENT KLS-1840N", manufacturer: "KENT", model: "KLS-1840N", machine_type: "lathe", controller_name: "FANUC", controller_model: "0i-Mate TF", active_revision_id: 2 };
const sourceDocument = { id: 3, machine_profile_id: 1, title: "KLS Manual", document_type: "machine_manual", processing_status: "ready" };
const post = { id: 4, machine_profile_id: 1, name: "KLS Post", status: "review_required", updated_at: "2026-08-19" };
const fact = { id: 10, post_record_id: 4, category: "Spindle", name: "Maximum Spindle RPM", fact_key: "max_spindle_rpm", value_json: 2000, unit: "RPM", status: "confirmed", source_document_id: 3, source_label: "KLS Manual", source_location: "p.42", used_by: [] };

function renderDetail(path = "/machines/1") {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/machines/:machineId/:view?" element={<MachineDetailPage />} /></Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("confirm", vi.fn(() => true));
  vi.mocked(api.getProfile).mockResolvedValue(machine as never);
  vi.mocked(api.listDocuments).mockResolvedValue([]);
  vi.mocked(api.listGPostDrafts).mockResolvedValue([]);
  vi.mocked(api.listMachineKnowledge).mockResolvedValue([]);
  vi.mocked(api.listPostQuestions).mockResolvedValue([]);
  vi.mocked(api.listManualMachineInformation).mockResolvedValue([]);
});

test("machine detail exposes only the four V1 machine views", async () => {
  renderDetail();
  expect(await screen.findByRole("heading", { name: machine.name })).toBeInTheDocument();
  const navigation = screen.getByRole("navigation", { name: "Machine views" });
  expect(navigation.querySelectorAll("a")).toHaveLength(4);
  for (const label of ["Overview", "Machine Information", "Documents", "Post Records"]) expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
  expect(screen.getByText("More Details", { selector: "summary" })).toBeInTheDocument();
});

test("machine overview is compact and exposes exactly one contextual next step", async () => {
  renderDetail(); await screen.findByRole("heading", { name: machine.name });
  expect(screen.queryByRole("heading", { name: "Machine Overview" })).not.toBeInTheDocument();
  const metrics = document.querySelector(".machine-summary-metrics")!;
  for (const metric of ["Documents", "Machine Information", "Post Records"]) expect(within(metrics as HTMLElement).getByText(metric)).toBeInTheDocument();
  const next = screen.getByText("Next Step").closest("aside")!;
  expect(within(next).getByRole("heading", { name: "Upload machine documentation." })).toBeInTheDocument();
  expect(within(next).getAllByRole("link")).toHaveLength(1);
});

test("Add Information Manually uses the dedicated workflow and buttons are spaced", async () => {
  renderDetail("/machines/1/machine-knowledge");
  const link = await screen.findByRole("link", { name: "Add Information Manually" });
  expect(link).toHaveAttribute("href", "/machines/1/machine-information/manual");
  expect(link).not.toHaveAttribute("href", expect.stringContaining("profile-extraction"));
  expect(link.parentElement).toHaveClass("machine-information-empty-actions");
});

test("Machine Information offers extraction and confirmed discard actions", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listManualMachineInformation).mockResolvedValue([{ id: 8, machine_profile_id: 1, revision_id: 3,
    fact_key: "axis_count", label: "Axis count", category: "Axes / Kinematics", value: 3, unit: null,
    source_basis: "engineer_entry", source_label: "Engineer Entry", source_detail: null, notes: null,
    review_status: "needs_review", proposal_id: null }] as never);
  vi.mocked(api.discardMachineInformation).mockResolvedValue(undefined);
  renderDetail("/machines/1/machine-knowledge");
  expect(await screen.findByRole("link", { name: "Extract from Documents" })).toHaveAttribute("href", "/machines/1/profile-extraction/new");
  const row = screen.getByText("Axis count").closest("tr")!;
  expect(within(row).getByText("Axes / Kinematics")).toBeInTheDocument();
  expect(within(row).getByText("Needs Review")).toHaveClass("machine-information-status");
  await user.click(within(row).getByRole("button", { name: "Actions for Axis count" }));
  await user.click(screen.getByRole("menuitem", { name: "Discard Information" }));
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Revision and audit history will be preserved"));
  await vi.waitFor(() => expect(api.discardMachineInformation).toHaveBeenCalledWith(1, "axis_count"));
});

test("selected-machine Documents table uses matching compact row actions", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listDocuments).mockResolvedValue([{ ...sourceDocument, original_filename: "kls-manual.pdf" }] as never);
  renderDetail("/machines/1/documents");
  const title = await screen.findByText("KLS Manual");
  const row = title.closest("tr")!;
  expect(within(row).getByText("kls-manual.pdf")).toBeInTheDocument();
  expect(within(row).getByText("Ready")).toHaveClass("document-status", "ready");
  expect(within(row).getByRole("link", { name: "Open →" })).toHaveClass("button", "tertiary", "machine-document-open");
  await user.click(within(row).getByRole("button", { name: "More actions for KLS Manual" }));
  expect(screen.getByRole("menuitem", { name: "Extract Information" })).toHaveAttribute("href", "/machines/1/profile-extraction/new");
  expect(screen.getByRole("menuitem", { name: "Delete Document" })).toHaveClass("danger");
});

test("next step continues an existing post when machine knowledge is ready", async () => {
  vi.mocked(api.listDocuments).mockResolvedValue([sourceDocument] as never); vi.mocked(api.listGPostDrafts).mockResolvedValue([post] as never);
  vi.mocked(api.listMachineKnowledge).mockResolvedValue([fact] as never);
  renderDetail(); expect(await screen.findByRole("heading", { name: "Continue Post Development" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open Post" })).toHaveAttribute("href", "/gpost/4");
});
