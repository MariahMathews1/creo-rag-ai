import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { ResearchToolsPage } from "./ResearchToolsPage";

afterEach(() => vi.unstubAllEnvs());

test("research tools redirect to the dashboard when the developer flag is off", async () => {
  vi.stubEnv("VITE_ENABLE_RESEARCH_TOOLS", "false");
  render(<MemoryRouter initialEntries={["/research-tools"]}><Routes><Route path="/" element={<h1>Dashboard</h1>} /><Route path="/research-tools" element={<ResearchToolsPage />} /></Routes></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Research Tools" })).not.toBeInTheDocument();
});

test("research tools are available only when the developer flag is enabled", async () => {
  vi.stubEnv("VITE_ENABLE_RESEARCH_TOOLS", "true");
  render(<MemoryRouter initialEntries={["/research-tools"]}><ResearchToolsPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "Research Tools" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Translation Explorer/ })).toHaveAttribute("href", "/translations");
});
