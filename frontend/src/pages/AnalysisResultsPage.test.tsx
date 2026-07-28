import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { AnalysisResultsPage } from "./AnalysisResultsPage";

vi.mock("../api/client", () => ({
  api: {
    getProject: vi.fn(),
    getFindings: vi.fn(),
    explain: vi.fn(),
    listProfiles: vi.fn(),
  },
}));

beforeEach(() => {
  vi.mocked(api.getProject).mockResolvedValue({
    id: 1, name: "Review A", gcode_source: "G54\nG0 X25\nM30",
    status: "blocked", updated_at: "2026-01-01T00:00:00Z",
  } as never);
  vi.mocked(api.listProfiles).mockResolvedValue([
    { id: 7, name: "Test Mill" } as never,
  ]);
  vi.mocked(api.getFindings).mockResolvedValue([
    { id: 1, severity: "blocking", category: "machine_limits", title: "X-axis value exceeds configured travel", description: "X25 is outside range.", recommendation: "Verify coordinates.", rule_id: "AXIS_X_LIMIT", line_number: 2, source_line: "G0 X25" },
    { id: 2, severity: "warning", category: "motion", title: "Rapid move requires review", description: "Low Z.", recommendation: "Simulate.", rule_id: "RAPID_Z_REVIEW", line_number: 2, source_line: "G0 X25" },
  ] as never);
  vi.mocked(api.explain).mockResolvedValue({ advisory: true, explanation: "Mock advisory." });
});

test("displays findings and filters by severity", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/analysis/1"]}><Routes><Route path="/analysis/:projectId" element={<AnalysisResultsPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("X-axis value exceeds configured travel")).toBeInTheDocument();
  expect(screen.getByText("Rapid move requires review")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /warning 1/i }));
  expect(screen.queryByText("Rapid move requires review")).not.toBeInTheDocument();
  expect(screen.getByText("X-axis value exceeds configured travel")).toBeInTheDocument();
});

test("selecting a finding highlights its G-code line", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/analysis/1"]}><Routes><Route path="/analysis/:projectId" element={<AnalysisResultsPage />} /></Routes></MemoryRouter>);
  await user.click(
    await screen.findByRole("button", {
      name: /X-axis value exceeds configured travel/i,
    }),
  );
  expect(document.getElementById("line-2")).toHaveClass("line-selected");
  expect(screen.getByText("AXIS_X_LIMIT")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Explain using machine manuals/ })).toHaveAttribute(
    "href", expect.stringContaining("/manual-assistant"),
  );
});

test("displays severity counts", async () => {
  render(<MemoryRouter initialEntries={["/analysis/1"]}><Routes><Route path="/analysis/:projectId" element={<AnalysisResultsPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByText("Review A")).toBeInTheDocument();
  expect(screen.getByText("Blocking issues detected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /blocking 1/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /warning 1/i })).toBeInTheDocument();
});
