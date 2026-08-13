import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { ActionMenu } from "./ActionMenu";

test("action menu manages focus, keyboard navigation, selection, and Escape", async () => {
  const user = userEvent.setup(); const select = vi.fn();
  render(<MemoryRouter><ActionMenu label="More" items={[{ label: "Edit Machine", onSelect: select }, { label: "Configuration History", to: "/history" }, { label: "Delete Machine", danger: true, divider: true, onSelect: vi.fn() }]} /></MemoryRouter>);
  const trigger = screen.getByRole("button", { name: "More" });
  await user.click(trigger);
  expect(screen.getByRole("menu").parentElement).toBe(document.body);
  expect(screen.getByRole("menuitem", { name: "Edit Machine" })).toHaveFocus();
  await user.keyboard("{ArrowDown}");
  expect(screen.getByRole("menuitem", { name: "Configuration History" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  expect(trigger).toHaveFocus();
  await user.click(trigger); await user.click(screen.getByRole("menuitem", { name: "Edit Machine" }));
  expect(select).toHaveBeenCalledOnce();
});

test("action menu closes on outside interaction and marks active navigation", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><div style={{ overflow: "hidden" }} data-testid="overflow-parent"><ActionMenu label="Advanced" active items={[{ label: "Templates", to: "/templates", active: true }, { label: "Mappings", to: "/mappings" }]} /></div></MemoryRouter>);
  const trigger = screen.getByRole("button", { name: "Advanced" });
  expect(trigger).toHaveClass("active");
  await user.click(trigger);
  const menu = screen.getByRole("menu");
  expect(menu.parentElement).toBe(document.body);
  expect(screen.getByRole("menuitem", { name: "Templates" })).toHaveAttribute("aria-current", "page");
  await user.click(document.body);
  expect(screen.queryByRole("menu")).not.toBeInTheDocument();
});
