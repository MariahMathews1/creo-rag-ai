import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { NewAnalysisPage } from "./NewAnalysisPage";

vi.mock("../api/client", () => ({
  api: {
    listProfiles: vi.fn(),
    createProject: vi.fn(),
    runAnalysis: vi.fn(),
  },
}));

beforeEach(() => {
  vi.mocked(api.listProfiles).mockResolvedValue([{ id: 7, name: "Test Mill" } as never]);
  vi.mocked(api.createProject).mockResolvedValue({ id: 42 } as never);
  vi.mocked(api.runAnalysis).mockResolvedValue({} as never);
});

test("submits the analysis and navigates to results", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/analysis/new"]}>
      <Routes>
        <Route path="/analysis/new" element={<NewAnalysisPage />} />
        <Route path="/analysis/:projectId" element={<p>Analysis results loaded</p>} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByRole("option", { name: "Test Mill" });
  await user.type(screen.getByLabelText("Analysis name"), "Housing review");
  await user.type(screen.getByLabelText("Post-processed G-code"), "G54\nM30");
  await user.click(screen.getByRole("button", { name: /run deterministic analysis/i }));
  await waitFor(() => expect(api.createProject).toHaveBeenCalled());
  expect(await screen.findByText("Analysis results loaded")).toBeInTheDocument();
});

test("shows API errors instead of a blank form", async () => {
  vi.mocked(api.listProfiles).mockRejectedValueOnce(
    new Error("Backend unavailable. Confirm the API is running and try again."),
  );
  render(
    <MemoryRouter>
      <NewAnalysisPage />
    </MemoryRouter>,
  );
  expect(
    await screen.findByText(/Backend unavailable/),
  ).toBeInTheDocument();
});
