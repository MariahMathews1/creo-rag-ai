import type {
  AnalysisFinding,
  AnalysisProject,
  AnalysisRun,
  MachineProfile,
  MachineProfileInput,
  SourceDocument,
  DocumentContent,
  DocumentType,
  ManualQuestion,
  ManualSession,
  CLRecord, GCodeBlock, AlignmentRun, AlignmentLink, AlignmentIssue,
  ProfileExtractionRun, ProfileProposal, MachineProfileRevision,
  ProfileReviewQueue, ProfileReviewSummary, BatchReviewResult,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const isForm = options?.body instanceof FormData;
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: isForm
        ? options?.headers
        : { "Content-Type": "application/json", ...options?.headers },
    });
  } catch {
    throw new Error(
      "Backend unavailable. Confirm the API is running and try again.",
    );
  }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string"
          ? body.detail
          : typeof body.detail?.message === "string"
            ? body.detail.message
            : message;
    } catch {
      // Keep the HTTP fallback message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  listProfiles: () => request<MachineProfile[]>("/machines"),
  createProfile: (profile: MachineProfileInput) =>
    request<MachineProfile>("/machines", {
      method: "POST",
      body: JSON.stringify(profile),
    }),
  updateProfile: (id: number, profile: MachineProfileInput) =>
    request<MachineProfile>(`/machines/${id}`, {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
  deleteProfile: (id: number) =>
    request<void>(`/machines/${id}`, { method: "DELETE" }),
  listProjects: () => request<AnalysisProject[]>("/analyses"),
  getProject: (id: number) => request<AnalysisProject>(`/analyses/${id}`),
  createProject: (payload: {
    name: string;
    machine_profile_id: number;
    cl_source: string;
    gcode_source: string;
  }) =>
    request<AnalysisProject>("/analyses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runAnalysis: (id: number) =>
    request<AnalysisRun>(`/analyses/${id}/run`, { method: "POST" }),
  getFindings: (id: number) =>
    request<AnalysisFinding[]>(`/analyses/${id}/findings`),
  explain: (id: number, contentType: "gcode" | "cl" | "findings") =>
    request<{ advisory: boolean; explanation: string }>(
      `/analyses/${id}/ai-explanation`,
      { method: "POST", body: JSON.stringify({ content_type: contentType }) },
    ),
  listDocuments: (machineId: number) =>
    request<SourceDocument[]>(`/machines/${machineId}/documents`),
  uploadDocument: (
    machineId: number, title: string, documentType: DocumentType, file: File,
  ) => {
    const form = new FormData();
    form.append("title", title);
    form.append("document_type", documentType);
    form.append("file", file);
    return request<SourceDocument>(`/machines/${machineId}/documents`, {
      method: "POST", body: form,
    });
  },
  getDocumentContent: (id: number) =>
    request<DocumentContent>(`/documents/${id}/content`),
  deleteDocument: (id: number) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),
  reprocessDocument: (id: number) =>
    request<SourceDocument>(`/documents/${id}/reprocess`, { method: "POST" }),
  searchDocuments: (machineId: number, query: string) =>
    request<Array<{
      document_id: number; document_title: string; document_type: DocumentType;
      chunk_id: number; page_start: number | null; page_end: number | null;
      section_title: string | null; snippet: string;
    }>>(`/machines/${machineId}/documents/search?q=${encodeURIComponent(query)}`),
  listManualSessions: (machineId?: number) =>
    request<ManualSession[]>(
      `/manual-sessions${machineId ? `?machine_profile_id=${machineId}` : ""}`,
    ),
  createManualSession: (machineId: number, title: string) =>
    request<ManualSession>("/manual-sessions", {
      method: "POST", body: JSON.stringify({ machine_profile_id: machineId, title }),
    }),
  getManualSession: (id: number) =>
    request<ManualSession & { questions: ManualQuestion[] }>(`/manual-sessions/${id}`),
  askManualQuestion: (
    sessionId: number,
    payload: { question: string; document_types: DocumentType[]; category: string },
  ) => request<ManualQuestion>(`/manual-sessions/${sessionId}/questions`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  explainCommand: (machineId: number, command: string, context: string) =>
    request<ManualQuestion>(`/machines/${machineId}/explain-command`, {
      method: "POST", body: JSON.stringify({ command, context }),
    }),
  recordCitationOpen: (documentId: number) =>
    request<void>(`/documents/${documentId}/citation-open`, { method: "POST" }),
  parseCL: (analysisId: number) =>
    request(`/analyses/${analysisId}/parse-cl`, { method: "POST" }),
  parseGCode: (analysisId: number) =>
    request(`/analyses/${analysisId}/parse-gcode`, { method: "POST" }),
  listCLRecords: (analysisId: number, page = 1, pageSize = 200) =>
    request<CLRecord[]>(`/analyses/${analysisId}/cl-records?page=${page}&page_size=${pageSize}`),
  listGCodeBlocks: (analysisId: number, page = 1, pageSize = 200) =>
    request<GCodeBlock[]>(`/analyses/${analysisId}/gcode-blocks?page=${page}&page_size=${pageSize}`),
  createAlignmentRun: (analysisId: number) =>
    request<AlignmentRun>(`/analyses/${analysisId}/alignment-runs`, { method: "POST" }),
  listAlignmentRuns: (analysisId: number) =>
    request<AlignmentRun[]>(`/analyses/${analysisId}/alignment-runs`),
  listAlignmentLinks: (runId: number) =>
    request<AlignmentLink[]>(`/alignment-runs/${runId}/links`),
  listAlignmentIssues: (runId: number) =>
    request<AlignmentIssue[]>(`/alignment-runs/${runId}/issues`),
  confirmAlignmentLink: (linkId: number) =>
    request<AlignmentLink>(`/alignment-links/${linkId}/confirm`, { method: "POST" }),
  rejectAlignmentLink: (linkId: number) =>
    request<AlignmentLink>(`/alignment-links/${linkId}/reject`, { method: "POST" }),
  updateAlignmentLink: (linkId: number, payload: {
    status?: string; review_note?: string; review_label?: string;
  }) => request<AlignmentLink>(`/alignment-links/${linkId}`, {
    method: "PUT", body: JSON.stringify(payload),
  }),
  createManualAlignmentLink: (
    runId: number, clRecordId: number, gcodeBlockId: number,
  ) => request<AlignmentLink>(`/alignment-runs/${runId}/links`, {
    method: "POST",
    body: JSON.stringify({
      cl_record_id: clRecordId, gcode_block_id: gcodeBlockId,
      link_type: "manual", status: "modified",
    }),
  }),
  recalculateAlignment: (runId: number) =>
    request<AlignmentRun>(`/alignment-runs/${runId}/recalculate`, { method: "POST" }),
  alignmentReportUrl: (runId: number, format = "markdown") =>
    `${API_BASE_URL}/alignment-runs/${runId}/report?format=${format}`,
  startProfileExtraction: (machineId: number, payload: {
    document_ids: number[]; target_machine_type: string;
    selected_machine_variant: string | null; field_categories: string[];
  }) => request<ProfileExtractionRun>(`/machines/${machineId}/profile-extraction-runs`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  listProfileExtractions: (machineId: number) =>
    request<ProfileExtractionRun[]>(`/machines/${machineId}/profile-extraction-runs`),
  getProfileExtraction: (runId: number) =>
    request<ProfileExtractionRun>(`/profile-extraction-runs/${runId}`),
  listProfileProposals: (runId: number) =>
    request<ProfileProposal[]>(
      `/profile-extraction-runs/${runId}/proposals?page_size=250`,
    ),
  getProfileReviewSummary: (runId: number) =>
    request<ProfileReviewSummary>(
      `/profile-extraction-runs/${runId}/review-summary`,
    ),
  getProfileReviewQueue: (runId: number, params: URLSearchParams) =>
    request<ProfileReviewQueue>(
      `/profile-extraction-runs/${runId}/review-queue?${params.toString()}`,
    ),
  batchReviewProfileProposals: (
    runId: number,
    proposalIds: number[],
    action: "accept" | "defer" | "reject" | "not_applicable",
  ) => request<BatchReviewResult>(
    `/profile-extraction-runs/${runId}/proposals/batch-review`,
    {
      method: "POST",
      body: JSON.stringify({
        proposal_ids: proposalIds,
        action,
        confirmation: { acknowledge_advisory_only: action === "accept" },
      }),
    },
  ),
  acceptEligibleHighConfidence: (runId: number, proposalIds: number[]) =>
    request<BatchReviewResult>(
      `/profile-extraction-runs/${runId}/accept-eligible-high-confidence`,
      {
        method: "POST",
        body: JSON.stringify({
          proposal_ids: proposalIds,
          confirmation: { acknowledge_advisory_only: true },
        }),
      },
    ),
  recordProfileReviewEvent: (
    runId: number,
    payload: {
      event_type: string; queue?: string; proposal_id?: number;
      document_id?: number; selected_count?: number;
    },
  ) => request<void>(`/profile-extraction-runs/${runId}/review-events`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  rerunProfileExtraction: (runId: number, selectedVariant?: string) =>
    request<ProfileExtractionRun>(
      `/profile-extraction-runs/${runId}/rerun${selectedVariant ? `?selected_machine_variant=${encodeURIComponent(selectedVariant)}` : ""}`,
      { method: "POST" },
    ),
  reviewProfileProposal: (proposalId: number, payload: {
    review_status: string; reviewed_value?: unknown; unit?: string | null;
    review_note?: string;
  }) => request<ProfileProposal>(`/profile-field-proposals/${proposalId}/review`, {
    method: "PUT", body: JSON.stringify(payload),
  }),
  applyProfileDraft: (runId: number, payload: {
    base_strategy: "active" | "blank" | "selected_revision";
    source_revision_id?: number; review_summary?: string;
  }) => request<{ revision: MachineProfileRevision; comparison: Array<{
    field_key: string; current: unknown; proposed: unknown; changed: boolean;
  }>; applied_field_keys: string[] }>(`/profile-extraction-runs/${runId}/apply-to-draft`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  listProfileRevisions: (machineId: number) =>
    request<MachineProfileRevision[]>(`/machines/${machineId}/revisions`),
  submitProfileRevision: (revisionId: number) =>
    request<MachineProfileRevision>(`/machine-profile-revisions/${revisionId}/submit-for-review`, { method: "POST" }),
  approveProfileRevision: (revisionId: number, reviewNote: string) =>
    request<MachineProfileRevision>(`/machine-profile-revisions/${revisionId}/approve`, {
      method: "POST", body: JSON.stringify({
        exact_machine_applicability_confirmed: true,
        safety_notice_acknowledged: true, review_note: reviewNote,
      }),
    }),
  compareProfileRevisions: (left: number, right: number) =>
    request<{ fields: Array<{ field_key: string; current: unknown; proposed: unknown; changed: boolean }> }>(
      `/machine-profile-revisions/${left}/compare/${right}`,
    ),
};
