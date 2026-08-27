import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { DashboardPage } from "./DashboardPage";

vi.mock("../api/client", () => ({ api: { listProfiles: vi.fn(), listDocuments: vi.fn(), listGPostDrafts: vi.fn(), getPostRecordSummary: vi.fn() } }));

beforeEach(() => {
  vi.mocked(api.listProfiles).mockResolvedValue([]);
  vi.mocked(api.listDocuments).mockResolvedValue([]);
  vi.mocked(api.listGPostDrafts).mockResolvedValue([]);
});

test("dashboard leads with Post Builder and three compact quick actions", async () => {
  render(<MemoryRouter><DashboardPage /></MemoryRouter>);
  await screen.findByText("Quick Actions");
  expect(screen.getAllByRole("link", { name: "Open Post Builder" })).toHaveLength(1);
  const quick = screen.getByRole("region", { name: "Quick actions" });
  expect(quick.querySelectorAll("a.button.secondary")).toHaveLength(3);
  expect(screen.queryByText("Validation Records")).not.toBeInTheDocument();
  expect(screen.queryByText("Site Standards")).not.toBeInTheDocument();
});
