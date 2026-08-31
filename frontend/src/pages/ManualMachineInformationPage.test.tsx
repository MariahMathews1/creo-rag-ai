import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { ManualMachineInformationPage } from "./ManualMachineInformationPage";

vi.mock("../api/client", () => ({ api: { getProfile: vi.fn(), listManualMachineInformationFields: vi.fn(), listDocuments: vi.fn(), getProfileProposal: vi.fn(), saveManualMachineInformation: vi.fn() } }));
const machine = { id: 2, name: "Demo Lathe", controller_name: "FANUC", controller_model: "0i-TF" };
const fields = [
  { fact_key: "max_spindle_rpm", label: "Maximum spindle RPM", category: "Spindle", data_type: "number", units: ["rpm"] },
  { fact_key: "controller_name", label: "Controller", category: "Controller", data_type: "string", units: [] },
  { fact_key: "x_travel", label: "X-axis travel", category: "Axes / Kinematics", data_type: "number", units: ["inch", "mm"] },
];
const proposal = { id: 33, extraction_run_id: 11, field_key: "x_travel", field_label: "X-axis travel", unit: null };
function Probe() { const location = useLocation(); return <output aria-label="location">{location.pathname}{location.search}</output>; }
function renderPage(path = "/machines/2/machine-information/manual") { return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/machines/:machineId/machine-information/manual" element={<><ManualMachineInformationPage /><Probe /></>} /><Route path="*" element={<Probe />} /></Routes></MemoryRouter>); }
beforeEach(() => { vi.clearAllMocks(); vi.mocked(api.getProfile).mockResolvedValue(machine as never); vi.mocked(api.listManualMachineInformationFields).mockResolvedValue(fields as never); vi.mocked(api.listDocuments).mockResolvedValue([]); vi.mocked(api.getProfileProposal).mockResolvedValue(proposal as never); vi.mocked(api.saveManualMachineInformation).mockResolvedValue({ id: 1 } as never); });

test("generic manual entry saves numeric value, unit, source, and explicit Confirmed status", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByRole("heading", { name: "Add Machine Information" });
  await user.selectOptions(screen.getByLabelText("Information / Fact"), "max_spindle_rpm");
  await user.type(screen.getByLabelText("Value"), "2000"); await user.selectOptions(screen.getByLabelText("Source / Basis"), "engineer_entry");
  await user.selectOptions(screen.getByLabelText("Review Status"), "confirmed"); await user.click(screen.getByRole("button", { name: "Save" }));
  expect(api.saveManualMachineInformation).toHaveBeenCalledWith(2, expect.objectContaining({ fact_key: "max_spindle_rpm", value: "2000", unit: "rpm", source_basis: "engineer_entry", review_status: "confirmed" }));
  await waitFor(() => expect(screen.getByLabelText("location")).toHaveTextContent("/machines/2/machine-knowledge?manualSaved=max_spindle_rpm"));
});

test("text entry does not force a unit and defaults to Needs Review", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByRole("heading", { name: "Add Machine Information" });
  await user.selectOptions(screen.getByLabelText("Information / Fact"), "controller_name"); await user.type(screen.getByLabelText("Value"), "FANUC 0i-TF");
  expect(screen.getByLabelText("Unit")).toBeDisabled(); expect(screen.getByLabelText("Review Status")).toHaveValue("needs_review");
});

test("missing-item entry preselects and locks the fact, then returns to extraction review", async () => {
  const user = userEvent.setup(); renderPage("/machines/2/machine-information/manual?run=11&proposal=33&field=x_travel");
  expect(await screen.findByLabelText("Information / Fact")).toHaveValue("x_travel"); expect(screen.getByLabelText("Information / Fact")).toBeDisabled();
  await user.type(screen.getByLabelText("Value"), "11"); await user.selectOptions(screen.getByLabelText("Unit"), "inch");
  await user.selectOptions(screen.getByLabelText("Source / Basis"), "installed_machine_configuration"); await user.click(screen.getByRole("button", { name: "Save" }));
  expect(api.saveManualMachineInformation).toHaveBeenCalledWith(2, expect.objectContaining({ proposal_id: 33, fact_key: "x_travel", value: "11", unit: "inch" }));
  await waitFor(() => expect(screen.getByLabelText("location")).toHaveTextContent("/machines/2/profile-extraction/11?v1=1&manualSaved=x_travel"));
});

test("Cancel returns to the invoking context without saving", async () => {
  const user = userEvent.setup(); renderPage("/machines/2/machine-information/manual?run=11&proposal=33&field=x_travel");
  await screen.findByLabelText("Information / Fact"); await user.click(screen.getByRole("button", { name: "Cancel" }));
  expect(api.saveManualMachineInformation).not.toHaveBeenCalled(); expect(screen.getByLabelText("location")).toHaveTextContent("/machines/2/profile-extraction/11?v1=1");
});
