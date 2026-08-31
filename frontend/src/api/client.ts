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
  ReferenceProgram, StandardConvention, StandardExtractionRun, StandardProfile,
  ProgramComparison, SimilarProgram, SideBySideComparison, ComparisonFinding,
  GPostDraft, GPostMapping, GPostPreview, GPostVersionDiff,
  TranslationExample, TranslationAlignment, TranslationAlignmentLink,
  TranslationDatasetSummary, TranslationExplorerGroup,
  GPostHistoricalTranslationEvidence,
  TranslationPreview, TranslationAuditEvent,
  ToolpathResponse,
  TranslationAIProviderStatus, TranslationRetrievalRequest, TranslationRetrievalResponse,
  TranslationExplanationResponse, TranslationAIInvocation,
  PostBuilderProviderStatus, PostBuilderSectionResponse,
  PostBuilderEvidence, PostRuleDraft, PostSectionCompare, PostSectionDraft, PostSectionReadiness,
  CustomLogicItem, MachineKnowledgeFact, ManualMachineInformation, ManualMachineInformationField, OFGSetting, PostOpenQuestion, PostRecordSummary,
  GPostDiagnostic, PostStandardApplication, PostValidationRecord, SiteStandard,
  ValidationFinding, ValidationHandoff, ValidationPolicy, ValidationTimeline,
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
  getPostRecordSummary: (id: number) => request<PostRecordSummary>(`/post-records/${id}/summary`),
  listMachineKnowledge: (id: number) => request<MachineKnowledgeFact[]>(`/post-records/${id}/machine-knowledge`),
  updateMachineKnowledge: (id: number, itemId: number, payload: Record<string, unknown>) => request<MachineKnowledgeFact>(`/post-records/${id}/machine-knowledge/${itemId}`, { method: "PUT", body: JSON.stringify(payload) }),
  listOFGSettings: (id: number, includeAdvanced = false) => request<OFGSetting[]>(`/post-records/${id}/ofg-settings?include_advanced=${includeAdvanced}`),
  createOFGSetting: (id: number, payload: Record<string, unknown>) => request<OFGSetting>(`/post-records/${id}/ofg-settings`, { method: "POST", body: JSON.stringify(payload) }),
  updateOFGSetting: (id: number, itemId: number, payload: Record<string, unknown>) => request<OFGSetting>(`/post-records/${id}/ofg-settings/${itemId}`, { method: "PUT", body: JSON.stringify(payload) }),
  listSiteStandards: () => request<SiteStandard[]>("/site-standards"),
  createSiteStandard: (payload: Record<string, unknown>) => request<SiteStandard>("/site-standards", { method: "POST", body: JSON.stringify(payload) }),
  listPostStandards: (id: number) => request<PostStandardApplication[]>(`/post-records/${id}/site-standards`),
  applySiteStandard: (id: number, payload: Record<string, unknown>) => request<PostStandardApplication>(`/post-records/${id}/site-standards`, { method: "POST", body: JSON.stringify(payload) }),
  updatePostStandard: (id: number, itemId: number, payload: Record<string, unknown>) => request<PostStandardApplication>(`/post-records/${id}/site-standards/${itemId}`, { method: "PUT", body: JSON.stringify(payload) }),
  listCustomLogic: (id: number) => request<CustomLogicItem[]>(`/post-records/${id}/custom-logic`),
  createCustomLogic: (id: number, payload: Record<string, unknown>) => request<CustomLogicItem>(`/post-records/${id}/custom-logic`, { method: "POST", body: JSON.stringify(payload) }),
  updateCustomLogic: (id: number, itemId: number, payload: Record<string, unknown>) => request<CustomLogicItem>(`/post-records/${id}/custom-logic/${itemId}`, { method: "PUT", body: JSON.stringify(payload) }),
  listPostQuestions: (id: number) => request<PostOpenQuestion[]>(`/post-records/${id}/open-questions`),
  createPostQuestion: (id: number, payload: Record<string, unknown>) => request<PostOpenQuestion>(`/post-records/${id}/open-questions`, { method: "POST", body: JSON.stringify(payload) }),
  updatePostQuestion: (id: number, itemId: number, payload: Record<string, unknown>) => request<PostOpenQuestion>(`/post-records/${id}/open-questions/${itemId}`, { method: "PUT", body: JSON.stringify(payload) }),
  listPostValidations: (id: number) => request<PostValidationRecord[]>(`/post-records/${id}/validation-records`),
  createPostValidation: (id: number, payload: Record<string, unknown>) => request<PostValidationRecord>(`/post-records/${id}/validation-records`, { method: "POST", body: JSON.stringify(payload) }),
  listValidationFindings: (id: number) => request<ValidationFinding[]>(`/post-records/${id}/validation-findings`),
  createValidationFinding: (id: number, validationId: number, payload: Record<string, unknown>) => request<ValidationFinding>(`/post-records/${id}/validation-records/${validationId}/findings`, { method: "POST", body: JSON.stringify(payload) }),
  updateValidationFinding: (id: number, findingId: number, payload: Record<string, unknown>) => request<ValidationFinding>(`/post-records/${id}/validation-findings/${findingId}`, { method: "PUT", body: JSON.stringify(payload) }),
  findingToOpenQuestion: (id: number, findingId: number) => request<PostOpenQuestion>(`/post-records/${id}/validation-findings/${findingId}/open-question`, { method: "POST" }),
  getValidationPolicy: (id: number) => request<ValidationPolicy>(`/post-records/${id}/validation-policy`),
  updateValidationPolicy: (id: number, payload: Record<string, unknown>) => request<ValidationPolicy>(`/post-records/${id}/validation-policy`, { method: "PUT", body: JSON.stringify(payload) }),
  getValidationTimeline: (id: number) => request<ValidationTimeline>(`/post-records/${id}/validation-timeline`),
  getValidationHandoff: (id: number) => request<ValidationHandoff>(`/post-records/${id}/validation-handoff`),
  listGPostDiagnostics: (id: number) => request<GPostDiagnostic[]>(`/post-records/${id}/diagnostics`),
  parseGPostDiagnostics: (id: number, validationId: number, listingText: string, fileName?: string) => request<GPostDiagnostic[]>(`/post-records/${id}/validation-records/${validationId}/diagnostics/parse`, { method: "POST", body: JSON.stringify({ listing_text: listingText, file_name: fileName || null, create_findings: true }) }),
  postDevelopmentPackageUrl: (id: number, format: "markdown" | "json" | "csv") => `${API_BASE_URL}/post-records/${id}/export?format=${format}`,
  comparePostRecords: (id: number, otherId: number) => request<Record<string, unknown>>(`/post-records/${id}/compare/${otherId}`),
  getPostSectionReadiness: (draftId: number) => request<PostSectionReadiness[]>(`/post-builder/${draftId}/readiness`),
  getAssembledPost: (draftId: number) => request<import("../types").AssembledPostDraft>(`/post-builder/${draftId}/assembled`),
  listPostSections: (draftId: number) => request<PostSectionDraft[]>(`/post-builder/${draftId}/sections`),
  getPostSection: (draftId: number, section: string) => request<PostSectionDraft>(`/post-builder/${draftId}/sections/${section}`),
  retrievePostBuilderEvidence: (draftId: number, section: string, query?: string) => request<PostBuilderEvidence[]>(`/post-builder/${draftId}/sections/${section}/retrieve-evidence`, { method: "POST", body: JSON.stringify({ query: query || null }) }),
  generatePostSection: (draftId: number, section: string, evidenceIds: number[], evidenceMode: "same" | "refresh" = "refresh") => request<PostSectionDraft>(`/post-builder/${draftId}/sections/${section}/draft`, { method: "POST", body: JSON.stringify({ evidence_ids: evidenceIds, evidence_mode: evidenceMode, context_reviewed: true }) }),
  reviewPostRule: (draftId: number, section: string, ruleId: number, action: "accept" | "edit-accept" | "reject" | "needs-information", payload: { reviewer_label: string; reason?: string | null; edited_template?: string | null }) => request<PostRuleDraft>(`/post-builder/${draftId}/sections/${section}/rules/${ruleId}/${action}`, { method: "POST", body: JSON.stringify(payload) }),
  listPostSectionVersions: (draftId: number, section: string) => request<PostSectionDraft[]>(`/post-builder/${draftId}/sections/${section}/versions`),
  comparePostSectionVersions: (draftId: number, section: string, left: number, right: number) => request<PostSectionCompare>(`/post-builder/${draftId}/sections/${section}/compare?left=${left}&right=${right}`),
  setDocumentPostBuilderPolicy: (documentId: number, allowed: boolean, reviewerLabel: string) => request<SourceDocument>(`/documents/${documentId}/post-builder-ai-policy`, { method: "POST", body: JSON.stringify({ allowed, reviewer_label: reviewerLabel, acknowledgement: true }) }),
  getPostBuilderProviderStatus: (checkReachability = false) => request<PostBuilderProviderStatus>(`/ai/post-builder/provider-status${checkReachability ? "?check_reachability=true" : ""}`),
  draftPostBuilderSection: (payload: { machine_profile_id: number; machine_profile_revision_id?: number | null; post_draft_id?: number | null; selected_post_section: string; existing_reviewed_rules?: Array<Record<string, unknown>>; relevant_document_excerpts?: Array<Record<string, unknown>> }) => request<PostBuilderSectionResponse>("/ai/post-builder/sections/draft", { method: "POST", body: JSON.stringify(payload) }),
  getTranslationAIProviderStatus: (checkReachability = false) => request<TranslationAIProviderStatus>(`/ai/translation/provider-status${checkReachability ? "?check_reachability=true" : ""}`),
  retrieveTranslationExamples: (payload: TranslationRetrievalRequest) => request<TranslationRetrievalResponse>("/ai/translation/retrieve", { method: "POST", body: JSON.stringify(payload) }),
  explainTranslation: (retrieval: TranslationRetrievalRequest, exampleIds: number[]) => request<TranslationExplanationResponse>("/ai/translation/explain", { method: "POST", body: JSON.stringify({ retrieval, example_ids: exampleIds }) }),
  listTranslationAIInvocations: (machineId?: number) => request<TranslationAIInvocation[]>(`/ai/translation/invocations${machineId ? `?machine_profile_id=${machineId}` : ""}`),
  setTranslationAIConsent: (exampleId: number, allowed: boolean, reviewerLabel: string, acknowledgement: boolean, note?: string) => request<TranslationExample>(`/translations/${exampleId}/ai-processing-consent`, { method: "POST", body: JSON.stringify({ allowed, reviewer_label: reviewerLabel, acknowledgement, note: note || null }) }),
  listProfiles: (includeArchived = false) => request<MachineProfile[]>(`/machines${includeArchived ? "?include_archived=true" : ""}`),
  getProfile: (id: number) => request<MachineProfile>(`/machines/${id}`),
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
  archiveProfile: (id: number) => request<MachineProfile>(`/machines/${id}/archive`, { method: "POST" }),
  restoreProfile: (id: number) => request<MachineProfile>(`/machines/${id}/restore`, { method: "POST" }),
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
  listManualMachineInformationFields: (machineId: number) => request<ManualMachineInformationField[]>(`/machines/${machineId}/machine-information/fields`),
  listManualMachineInformation: (machineId: number) => request<ManualMachineInformation[]>(`/machines/${machineId}/machine-information`),
  saveManualMachineInformation: (machineId: number, payload: Record<string, unknown>) => request<ManualMachineInformation>(`/machines/${machineId}/machine-information/manual`, { method: "POST", body: JSON.stringify(payload) }),
  discardMachineInformation: (machineId: number, fieldKey: string) => request<void>(`/machines/${machineId}/machine-information/${encodeURIComponent(fieldKey)}`, { method: "DELETE" }),
  getProfileExtraction: (runId: number) =>
    request<ProfileExtractionRun>(`/profile-extraction-runs/${runId}`),
  listProfileProposals: (runId: number) =>
    request<ProfileProposal[]>(
      `/profile-extraction-runs/${runId}/proposals?page_size=250`,
    ),
  getProfileProposal: (proposalId: number) => request<ProfileProposal>(`/profile-field-proposals/${proposalId}`),
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
  listReferencePrograms: (machineId: number) =>
    request<ReferenceProgram[]>(`/machines/${machineId}/reference-programs`),
  createReferenceProgram: (machineId: number, payload: Record<string, unknown>) =>
    request<ReferenceProgram>(`/machines/${machineId}/reference-programs`, {
      method: "POST", body: JSON.stringify(payload),
    }),
  updateReferenceProgram: (programId: number, payload: Record<string, unknown>) =>
    request<ReferenceProgram>(`/reference-programs/${programId}`, {
      method: "PUT", body: JSON.stringify(payload),
    }),
  parseReferenceProgram: (programId: number) =>
    request<ReferenceProgram>(`/reference-programs/${programId}/parse`, {
      method: "POST",
    }),
  markReferenceEligible: (programId: number, reason: string) =>
    request<ReferenceProgram>(`/reference-programs/${programId}/mark-eligible`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  markReferenceIneligible: (programId: number, reason: string) =>
    request<ReferenceProgram>(`/reference-programs/${programId}/mark-ineligible`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  startStandardExtraction: (machineId: number, payload: {
    machine_profile_revision_id: number; reference_program_ids: number[];
    post_processor_revision?: string;
  }) => request<StandardExtractionRun>(
    `/machines/${machineId}/standard-extraction-runs`,
    { method: "POST", body: JSON.stringify(payload) },
  ),
  listStandardExtractions: (machineId: number) =>
    request<StandardExtractionRun[]>(
      `/machines/${machineId}/standard-extraction-runs`,
    ),
  getStandardExtraction: (runId: number) =>
    request<StandardExtractionRun>(`/standard-extraction-runs/${runId}`),
  listStandardConventions: (runId: number) =>
    request<StandardConvention[]>(
      `/standard-extraction-runs/${runId}/proposals`,
    ),
  reviewStandardConvention: (
    conventionId: number,
    payload: {
      review_status: string; expected_pattern_json?: Record<string, unknown>;
      review_note?: string;
    },
  ) => request<StandardConvention>(`/standard-conventions/${conventionId}/review`, {
    method: "PUT", body: JSON.stringify(payload),
  }),
  batchReviewConventions: (
    runId: number, conventionIds: number[], reviewStatus: string,
  ) => request<{ succeeded: number[]; failed: Array<{
    convention_id: number; reason: string;
  }> }>(`/standard-extraction-runs/${runId}/proposals/batch-review`, {
    method: "POST",
    body: JSON.stringify({
      convention_ids: conventionIds, review_status: reviewStatus,
      acknowledge_frequency_is_not_requirement: reviewStatus === "accepted",
    }),
  }),
  createStandardDraft: (runId: number, name: string) =>
    request<StandardProfile>(`/standard-extraction-runs/${runId}/apply-to-draft`, {
      method: "POST", body: JSON.stringify({ name }),
    }),
  listStandards: (machineId: number) =>
    request<StandardProfile[]>(`/machines/${machineId}/standard-profiles`),
  getStandard: (standardId: number) =>
    request<StandardProfile>(`/standard-profiles/${standardId}`),
  submitStandard: (standardId: number, note: string) =>
    request<StandardProfile>(`/standard-profiles/${standardId}/submit-for-review`, {
      method: "POST", body: JSON.stringify({ note }),
    }),
  approveStandard: (standardId: number, note: string) =>
    request<StandardProfile>(`/standard-profiles/${standardId}/approve`, {
      method: "POST", body: JSON.stringify({ note }),
    }),
  createStandardComparison: (
    analysisId: number, standardProfileId: number, referenceProgramId?: number,
  ) => request<ProgramComparison>(`/analyses/${analysisId}/standard-comparisons`, {
    method: "POST",
    body: JSON.stringify({
      standard_profile_id: standardProfileId,
      reference_program_id: referenceProgramId,
    }),
  }),
  listStandardComparisons: (analysisId: number) =>
    request<ProgramComparison[]>(`/analyses/${analysisId}/standard-comparisons`),
  getStandardComparison: (comparisonId: number) =>
    request<ProgramComparison>(`/standard-comparisons/${comparisonId}`),
  getComparisonFindings: (comparisonId: number) =>
    request<ComparisonFinding[]>(`/standard-comparisons/${comparisonId}/findings`),
  getSideBySideComparison: (comparisonId: number) =>
    request<SideBySideComparison>(
      `/standard-comparisons/${comparisonId}/side-by-side`,
    ),
  classifyComparisonException: (
    findingId: number, classification: string, note: string,
  ) => request<ComparisonFinding>(
    `/standard-comparison-findings/${findingId}/exception`,
    { method: "PUT", body: JSON.stringify({ classification, note }) },
  ),
  listSimilarPrograms: (analysisId: number) =>
    request<SimilarProgram[]>(`/analyses/${analysisId}/similar-reference-programs`),
  standardReportUrl: (standardId: number, format = "markdown") =>
    `${API_BASE_URL}/standard-profiles/${standardId}/report?format=${format}`,
  comparisonReportUrl: (comparisonId: number, format = "markdown") =>
    `${API_BASE_URL}/standard-comparisons/${comparisonId}/report?format=${format}`,
  listGPostDrafts: (machineId: number) =>
    request<GPostDraft[]>(`/machines/${machineId}/gpost-drafts`),
  getGPostDraft: (draftId: number) => request<GPostDraft>(`/gpost-drafts/${draftId}`),
  createGPostDraft: (machineId: number, payload: {
    machine_profile_revision_id: number; name: string; controller_family: string;
    selected_document_ids: number[]; standard_profile_id?: number;
    reference_program_ids: number[]; manual_configuration_acknowledged?: boolean;
  }) => request<GPostDraft>(`/machines/${machineId}/gpost-drafts`, {
    method: "POST", body: JSON.stringify(payload),
  }),
  updateGPostDraft: (draftId: number, payload: Record<string, unknown>) =>
    request<GPostDraft>(`/gpost-drafts/${draftId}`, {
      method: "PUT", body: JSON.stringify(payload),
    }),
  createGPostVersion: (draftId: number) => request<GPostDraft>(
    `/gpost-drafts/${draftId}/versions`, { method: "POST" },
  ),
  listGPostVersions: (draftId: number) => request<GPostDraft[]>(`/gpost-drafts/${draftId}/versions`),
  duplicateGPostDraft: (draftId: number) => request<GPostDraft>(`/gpost-drafts/${draftId}/duplicate`, { method: "POST" }),
  deleteGPostDraft: (draftId: number) => request<void>(`/gpost-drafts/${draftId}`, { method: "DELETE" }),
  archiveGPostDraft: (draftId: number) => request<GPostDraft>(
    `/gpost-drafts/${draftId}/archive`, { method: "POST" },
  ),
  listGPostMappings: (draftId: number) =>
    request<GPostMapping[]>(`/gpost-drafts/${draftId}/mappings`),
  updateGPostMapping: (mappingId: number, payload: Record<string, unknown>) =>
    request<GPostMapping>(`/gpost-mappings/${mappingId}`, {
      method: "PUT", body: JSON.stringify(payload),
    }),
  resetGPostMappingOverride: (mappingId: number) =>
    request<GPostMapping>(`/gpost-mappings/${mappingId}/reset-override`, { method: "POST" }),
  addGPostEvidence: (mappingId: number, payload: Record<string, unknown>) =>
    request(`/gpost-mappings/${mappingId}/evidence`, {
      method: "POST", body: JSON.stringify(payload),
    }),
  preflightGPost: (draftId: number, clSource: string) =>
    request<import("../types").GPostPreflight>(`/gpost-drafts/${draftId}/preflight`, {
      method: "POST", body: JSON.stringify({ cl_source: clSource }),
    }),
  previewGPost: (draftId: number, clSource: string) =>
    request<GPostPreview>(`/gpost-drafts/${draftId}/preview`, {
      method: "POST", body: JSON.stringify({ cl_source: clSource }),
    }),
  compareGPostVersions: (draftId: number, otherDraftId: number) =>
    request<GPostVersionDiff>(`/gpost-drafts/${draftId}/compare/${otherDraftId}`),
  validateGPostForRnd: (draftId: number) => request<GPostDraft>(
    `/gpost-drafts/${draftId}/validate-for-rnd`, {
      method: "POST", body: JSON.stringify({ acknowledge_rnd_only: true }),
    },
  ),
  gpostExportUrl: (draftId: number, format: "json" | "markdown") =>
    `${API_BASE_URL}/gpost-drafts/${draftId}/export?format=${format}`,
  listTranslations: (params = new URLSearchParams()) =>
    request<TranslationExample[]>(`/translations${params.size ? `?${params}` : ""}`),
  getTranslation: (id: number) => request<TranslationExample>(`/translations/${id}`),
  getTranslationSummary: () => request<TranslationDatasetSummary>("/translations/summary"),
  getTranslationExplorer: (params = new URLSearchParams()) =>
    request<TranslationExplorerGroup[]>(`/translations/explorer${params.size ? `?${params}` : ""}`),
  createTranslation: (payload: Record<string, unknown>) => request<TranslationExample>("/translations", {
    method: "POST", body: JSON.stringify(payload),
  }),
  previewTranslation: (payload: { machine_profile_id: number; machine_profile_revision_id: number; cl_source_text: string; gcode_source_text: string }) => request<TranslationPreview>("/translations/preview", { method: "POST", body: JSON.stringify(payload) }),
  getTranslationHistory: (id: number) => request<TranslationAuditEvent[]>(`/translations/${id}/history`),
  getAnalysisToolpath: (id: number, source = "both") => request<ToolpathResponse>(`/analyses/${id}/toolpath?source=${source}`),
  getTranslationToolpath: (id: number, source = "both") => request<ToolpathResponse>(`/translations/${id}/toolpath?source=${source}`),
  getGPostPreviewToolpath: (id: number, source = "both") => request<ToolpathResponse>(`/gpost-preview-runs/${id}/toolpath?source=${source}`),
  getGPostHistoricalTranslationEvidence: (mappingId: number) => request<GPostHistoricalTranslationEvidence>(`/gpost-mappings/${mappingId}/historical-translation-evidence`),
  importTranslation: (metadata: Record<string, unknown>, clFile: File, gcodeFile: File) => {
    const form = new FormData(); form.append("metadata_json", JSON.stringify(metadata));
    form.append("cl_file", clFile); form.append("gcode_file", gcodeFile);
    return request<TranslationExample>("/translations/import", { method: "POST", body: form });
  },
  createTranslationAlignment: (id: number) => request<TranslationAlignment>(`/translations/${id}/alignment`, { method: "POST" }),
  confirmTranslationLink: (id: number) => request<TranslationAlignmentLink>(`/translation-alignment-links/${id}/confirm`, { method: "POST" }),
  rejectTranslationLink: (id: number) => request<TranslationAlignmentLink>(`/translation-alignment-links/${id}/reject`, { method: "POST" }),
  updateTranslationLink: (id: number, payload: Record<string, unknown>) => request<TranslationAlignmentLink>(`/translation-alignment-links/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  createManualTranslationLink: (alignmentId: number, payload: Record<string, unknown>) => request<TranslationAlignmentLink>(`/translation-alignments/${alignmentId}/links`, { method: "POST", body: JSON.stringify(payload) }),
  transitionTranslation: (id: number, action: "candidate" | "review" | "verify" | "deprecate" | "invalidate", payload: { note: string; reviewer_label: string; acknowledgement?: boolean }) =>
    request<TranslationExample>(`/translations/${id}/${action}`, { method: "POST", body: JSON.stringify(payload) }),
};
