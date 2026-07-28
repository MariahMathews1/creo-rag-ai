import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { test, vi } from "vitest";
import { api } from "../api/client";
import { ProfileRevisionsPage } from "./ProfileRevisionsPage";

vi.mock("../api/client", () => ({ api: { listProfileRevisions: vi.fn() } }));

test("renders preserved approved, superseded, and draft revisions", async () => {
  vi.mocked(api.listProfileRevisions).mockResolvedValue([
    { id: 3, revision_number: 3, status: "draft", manufacturer: "Northstar", model: "LT-200", controller_name: "Orion", source_type: "document_extraction", review_summary: "Review in progress" },
    { id: 2, revision_number: 2, status: "approved", manufacturer: "Northstar", model: "LT-200", controller_name: "Orion", source_type: "manual_entry", review_summary: "Approved" },
    { id: 1, revision_number: 1, status: "superseded", manufacturer: "Northstar", model: "LT-200", controller_name: "Orion", source_type: "imported", review_summary: "Migrated" },
  ] as never);
  render(<MemoryRouter initialEntries={["/machines/2/revisions"]}><Routes>
    <Route path="/machines/:machineId/revisions" element={<ProfileRevisionsPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("Revision v3")).toBeInTheDocument();
  expect(screen.getByText("Revision v2")).toBeInTheDocument();
  expect(screen.getByText("Revision v1")).toBeInTheDocument();
  expect(screen.getByText("superseded")).toBeInTheDocument();
});
