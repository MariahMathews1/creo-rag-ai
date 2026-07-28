import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { ProfileExtractionSetupPage } from "./ProfileExtractionSetupPage";

vi.mock("../api/client", () => ({ api: {
  listProfiles: vi.fn(), listDocuments: vi.fn(), startProfileExtraction: vi.fn(),
} }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listProfiles).mockResolvedValue([{
    id: 2, name: "Fictional LT-200", machine_type: "lathe",
  }] as never);
  vi.mocked(api.listDocuments).mockResolvedValue([
    {
      id: 7, title: "Operator manual", processing_status: "ready",
      document_type: "operator_manual", original_filename: "operator.md", page_count: 4,
    },
    {
      id: 8, title: "Scanned manual", processing_status: "failed",
      document_type: "machine_manual", original_filename: "scan.pdf", page_count: null,
    },
  ] as never);
  vi.mocked(api.startProfileExtraction).mockResolvedValue({ id: 11 } as never);
});

test("selects only ready documents and starts the configured extraction", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/machines/2/profile-extraction/new"]}><Routes>
    <Route path="/machines/:machineId/profile-extraction/new" element={<ProfileExtractionSetupPage />} />
    <Route path="/machines/:machineId/profile-extraction/:runId" element={<p>Review route</p>} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Operator manual")).toBeInTheDocument();
  const checkboxes = screen.getAllByRole("checkbox");
  expect(checkboxes[1]).toBeDisabled();
  await user.click(checkboxes[0]);
  await user.click(screen.getByRole("button", { name: "Start extraction" }));
  expect(api.startProfileExtraction).toHaveBeenCalledWith(2, expect.objectContaining({
    document_ids: [7], target_machine_type: "lathe",
  }));
  expect(await screen.findByText("Review route")).toBeInTheDocument();
});

test("renders API failures and disables submission without documents", async () => {
  vi.mocked(api.listDocuments).mockRejectedValue(new Error("Documents unavailable"));
  render(<MemoryRouter initialEntries={["/machines/2/profile-extraction/new"]}><Routes>
    <Route path="/machines/:machineId/profile-extraction/new" element={<ProfileExtractionSetupPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Documents unavailable")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start extraction" })).toBeDisabled();
});
