import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MachineProfileForm } from "./MachineProfileForm";

test("renders and submits the machine-profile creation form", async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn().mockResolvedValue(undefined);
  render(<MachineProfileForm onSubmit={onSubmit} onCancel={vi.fn()} />);
  expect(screen.getByLabelText("Profile name")).toBeInTheDocument();
  expect(screen.getByLabelText("X minimum")).toBeInTheDocument();
  expect(screen.getByLabelText("Approved G-codes")).toBeInTheDocument();
  expect(screen.getByLabelText("Safe-start template")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Profile name"), "Test Mill");
  await user.type(screen.getByLabelText("Manufacturer"), "Example");
  await user.type(screen.getByLabelText("Model"), "VM-1");
  await user.type(screen.getByLabelText("Controller name"), "Fanuc-style");
  await user.click(screen.getByRole("button", { name: "Create profile" }));
  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ name: "Test Mill", axis_count: 3 }),
  );
});
