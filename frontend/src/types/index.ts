export type Severity = "blocking" | "warning" | "informational";
export type MachineType =
  | "mill" | "lathe" | "mill-turn" | "turning_center" | "machining_center"
  | "vertical_mill" | "horizontal_mill" | "vertical_lathe" | "other";

export interface MachineProfile {
  id: number;
  name: string;
  manufacturer: string;
  model: string;
  controller_name: string;
  controller_manufacturer?: string | null;
  controller_model?: string | null;
  controller_version: string | null;
  machine_type: MachineType;
  axis_count: number;
  x_min: number | null;
  x_max: number | null;
  y_min: number | null;
  y_max: number | null;
  z_min: number | null;
  z_max: number | null;
  max_spindle_rpm: number | null;
  max_feed_rate: number | null;
  rapid_z_review_threshold: number | null;
  supported_work_offsets: string[];
  approved_g_codes: string[];
  approved_m_codes: string[];
  restricted_commands: string[];
  safe_start_template: string | null;
  tool_change_template: string | null;
  program_end_template: string | null;
  notes: string | null;
  active_revision_id: number | null;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export type MachineProfileInput = Omit<
  MachineProfile,
  "id" | "active_revision_id" | "archived_at" | "created_at" | "updated_at"
>;

export interface AnalysisProject {
  id: number;
  name: string;
  machine_profile_id: number;
  cl_source: string | null;
  gcode_source: string | null;
  status: "draft" | "passed" | "review_required" | "blocked";
  created_at: string;
  updated_at: string;
  advisory_only: true;
  safety_notice: string;
  cl_processing_status: string;
  gcode_processing_status: string;
  alignment_status: string;
  alignment_version: number;
  alignment_summary_json: Record<string, unknown>;
  machine_profile_revision_id: number | null;
  machine_profile_snapshot_json: Record<string, unknown>;
}

export interface CLRecord {
  id: number; record_index: number; line_number: number; original_text: string;
  normalized_text: string; command: string; original_command: string | null;
  parameters_json: unknown[]; coordinates_json: Record<string, number>;
  motion_type: string | null; tool_number: number | null; feed_rate: number | null;
  spindle_speed: number | null; coolant_state: string | null;
  operation_name: string | null; parse_errors_json: string[];
}

export interface GCodeBlock {
  id: number; block_index: number; line_number: number; original_text: string;
  cleaned_text: string; g_codes_json: string[]; m_codes_json: string[];
  coordinates_json: Record<string, number>; motion_mode: string | null;
  tool_number: number | null; active_tool: number | null; feed_rate: number | null;
  spindle_speed: number | null; parse_errors_json: string[];
}

export interface AlignmentLink {
  id: number; alignment_run_id: number; cl_record_id: number | null;
  gcode_block_id: number | null; link_type: string; confidence: number;
  match_reasons_json: string[]; mismatch_reasons_json: string[];
  score_components_json: Record<string, number>; status: string;
  review_note: string | null; review_label: string | null;
}

export interface AlignmentIssue {
  id: number; issue_type: string; severity: string; cl_record_id: number | null;
  gcode_block_id: number | null; title: string; description: string;
  recommendation: string;
}

export interface AlignmentRun {
  id: number; analysis_project_id: number; version: number; status: string;
  algorithm_version: string; settings_json: Record<string, unknown>;
  summary_json: Record<string, number | boolean>; metrics_json: Record<string, number>;
  stale: boolean; completed_at: string | null; advisory_only: true;
  alignment_is_inferred: true; manual_review_required: true; safety_notice: string;
}

export interface AnalysisFinding {
  id: number;
  analysis_project_id: number;
  severity: Severity;
  category: string;
  title: string;
  description: string;
  line_number: number | null;
  source_line: string | null;
  rule_id: string;
  recommendation: string;
  confidence: number;
  created_at: string;
}

export interface AnalysisRun {
  project: AnalysisProject;
  findings: AnalysisFinding[];
}

export type DocumentType =
  | "controller_manual" | "machine_manual" | "programming_manual"
  | "company_standard" | "approved_program" | "setup_document"
  | "post_processor_document" | "operator_manual" | "specification_document"
  | "maintenance_manual" | "parameter_list" | "machine_configuration_document"
  | "purchase_specification" | "other";

export interface SourceDocument {
  id: number;
  machine_profile_id: number;
  title: string;
  document_type: DocumentType;
  original_filename: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  file_hash: string | null;
  processing_status: "uploaded" | "processing" | "ready" | "failed";
  processing_error: string | null;
  page_count: number | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface DocumentChunk {
  id: number;
  chunk_index: number;
  page_start: number | null;
  page_end: number | null;
  section_title: string | null;
  content: string;
  content_hash: string;
  token_estimate: number;
}

export interface DocumentContent {
  document: SourceDocument;
  pages: Array<{ page_number: number; text: string; character_count: number }>;
  extracted_text: string | null;
  chunks: DocumentChunk[];
}

export interface ManualSession {
  id: number;
  machine_profile_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  citation_number: number;
  document_id: number;
  document_title: string;
  document_type: DocumentType;
  document_chunk_id: number;
  page_start: number | null;
  page_end: number | null;
  section_title: string | null;
  excerpt: string;
  relevance_score: number;
}

export interface ManualQuestion {
  id: number;
  session_id: number;
  question: string;
  category: string;
  answer_status: "answered" | "insufficient_evidence" | "failed";
  answer: string;
  unresolved_questions: string[];
  citations: Citation[];
  advisory_only: true;
  grounded_in_uploaded_documents: true;
  production_approval_required: true;
  safety_notice: string;
  created_at: string;
}

export interface ProfileEvidence {
  id: number; document_id: number; document_title: string; document_type: string; document_chunk_id: number; citation_number: number;
  page_start: number | null; page_end: number | null; section_title: string | null;
  excerpt: string; raw_value_text: string | null; unit: string | null;
  relevance_score: number; evidence_type: string;
}
export interface ProfileProposal {
  id: number; extraction_run_id: number; field_key: string; field_label: string;
  field_category: string; proposed_value_json: unknown; normalized_value_json: unknown;
  unit: string | null; confidence: number; proposal_status: string; review_status: string;
  reviewed_value_json: unknown; review_note: string | null;
  requires_exact_machine_verification: boolean; safety_relevant: boolean;
  interpretation_note: string | null; variant_applicability_json: string[];
  evidence: ProfileEvidence[];
}
export interface ProfileExtractionRun {
  id: number; machine_profile_id: number; target_revision_id: number | null;
  status: string; provider_name: string; selected_document_ids_json: number[];
  settings_json: Record<string, unknown>; summary_json: Record<string, number>;
  detected_variants_json: string[]; selected_machine_variant: string | null;
  started_at: string; completed_at: string | null; failure_message: string | null;
  advisory_only: true; machine_profile_is_draft: true; qualified_review_required: true;
  safety_notice: string;
}
export interface ReviewCategorySummary {
  category: string; total: number; reviewed: number; pending: number;
  conflicts: number; complete: boolean;
}
export interface ProfileReviewSummary {
  run_id: number; machine_profile_id: number; machine_name: string;
  selected_variant: string | null; run_status: string; documents_analyzed: number;
  total: number; found: number; not_found: number; conflicting: number;
  ambiguous: number; pending: number; accepted: number;
  accepted_with_edit: number; rejected: number; deferred: number;
  manually_entered: number; not_applicable: number; found_pending: number;
  not_found_pending: number; conflict_pending: number; ambiguous_pending: number;
  high_confidence_eligible: number; safety_low_confidence_pending: number;
  remaining_required_review: number; reviewed: number;
  review_progress_percent: number; documentation_coverage: number;
  category_summaries: ReviewCategorySummary[]; draft_ready: boolean;
  approval_ready: boolean; variant_rerun_required: boolean;
  readiness_reasons: string[]; recommended_next_queue: string | null;
  confidence_high_threshold: number; confidence_medium_threshold: number;
}
export interface ProfileReviewQueue {
  queue: string; total: number; page: number; page_size: number;
  items: ProfileProposal[];
}
export interface BatchReviewResult {
  succeeded: number[];
  failed: Array<{ proposal_id: number; reason: string }>;
  summary: ProfileReviewSummary;
}
export interface MachineProfileRevision {
  id: number; machine_profile_id: number; revision_number: number; status: string;
  source_type: string; name: string; manufacturer: string | null; model: string | null;
  controller_name: string | null; controller_version: string | null;
  controller_manufacturer: string | null; controller_model: string | null;
  machine_type: string | null; axis_count: number | null;
  x_min: number | null; x_max: number | null; y_min: number | null; y_max: number | null;
  z_min: number | null; z_max: number | null; max_spindle_rpm: number | null;
  max_feed_rate: number | null; rapid_traverse_rate: number | null;
  supported_work_offsets_json: string[]; restricted_commands_json: string[];
  approved_g_codes_json?: string[]; approved_m_codes_json?: string[];
  tool_change_template?: string | null; min_spindle_rpm?: number | null;
  units?: string | null; notes?: string | null;
  safe_start_template: string | null; program_end_template: string | null;
  capabilities_json: Record<string, unknown>; machine_configuration_json: Record<string, unknown>;
  review_summary: string | null; approved_at: string | null;
}

export interface ReferenceProgram {
  id: number; machine_profile_id: number; machine_profile_revision_id: number;
  source_document_id: number | null; name: string; description: string | null;
  original_filename: string | null; file_hash: string; program_number: string | null;
  program_type: string; controller_name: string | null; controller_version: string | null;
  controller_variant: string | null; post_processor_name: string | null;
  post_processor_version: string | null; post_processor_revision: string | null;
  part_identifier: string | null; operation_identifier: string | null;
  material: string | null; units: string | null; machine_variant: string | null;
  installed_options_json: string[]; approval_status: string; eligibility_status: string;
  eligibility_reason: string | null; approved_by_label: string | null;
  parsing_status: string; parser_version: string | null; rule_set_version: string | null;
  validation_summary_json: Record<string, unknown>; source_integrity_json: Record<string, unknown>;
  ai_processing_allowed: boolean; imported_at: string; updated_at: string;
  advisory_only: true; historical_similarity_is_not_certification: true;
  safety_notice: string;
}
export interface ConventionEvidence {
  id: number; reference_program_id: number; gcode_block_id: number | null;
  line_start: number | null; line_end: number | null; excerpt: string;
  evidence_type: string; match_context_json: Record<string, unknown>;
  program_name: string | null;
}
export interface StandardConvention {
  id: number; standard_profile_id: number | null; extraction_run_id: number | null;
  convention_key: string; category: string; title: string; description: string;
  convention_type: string; expected_pattern_json: Record<string, unknown>;
  condition_json: Record<string, unknown>; expected_behavior_json: Record<string, unknown>;
  applicability_json: Record<string, unknown>; severity: string; confidence: number;
  support_count: number; eligible_program_count: number; support_percentage: number;
  frequency_classification: string; proposal_status: string; review_status: string;
  review_note: string | null; safety_relevant: boolean; evidence: ConventionEvidence[];
}
export interface StandardExtractionRun {
  id: number; machine_profile_id: number; machine_profile_revision_id: number;
  status: string; selected_reference_program_ids_json: number[];
  algorithm_version: string; settings_json: Record<string, unknown>;
  summary_json: Record<string, unknown>; completed_at: string | null;
  advisory_only: true; historical_similarity_is_not_certification: true;
  safety_notice: string;
}
export interface StandardProfile {
  id: number; machine_profile_id: number; machine_profile_revision_id: number;
  name: string; revision_number: number; status: string;
  source_program_ids_json: number[]; summary_json: Record<string, unknown>;
  stale: boolean; stale_reasons_json: string[]; approved_at: string | null;
  conventions: StandardConvention[]; safety_notice: string;
}
export interface ComparisonFinding {
  id: number; comparison_run_id: number; standard_convention_id: number | null;
  severity: string; status: string; title: string; description: string;
  line_number: number | null; source_line: string | null;
  expected_pattern_json: Record<string, unknown>;
  observed_pattern_json: Record<string, unknown>; comparison_type: string;
  recommendation: string; exception_classification: string | null;
  exception_note: string | null;
}
export interface ProgramComparison {
  id: number; analysis_project_id: number; machine_profile_revision_id: number;
  standard_profile_id: number; reference_program_id: number | null; status: string;
  summary_json: Record<string, number | boolean>; parser_version: string;
  algorithm_version: string; stale: boolean; stale_reasons_json: string[];
  findings: ComparisonFinding[]; safety_notice: string;
}
export interface SimilarProgram {
  program: ReferenceProgram; similarity_score: number;
  match_reasons: string[]; differences: string[];
}
export interface SideBySideComparison {
  comparison_id: number; current_program: string; reference_program: string;
  sections: Array<{
    type: "common" | "added" | "removed" | "changed";
    reference_line_start: number; current_line_start: number;
    reference_lines: string[]; current_lines: string[];
  }>;
  source_metadata: Record<string, unknown>;
  deterministic_findings: Array<Record<string, unknown>>;
  convention_findings: ComparisonFinding[];
  safety_notice: string;
}

export interface GPostDraft {
  id: number; machine_profile_id: number; machine_profile_revision_id: number;
  created_from_draft_id: number | null; name: string; version: number;
  status: "draft" | "under_review" | "review_required" | "validated_for_rnd" | "superseded" | "archived";
  controller_family: string; machine_type: string;
  selected_document_ids_json: number[]; standard_profile_id: number | null;
  reference_program_ids_json: number[]; manual_configuration_acknowledged: boolean;
  capability_snapshot_json: Record<string, unknown>;
  machine_profile_snapshot_json: Record<string, unknown>; templates_json: Record<string, string>;
  unsupported_features_json: string[]; warnings_json: Array<Record<string, unknown>>;
  review_summary_json: Record<string, number>; created_at: string; updated_at: string;
  superseded_at: string | null; advisory_only: true; safety_notice: string;
}

export interface GPostEvidence {
  id: number; source_type: string; document_id: number | null;
  document_chunk_id: number | null; reference_program_id: number | null;
  standard_convention_id: number | null; page: number | null;
  section: string | null; excerpt: string | null; authority_level: string | null;
  metadata_json: Record<string, unknown>;
}

export interface GPostMapping {
  id: number; gpost_draft_id: number; mapping_key: string; cl_command: string;
  mapping_type: string; output_template: string | null;
  template_key: string | null; template_override: string | null; uses_override: boolean;
  effective_output_template: string | null;
  support_status: "supported" | "not_applicable" | "unsupported_required" | "not_implemented";
  required_for_v1: boolean; description: string | null;
  conditions_json: Record<string, unknown>; required_state_json: Record<string, unknown>;
  resulting_state_json: Record<string, unknown>; machine_type_scope: string | null;
  dialect_scope: string | null; supported: boolean; confidence: number | null;
  source_type: string; source_document_id: number | null; source_chunk_id: number | null;
  source_page: number | null; source_section: string | null; source_excerpt: string | null;
  source_authority: string | null; review_status: string; review_note: string | null;
  evidence: GPostEvidence[]; created_at: string; updated_at: string;
}

export interface GPostPreview {
  id: number; gpost_draft_id: number; status: string; generated_gcode: string;
  parser_diagnostics_json: string[]; deterministic_findings_json: Array<Record<string, unknown>>;
  unsupported_commands_json: Array<Record<string, unknown>>;
  missing_mappings_json: Array<Record<string, unknown>>; warnings_json: Array<Record<string, unknown>>;
  traceability_json: Array<Record<string, unknown>>; summary_json: Record<string, unknown>;
  parser_version: string; rule_set_version: string; created_at: string; safety_notice: string;
}

export interface GPostVersionDiff {
  left_draft_id: number; right_draft_id: number; mappings_added: string[];
  mappings_removed: string[]; templates_changed: string[]; conditions_changed: string[];
  evidence_changed: string[]; warnings_added: unknown[]; warnings_resolved: unknown[];
}
