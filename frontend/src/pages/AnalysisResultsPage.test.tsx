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
    getAnalysisToolpath: vi.fn(),
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
  vi.mocked(api.getAnalysisToolpath).mockResolvedValue({
    source: "gcode", machine_type: "mill", default_view: "XY", coordinate_context: "work",
    bounds: { min_x: 0, max_x: 25, min_y: 0, max_y: 0, min_z: 0, max_z: 0 },
    summary: { segments: 1, rapid: 1, feed: 0, arcs: 0, tools: 0, operations: 0, unresolved_geometry: 0, visualization_simplified: false },
    warnings: [], comparison_summary: null, advisory_only: true,
    safety_notice: "TOOLPATH VISUALIZATION ONLY — NOT MACHINE SIMULATION",
    segments: [{ id: "gcode-2", source_type: "gcode", source_record_id: 1, source_line_start: 2, source_line_end: 2, operation_id: null, tool_number: null, motion_type: "rapid", start_point: { x: 0, y: 0, z: 0 }, end_point: { x: 25, y: 0, z: 0 }, center_point: null, radius: null, path_points: [], plane: null, feed_rate: null, spindle_speed: null, rapid: true, arc_direction: null, helical: false, tool_axis: null, alignment_link_id: null, aligned_segment_ids: [], finding_ids: [1, 2], sequence_index: 0, visualizable: true, unmatched: false, geometry_status: null, metadata_json: {} }],
  } as never);
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

test("toolpath tab loads the visual trace and preserves finding linkage", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/analysis/1"]}><Routes><Route path="/analysis/:projectId" element={<AnalysisResultsPage />} /></Routes></MemoryRouter>);
  await screen.findByText("Review A");
  await user.click(screen.getByRole("button", { name: "Toolpath" }));
  expect(await screen.findByText(/TOOLPATH VISUALIZATION ONLY/)).toBeInTheDocument();
  expect(api.getAnalysisToolpath).toHaveBeenCalledWith(1);
  expect(screen.getByRole("table")).toBeInTheDocument();
  await user.click(screen.getByRole("row", { name: /1 rapid/i }));
  expect(document.getElementById("line-2")).toHaveClass("line-selected");
});
