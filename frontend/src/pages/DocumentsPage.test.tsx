import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, test, vi } from "vitest";
import { api } from "../api/client";
import { DocumentsPage } from "./DocumentsPage";

vi.mock("../api/client", () => ({ api: {
  listProfiles: vi.fn(), listDocuments: vi.fn(), uploadDocument: vi.fn(),
  searchDocuments: vi.fn(), deleteDocument: vi.fn(), reprocessDocument: vi.fn(),
} }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listProfiles).mockResolvedValue([{ id: 1, name: "Demo Mill" } as never]);
  vi.mocked(api.listDocuments).mockResolvedValue([
    { id: 2, title: "Ready Manual", processing_status: "ready", document_type: "controller_manual", original_filename: "ready.md", file_size_bytes: 1000, page_count: 1, uploaded_at: "2026-01-01" },
    { id: 3, title: "Scanned Manual", processing_status: "failed", processing_error: "No extractable text was found. OCR may be required.", document_type: "machine_manual", original_filename: "scan.pdf", file_size_bytes: 2000, page_count: null, uploaded_at: "2026-01-01" },
  ] as never);
  vi.mocked(api.searchDocuments).mockResolvedValue([]);
});

test("shows upload form, processing statuses, and extraction failure", async () => {
  render(<MemoryRouter><DocumentsPage /></MemoryRouter>);
  expect(await screen.findByText("Ready Manual")).toBeInTheDocument();
  expect(screen.getByText(/No extractable text/)).toBeInTheDocument();
  expect(screen.getByLabelText("PDF, TXT, or MD file")).toBeInTheDocument();
  expect(screen.getByText(/ready$/, { selector: ".document-status" })).toBeInTheDocument();
  expect(screen.getByText(/failed$/, { selector: ".document-status" })).toBeInTheDocument();
  for (const heading of ["Document", "Machine", "Type", "Extraction Status", "AI Use", "Action"]) expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
  expect(screen.queryByText(/Review Eligibility/i)).not.toBeInTheDocument();
});

test("uploads a selected document", async () => {
  const user = userEvent.setup();
  vi.mocked(api.uploadDocument).mockResolvedValue({} as never);
  render(<MemoryRouter><DocumentsPage /></MemoryRouter>);
  await screen.findByText("Ready Manual");
  await user.type(screen.getByLabelText("Document title"), "New Manual");
  await user.upload(screen.getByLabelText("PDF, TXT, or MD file"), new File(["# G84"], "manual.md", { type: "text/markdown" }));
  expect(screen.getByRole("button", { name: "Upload and process" })).toBeEnabled();
  await act(async () => {
    fireEvent.submit(screen.getByRole("button", { name: "Upload and process" }).closest("form")!);
  });
  await vi.waitFor(() => expect(api.uploadDocument).toHaveBeenCalled());
  await vi.waitFor(() => expect(screen.getByLabelText("Document title")).toHaveValue(""));
});

test("reloads the document list when the machine filter changes", async () => {
  vi.mocked(api.listProfiles).mockResolvedValue([
    { id: 1, name: "Demo Mill" },
    { id: 2, name: "Second Mill" },
  ] as never);
  const user = userEvent.setup();
  render(<MemoryRouter><DocumentsPage /></MemoryRouter>);
  await screen.findByText("Ready Manual");
  await user.selectOptions(screen.getByLabelText("Machine profile"), "2");
  await vi.waitFor(() => expect(api.listDocuments).toHaveBeenCalledWith(2));
});

test("shows a backend failure state", async () => {
  vi.mocked(api.listDocuments).mockRejectedValue(new Error("Backend unavailable"));
  render(<MemoryRouter><DocumentsPage /></MemoryRouter>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
});
