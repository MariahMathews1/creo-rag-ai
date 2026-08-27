import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";
import { api } from "../api/client";
import { MachineDetailPage } from "./MachineDetailPage";
import { MachineProfilesPage } from "./MachineProfilesPage";

vi.mock("../api/client", () => ({ api: {
  listProfiles: vi.fn(), getProfile: vi.fn(), listDocuments: vi.fn(), listGPostDrafts: vi.fn(), listMachineKnowledge: vi.fn(), listPostQuestions: vi.fn(),
  updateProfile: vi.fn(), createProfile: vi.fn(), deleteProfile: vi.fn(), archiveProfile: vi.fn(), restoreProfile: vi.fn(), updateMachineKnowledge: vi.fn(),
} }));

const base = {
  controller_manufacturer: null, controller_model: null, controller_version: null, axis_count: 3,
  x_min: null, x_max: null, y_min: null, y_max: null, z_min: null, z_max: null,
  max_spindle_rpm: null, max_feed_rate: null, rapid_z_review_threshold: 0,
  supported_work_offsets: [], approved_g_codes: [], approved_m_codes: [], restricted_commands: [],
  safe_start_template: null, tool_change_template: null, program_end_template: null,
  active_revision_id: 1, archived_at: null, created_at: "2026-08-01", updated_at: "2026-08-01",
};
const profiles = [
  { ...base, id: 1, name: "KENT USA KLS-1840N", manufacturer: "KENT USA", model: "KLS-1840N", machine_type: "lathe", controller_name: "FANUC", notes: "" },
  { ...base, id: 2, name: "Fictional KLS Demo", manufacturer: "Fictional", model: "KLS Demo", machine_type: "lathe", controller_name: "FANUC", notes: "DEMO" },
  { ...base, id: 3, name: "Review Mill", manufacturer: "Acme", model: "M1", machine_type: "mill", controller_name: "FANUC", notes: "" },
  { ...base, id: 4, name: "Empty Mill", manufacturer: "Acme", model: "M2", machine_type: "mill", controller_name: "FANUC", notes: "" },
  { ...base, id: 5, name: "Archived Lathe", manufacturer: "Acme", model: "A1", machine_type: "lathe", controller_name: "FANUC", notes: "", archived_at: "2026-08-20" },
];
const post = (machineId: number) => ({ id: machineId * 10, machine_profile_id: machineId, name: `Post ${machineId}`, status: "review_required" });
const fact = (status: string, id: number) => ({ id, post_record_id: Math.floor(id / 10) * 10, category: "Spindle", fact_key: `fact_${id}`, name: `Fact ${id}`, value_json: 1, unit: null, status, source_document_id: null, source_label: null, source_location: null, used_by: [] });

function renderPage() {
  return render(<MemoryRouter initialEntries={["/machines"]}><Routes>
    <Route path="/machines" element={<MachineProfilesPage />} />
    <Route path="/machines/:machineId/:view?" element={<MachineDetailPage />} />
  </Routes></MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks(); vi.mocked(api.listProfiles).mockResolvedValue(profiles as never); vi.mocked(api.listDocuments).mockResolvedValue([]);
  vi.mocked(api.listGPostDrafts).mockImplementation(async (id) => id === 4 || id === 5 ? [] as never : [post(id)] as never);
  vi.mocked(api.listMachineKnowledge).mockImplementation(async (id) => id === 10 ? [fact("confirmed", 101)] as never : id === 20 ? [fact("unknown", 201), fact("unknown", 202), fact("unknown", 203)] as never : [fact("needs_review", 301)] as never);
  vi.mocked(api.listPostQuestions).mockResolvedValue([]); vi.mocked(api.archiveProfile).mockResolvedValue({} as never); vi.mocked(api.restoreProfile).mockResolvedValue({} as never);
});

test("machines table stays compact and defaults to active machines", async () => {
  renderPage(); expect(await screen.findByText("KENT USA KLS-1840N")).toBeInTheDocument();
  for (const heading of ["Machine", "Type", "Controller", "Documents", "Knowledge", "Posts", "Action"]) expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
  expect(screen.queryByText("Archived Lathe")).not.toBeInTheDocument();
  expect(screen.getByText("Ready")).toBeInTheDocument(); expect(screen.getByText("Needs 3 Facts")).toBeInTheDocument(); expect(screen.getByText("Needs Review")).toBeInTheDocument(); expect(screen.getByText("No Knowledge")).toBeInTheDocument();
  expect(screen.getByText("DEMO")).toBeInTheDocument(); expect(screen.getAllByRole("link", { name: "Open →" })).toHaveLength(4);
  expect(screen.getAllByRole("button", { name: /More actions for/ })).toHaveLength(4);
  expect(api.listProfiles).toHaveBeenCalledWith(true);
});

test("Active, Archived, and All filters preserve archived rows", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByText("KENT USA KLS-1840N");
  await user.click(screen.getByRole("button", { name: "Archived" }));
  expect(screen.getByText("Archived Lathe")).toBeInTheDocument(); expect(screen.getByText("ARCHIVED")).toBeInTheDocument(); expect(screen.queryByText("Empty Mill")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "All" }));
  expect(screen.getByText("Archived Lathe")).toBeInTheDocument(); expect(screen.getByText("Empty Mill")).toBeInTheDocument();
});

test("row More menu edits and archives without adding large row buttons", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByText("KENT USA KLS-1840N");
  await user.click(screen.getByRole("button", { name: "More actions for Empty Mill" }));
  for (const item of ["Edit Machine", "Create Post", "Archive Machine", "Delete Machine"]) expect(screen.getByRole("menuitem", { name: item })).toBeInTheDocument();
  await user.click(screen.getByRole("menuitem", { name: "Edit Machine" }));
  expect(screen.getByRole("heading", { name: "Edit Machine" })).toBeInTheDocument();
  expect(screen.getByLabelText("Machine Name")).toHaveValue("Empty Mill");
  expect(screen.queryByLabelText("Axis count")).not.toBeInTheDocument();
  await user.clear(screen.getByLabelText("Machine Name")); await user.type(screen.getByLabelText("Machine Name"), "Edited Empty Mill");
  vi.mocked(api.updateProfile).mockResolvedValue({} as never); await user.click(screen.getByRole("button", { name: "Save Changes" }));
  expect(api.updateProfile).toHaveBeenCalledWith(4, expect.objectContaining({ name: "Edited Empty Mill", manufacturer: "Acme", model: "M2" }));
});

test("Archive Machine uses the lifecycle endpoint", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByText("Empty Mill");
  await user.click(screen.getByRole("button", { name: "More actions for Empty Mill" })); await user.click(screen.getByRole("menuitem", { name: "Archive Machine" }));
  await vi.waitFor(() => expect(api.archiveProfile).toHaveBeenCalledWith(4));
});

test("Create Post routes into creation with the machine preselected", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByText("Empty Mill");
  await user.click(screen.getByRole("button", { name: "More actions for Empty Mill" }));
  expect(screen.getByRole("menuitem", { name: "Create Post" })).toHaveAttribute("href", "/gpost?machine=4");
});

test("Delete Machine requires confirmation", async () => {
  const user = userEvent.setup(); vi.mocked(api.deleteProfile).mockResolvedValue(undefined); renderPage(); await screen.findByText("Empty Mill");
  await user.click(screen.getByRole("button", { name: "More actions for Empty Mill" })); await user.click(screen.getByRole("menuitem", { name: "Delete Machine" }));
  const dialog = screen.getByRole("dialog", { name: "Delete “Empty Mill”?" });
  expect(within(dialog).getByText(/cannot be undone/)).toBeInTheDocument(); expect(api.deleteProfile).not.toHaveBeenCalled();
  await user.click(within(dialog).getByRole("button", { name: "Delete Machine" }));
  expect(api.deleteProfile).toHaveBeenCalledWith(4);
});

test("dependent Post Records block delete and offer Archive Machine", async () => {
  const user = userEvent.setup(); renderPage(); await screen.findByText("KENT USA KLS-1840N");
  await user.click(screen.getByRole("button", { name: "More actions for KENT USA KLS-1840N" })); await user.click(screen.getByRole("menuitem", { name: "Delete Machine" }));
  const dialog = screen.getByRole("dialog", { name: "Delete “KENT USA KLS-1840N”?" });
  expect(within(dialog).getByText("This machine has 1 Post Records and cannot be deleted. Archive it instead or resolve the dependent records.")).toBeInTheDocument();
  expect(within(dialog).queryByRole("button", { name: "Delete Machine" })).not.toBeInTheDocument();
  await user.click(within(dialog).getByRole("button", { name: "Archive Machine" })); expect(api.archiveProfile).toHaveBeenCalledWith(1);
});

test("Add Machine uses the simple form and routes to Upload machine documentation", async () => {
  const user = userEvent.setup(); const created = { ...base, id: 9, name: "New Lathe", manufacturer: "Acme", model: "NL-1", machine_type: "lathe", controller_name: "FANUC", notes: null };
  vi.mocked(api.createProfile).mockResolvedValue(created as never); vi.mocked(api.getProfile).mockResolvedValue(created as never);
  renderPage(); await screen.findByText("KENT USA KLS-1840N"); await user.click(screen.getByRole("button", { name: "+ Add Machine" }));
  for (const label of ["Machine Name", "Manufacturer", "Model", "Machine Type", "Controller", /Notes/]) expect(screen.getByLabelText(label)).toBeInTheDocument();
  await user.type(screen.getByLabelText("Machine Name"), "New Lathe"); await user.type(screen.getByLabelText("Manufacturer"), "Acme"); await user.type(screen.getByLabelText("Model"), "NL-1"); await user.selectOptions(screen.getByLabelText("Machine Type"), "lathe"); await user.type(screen.getByLabelText("Controller"), "FANUC");
  await user.click(screen.getByRole("button", { name: "Create Machine" }));
  expect(await screen.findByRole("heading", { name: "Upload machine documentation." })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Upload Documents" })).toHaveAttribute("href", "/documents?machine=9");
});
