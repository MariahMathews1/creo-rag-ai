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
  safe_start_template: string | null; program_end_template: string | null;
  capabilities_json: Record<string, unknown>; machine_configuration_json: Record<string, unknown>;
  review_summary: string | null; approved_at: string | null;
}
