import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/client", () => ({ api: { listProfiles: vi.fn(), listProjects: vi.fn(), getTranslationSummary: vi.fn() } }));

beforeEach(() => {
  vi.mocked(api.listProfiles).mockResolvedValue([]);
  vi.mocked(api.listProjects).mockResolvedValue([]);
  vi.mocked(api.getTranslationSummary).mockResolvedValue({ total: 0, candidates: 0, reviewed: 0, verified: 0, deprecated: 0, invalid: 0, by_machine: [], by_post_revision: [], by_operation: [] });
});

test("dashboard has one G-POST CTA and four compact secondary quick actions", async () => {
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);
  await screen.findByText("Quick Actions");
  expect(screen.getAllByRole("link", { name: "Generate G-POST Draft" })).toHaveLength(1);
  const quick = screen.getByRole("region", { name: "Quick actions" });
  expect(quick.querySelectorAll("a.button.secondary")).toHaveLength(4);
});
