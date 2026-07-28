import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { TraceabilityPage } from "./TraceabilityPage";

vi.mock("../api/client", () => ({ api: {
  getProject: vi.fn(), listAlignmentRuns: vi.fn(), listCLRecords: vi.fn(),
  listGCodeBlocks: vi.fn(), listAlignmentLinks: vi.fn(), listAlignmentIssues: vi.fn(),
  createAlignmentRun: vi.fn(), confirmAlignmentLink: vi.fn(),
  rejectAlignmentLink: vi.fn(), updateAlignmentLink: vi.fn(),
  alignmentReportUrl: vi.fn(() => "/report.md"),
} }));

const run = {
  id: 4, analysis_project_id: 1, version: 1, status: "review_required",
  algorithm_version: "deterministic-v1", settings_json: {},
  summary_json: { proposed_link_count: 1, review_required: true }, metrics_json: {},
  stale: false, completed_at: "2026-01-01", advisory_only: true,
  alignment_is_inferred: true, manual_review_required: true, safety_notice: "Review required",
};
const link = {
  id: 7, alignment_run_id: 4, cl_record_id: 10, gcode_block_id: 20,
  link_type: "direct", confidence: .95, match_reasons_json: ["Tool numbers match"],
  mismatch_reasons_json: [], score_components_json: {}, status: "proposed",
  review_note: null, review_label: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.getProject).mockResolvedValue({
    id: 1, name: "Pocket", machine_profile_id: 2, alignment_status: "review_required",
  } as never);
  vi.mocked(api.listAlignmentRuns).mockResolvedValue([run] as never);
  vi.mocked(api.listCLRecords).mockResolvedValue([{
    id: 10, record_index: 1, line_number: 2, original_text: "LOADTL/8",
    command: "LOADTL", motion_type: null, tool_number: 8, parse_errors_json: [],
  }] as never);
  vi.mocked(api.listGCodeBlocks).mockResolvedValue([{
    id: 20, block_index: 1, line_number: 3, original_text: "T08 M06",
    g_codes_json: [], m_codes_json: ["M06"], motion_mode: null, tool_number: 8,
    parse_errors_json: [],
  }] as never);
  vi.mocked(api.listAlignmentLinks).mockResolvedValue([link] as never);
  vi.mocked(api.listAlignmentIssues).mockResolvedValue([]);
  vi.mocked(api.confirmAlignmentLink).mockResolvedValue({ ...link, status: "confirmed" } as never);
});

test("renders panels, selects relationship, and confirms a link", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/analyses/1/traceability"]}><Routes>
    <Route path="/analyses/:analysisId/traceability" element={<TraceabilityPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("LOADTL/8")).toBeInTheDocument();
  expect(screen.getByText("T08 M06")).toBeInTheDocument();
  await user.click(screen.getByText(/95%/));
  expect(screen.getByText("Tool numbers match")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Confirm" }));
  expect(api.confirmAlignmentLink).toHaveBeenCalledWith(7);
  expect(screen.getByRole("link", { name: "Export report" })).toHaveAttribute("href", "/report.md");
});

test("shows stale-run warning and failure state", async () => {
  vi.mocked(api.listAlignmentRuns).mockResolvedValue([{ ...run, stale: true }] as never);
  render(<MemoryRouter initialEntries={["/analyses/1/traceability"]}><Routes>
    <Route path="/analyses/:analysisId/traceability" element={<TraceabilityPage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText(/alignment is stale/)).toBeInTheDocument();
});
