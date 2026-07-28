import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { ManualAssistantPage } from "./ManualAssistantPage";

vi.mock("../api/client", () => ({ api: {
  listProfiles: vi.fn(), listManualSessions: vi.fn(), createManualSession: vi.fn(),
  getManualSession: vi.fn(), askManualQuestion: vi.fn(), recordCitationOpen: vi.fn(),
} }));

beforeEach(() => {
  vi.mocked(api.listProfiles).mockResolvedValue([{ id: 1, name: "Demo Mill" } as never]);
  vi.mocked(api.listManualSessions).mockResolvedValue([]);
  vi.mocked(api.createManualSession).mockResolvedValue({ id: 8, machine_profile_id: 1, title: "G84", updated_at: "2026-01-01" } as never);
  vi.mocked(api.getManualSession).mockResolvedValue({ questions: [] } as never);
});

test("submits a question and renders its citation", async () => {
  const answer = {
    id: 4, question: "Does G84 support tapping?", category: "cycle_support",
    answer_status: "answered", answer: "The uploaded manual states G84 is rigid tapping. [1]",
    unresolved_questions: [], safety_notice: "Qualified review required.",
    citations: [{ citation_number: 1, document_id: 5, document_title: "Controller Manual", document_type: "controller_manual", page_start: 12, section_title: "G84", excerpt: "G84 commands rigid tapping.", relevance_score: .91 }],
  };
  vi.mocked(api.askManualQuestion).mockResolvedValue(answer as never);
  vi.mocked(api.getManualSession).mockResolvedValue({ questions: [answer] } as never);
  const user = userEvent.setup();
  render(<MemoryRouter><ManualAssistantPage /></MemoryRouter>);
  await screen.findByRole("option", { name: "Demo Mill" });
  await user.type(screen.getByLabelText("Technical question"), "Does G84 support tapping?");
  await user.click(screen.getByRole("button", { name: "Retrieve grounded answer" }));
  expect(await screen.findByText("Controller Manual")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open source →" })).toHaveAttribute("href", expect.stringContaining("/documents/5"));
});

test("renders insufficient evidence without citations", async () => {
  const answer = {
    id: 5, question: "Laser probing?", category: "general",
    answer_status: "insufficient_evidence", answer: "The uploaded documents do not provide enough evidence.",
    unresolved_questions: [], safety_notice: "Qualified review required.", citations: [],
  };
  vi.mocked(api.askManualQuestion).mockResolvedValue(answer as never);
  vi.mocked(api.getManualSession).mockResolvedValue({ questions: [answer] } as never);
  const user = userEvent.setup();
  render(<MemoryRouter><ManualAssistantPage /></MemoryRouter>);
  await screen.findByRole("option", { name: "Demo Mill" });
  await user.type(screen.getByLabelText("Technical question"), "Laser probing?");
  await user.click(screen.getByRole("button", { name: "Retrieve grounded answer" }));
  expect(await screen.findByText(/do not provide enough evidence/)).toBeInTheDocument();
  expect(screen.getByText("No supporting citation met the evidence threshold.")).toBeInTheDocument();
});
