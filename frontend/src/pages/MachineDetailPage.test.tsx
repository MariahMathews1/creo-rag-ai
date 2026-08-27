import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { MachineDetailPage } from "./MachineDetailPage";

vi.mock("../api/client", () => ({ api: { getProfile: vi.fn(), listDocuments: vi.fn(), listGPostDrafts: vi.fn(), listMachineKnowledge: vi.fn(), listPostQuestions: vi.fn(), updateMachineKnowledge: vi.fn() } }));

const machine = { id: 1, name: "KENT KLS-1840N", manufacturer: "KENT", model: "KLS-1840N", machine_type: "lathe", controller_name: "FANUC", controller_model: "0i-Mate TF", active_revision_id: 2 };
const sourceDocument = { id: 3, machine_profile_id: 1, title: "KLS Manual", document_type: "machine_manual", processing_status: "ready" };
const post = { id: 4, machine_profile_id: 1, name: "KLS Post", status: "review_required", updated_at: "2026-08-19" };
const fact = { id: 10, post_record_id: 4, category: "Spindle", name: "Maximum Spindle RPM", fact_key: "max_spindle_rpm", value_json: 2000, unit: "RPM", status: "confirmed", source_document_id: 3, source_label: "KLS Manual", source_location: "p.42", used_by: [] };

function renderDetail(path = "/machines/1") {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/machines/:machineId/:view?" element={<MachineDetailPage />} /></Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.mocked(api.getProfile).mockResolvedValue(machine as never);
  vi.mocked(api.listDocuments).mockResolvedValue([]);
  vi.mocked(api.listGPostDrafts).mockResolvedValue([]);
  vi.mocked(api.listMachineKnowledge).mockResolvedValue([]);
  vi.mocked(api.listPostQuestions).mockResolvedValue([]);
});

test("machine detail exposes only the four V1 machine views", async () => {
  renderDetail();
  expect(await screen.findByRole("heading", { name: machine.name })).toBeInTheDocument();
  const navigation = screen.getByRole("navigation", { name: "Machine views" });
  expect(navigation.querySelectorAll("a")).toHaveLength(4);
  for (const label of ["Overview", "Machine Knowledge", "Documents", "Post Records"]) expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
  expect(screen.getByText("View Technical Details", { selector: "summary" })).toBeInTheDocument();
});

test("machine overview is compact and exposes exactly one contextual next step", async () => {
  renderDetail(); await screen.findByRole("heading", { name: machine.name });
  expect(screen.queryByRole("heading", { name: "Machine Overview" })).not.toBeInTheDocument();
  const metrics = document.querySelector(".machine-summary-metrics")!;
  for (const metric of ["Documents", "Machine Knowledge", "Post Records"]) expect(within(metrics as HTMLElement).getByText(metric)).toBeInTheDocument();
  const next = screen.getByText("Next Step").closest("aside")!;
  expect(within(next).getByRole("heading", { name: "Upload machine documentation." })).toBeInTheDocument();
  expect(within(next).getAllByRole("link")).toHaveLength(1);
});

test("next step continues an existing post when machine knowledge is ready", async () => {
  vi.mocked(api.listDocuments).mockResolvedValue([sourceDocument] as never); vi.mocked(api.listGPostDrafts).mockResolvedValue([post] as never);
  vi.mocked(api.listMachineKnowledge).mockResolvedValue([fact] as never);
  renderDetail(); expect(await screen.findByRole("heading", { name: "Continue Post Development" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open Post" })).toHaveAttribute("href", "/gpost/4");
});
