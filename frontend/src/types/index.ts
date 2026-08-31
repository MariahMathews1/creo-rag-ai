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
  ai_post_builder_allowed: boolean;
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
  review_summary: string | null; created_at: string; updated_at: string; approved_at: string | null;
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
  mapping_count?: number;
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

export interface GPostPreflight {
  machine_ready: boolean; post_context_ready: boolean; cl_parse_status: string; cl_record_count: number;
  required_behavior_keys: string[]; supported_behavior_keys: string[]; reviewed_behavior_keys: string[];
  unreviewed_behavior_keys: string[]; unsupported_required_behaviors: string[];
  blocking_issues: Array<Record<string, unknown>>; warnings: Array<Record<string, unknown>>;
  generation_allowed: boolean; generation_allowed_with_warning: boolean;
}

export type TranslationStatus = "unknown" | "candidate" | "reviewed" | "verified_successful" | "deprecated" | "invalid";
export interface TranslationAlignmentLink {
  id: number; alignment_id: number; cl_record_start: number | null; cl_record_end: number | null;
  gcode_block_start: number | null; gcode_block_end: number | null; link_type: string;
  confidence: number; review_status: string; match_reasons_json: string[];
  notes: string | null; reviewed_by_label: string | null; created_at: string; updated_at: string;
}
export interface TranslationAlignment {
  id: number; translation_example_id: number; status: string; algorithm_version: string;
  summary_json: Record<string, number>; created_at: string; updated_at: string;
  links: TranslationAlignmentLink[];
}
export interface TranslationExample {
  id: number; machine_profile_id: number; machine_profile_revision_id: number; reference_program_id: number | null;
  name: string; description: string | null; controller_name: string | null; controller_version: string | null;
  post_processor_name: string | null; post_processor_revision: string | null;
  operation_type: string; operation_name: string | null; cl_source_text: string; cl_source_hash: string;
  cl_original_filename: string | null; gcode_source_text: string; gcode_source_hash: string;
  gcode_original_filename: string | null; verification_status: TranslationStatus;
  part_identifier: string | null; program_identifier: string | null; project_identifier: string | null;
  tooling_context_json: Record<string, unknown>; setup_context_json: Record<string, unknown>;
  machine_context_snapshot_json: Record<string, unknown>; source_system: string | null;
  source_repository: string | null; work_order_reference: string | null; imported_by_label: string | null;
  source_provenance: string | null; verification_basis: string | null; verification_note: string | null;
  cl_parse_summary_json: Record<string, number | boolean>; gcode_parse_summary_json: Record<string, number | boolean>;
  parsed_cl_records_json: Array<Record<string, unknown>>; parsed_gcode_blocks_json: Array<Record<string, unknown>>;
  validation_summary_json: { blocking_count?: number; warning_count?: number; informational_count?: number; findings?: Array<Record<string, unknown>> };
  ai_processing_allowed: boolean; created_at: string; updated_at: string; reviewed_at: string | null;
  verified_at: string | null; deprecated_at: string | null; alignments: TranslationAlignment[];
  advisory_only: true; safety_notice: string;
}
export interface TranslationDatasetSummary {
  total: number; candidates: number; reviewed: number; verified: number; deprecated: number; invalid: number;
  by_machine: Array<Record<string, number | string>>; by_post_revision: Array<Record<string, number | string>>;
  by_operation: Array<Record<string, number | string>>;
}
export interface TranslationExplorerGroup {
  machine_profile_id: number; machine: string; controller: string | null; post_revision: string | null;
  operation: string; cl_command: string; cl_pattern: string; gcode_pattern: string; count: number;
}
export interface TranslationPreview {
  cl_source_hash: string; gcode_source_hash: string;
  cl_parse_summary_json: Record<string, number | boolean>;
  gcode_parse_summary_json: Record<string, number | boolean>;
  validation_summary_json: { blocking_count: number; warning_count: number; informational_count: number; findings: Array<Record<string, unknown>> };
  machine_context_snapshot_json: Record<string, unknown>; revision_warning: string | null; advisory_only: true;
}
export interface TranslationAuditEvent {
  id: number; event_type: string; metadata_json: Record<string, unknown>; created_at: string;
}
export interface GPostHistoricalTranslationEvidence {
  mapping_id: number; machine_profile_id: number; cl_command: string; verified_example_count: number;
  observations: Array<{ translation_example_id: number; name: string; post_revision: string | null; operation: string; cl_pattern: string; gcode_pattern: string }>;
  read_only: true; mapping_changed: false;
}
export interface PostBuilderProviderStatus {
  provider: "disabled" | "mock" | "azure_openai"; configured: boolean; reachable: boolean | null;
  authentication_mode: string | null; deployment: string | null; model: string | null;
  external_processing: boolean; public_web: false; data_source: string; mode: "R&D Post Development";
  cl_ncl_ai_access: "prohibited"; error_code: string | null;
}
export interface PostBuilderSectionResponse {
  section_key: string; status: "draft" | "needs_machine_information";
  draft_rules: Array<{ rule_key: string; name: string; condition: string; output_behavior: string; evidence_reference_ids: number[]; review_status: "draft" }>;
  draft_templates: Array<Record<string, unknown>>; missing_information: string[]; assumptions: string[];
  source_reference_ids: number[]; warnings: string[]; provider_metadata: Record<string, unknown>;
  invocation_id: number; advisory_only: true; safety_notice: string;
}
export type PostSectionKey = "program_structure" | "tooling" | "spindle" | "coolant" | "feed" | "motion" | "coordinates" | "program_end" | "cycles";
export type PostSectionReadinessStatus = "ready" | "ready_with_review" | "needs_information" | "blocked" | "deferred";
export interface PostMachineFact { key: string; label: string; value: unknown; status: "known" | "needs_review" | "unknown" | "not_applicable"; critical: boolean; source: string; }
export interface PostSectionReadiness {
  section_key: PostSectionKey; label: string; readiness: PostSectionReadinessStatus;
  manual_setup_readiness: PostSectionReadinessStatus; ai_drafting_readiness: PostSectionReadinessStatus;
  known_machine_facts: PostMachineFact[]; missing_information: string[]; warnings: string[];
  conflicts: Array<Record<string, unknown>>; evidence_count: number; reviewed_rule_count: number;
  current_draft_status: string; draft_allowed: boolean;
}
export interface PostBuilderEvidence {
  evidence_id: number; document_id: number; document_title: string; document_type: string;
  page_start: number | null; page_end: number | null; section_title: string | null; excerpt: string;
  relevance_score: number; matched_terms: string[]; ai_eligible: boolean; conflict_labels: string[];
}
export interface PostRuleDraft {
  id: number; rule_key: string; name: string; description: string | null; condition: string; output_behavior: string;
  ai_draft_template: string | null; engineer_template: string | null; required_machine_facts_json: string[];
  evidence_ids_json: number[]; assumptions_json: string[]; warnings_json: string[]; status: string; engineering_classification?: "STANDARD_OFG" | "CUSTOM_LOGIC" | "SITE_STANDARD" | "UNKNOWN";
  review_reason: string | null; reviewer_label: string | null; reviewed_at: string | null; created_at: string; updated_at: string;
}
export interface PostSectionDraft {
  id: number; gpost_draft_id: number; section_key: PostSectionKey; section_version: number; status: string;
  source_type: string; machine_context_snapshot_json: Record<string, unknown>; draft_templates_json: Array<Record<string, unknown>>;
  missing_information_json: string[]; assumptions_json: string[]; warnings_json: string[];
  source_evidence_json: PostBuilderEvidence[]; ai_generated: boolean; provider: string | null; model: string | null;
  prompt_version: string | null; response_schema_version: string | null; reviewed_at: string | null;
  created_at: string; updated_at: string; rules: PostRuleDraft[]; advisory_only: true;
}
export interface PostSectionCompare { left_version: number; right_version: number; rules_added: string[]; rules_removed: string[]; templates_changed: string[]; evidence_changed: boolean; assumptions_changed: boolean; }
export interface AssembledPostComponent {
  section_key: PostSectionKey; label: string; state: "reviewed" | "needs_review" | "needs_information" | "not_started" | "deferred";
  required: boolean; section_version: number | null; rules: Array<{ rule_key: string; name: string; condition: string; template: string; status: string; evidence_ids: number[]; reviewer: string | null }>;
  missing_information: string[]; evidence_count: number;
}
export interface AssembledPostDraft {
  draft_id: number; name: string; status: "setup" | "building" | "needs_information" | "ready_for_review" | "reviewed_rnd_draft" | "archived";
  required_area_count: number; counts: Record<string, number>; components: AssembledPostComponent[];
  ready_for_complete_review: boolean; advisory_only: true; native_gpost_export: "not_configured";
}

export interface MachineKnowledgeFact {
  id: number; post_record_id: number; category: string; fact_key: string; name: string;
  value_json: unknown; unit: string | null; status: string; post_review_status: "available_from_machine" | "needs_information" | "reviewed_for_post" | "not_applicable"; source_document_id: number | null;
  source_label: string | null; source_location: string | null; reviewer: string | null;
  reviewed_at: string | null; review_note: string | null; created_at: string; updated_at: string;
  used_by: Array<{ type: string; id: number; label: string }>;
}

export interface ManualMachineInformationField {
  fact_key: string; label: string; category: string; data_type: string; units: string[];
}

export interface ManualMachineInformation {
  id: number; machine_profile_id: number; revision_id: number; fact_key: string; label: string; category: string;
  value: unknown; unit: string | null; source_basis: string; source_label: string; source_detail: string | null;
  notes: string | null; review_status: string; proposal_id: number | null;
}

export interface OFGSetting {
  id: number; post_record_id: number; category: string; setting_key: string; display_name: string;
  subsection: string | null;
  description: string | null; value_json: unknown; unit: string | null; status: string;
  source_machine_fact_ids_json: number[]; source_document_evidence_ids_json: number[];
  site_standard_ids_json: number[]; requires_custom_logic: boolean; custom_logic_id: number | null;
  ofg_menu_path: string | null; ofg_menu_path_status: string; reviewer: string | null;
  relevance_class: "core" | "conditional" | "advanced";
  relevance_label: "required_for_post" | "applicable" | "optional" | "not_applicable" | "advanced";
  is_applicable: boolean; user_selected: boolean;
  source_type: "Machine Knowledge" | "Controller Documentation" | "OFG Reference" | "Site Standard" | "Existing Post Reference" | "Engineer Entry" | "Unknown";
  source_reference: string | null; structured_value_json: unknown; code_status: "defined" | "not_available" | "not_required" | "unknown" | null;
  review_note: string | null; reviewed_at: string | null; created_at: string; updated_at: string;
  source_machine_facts: Array<{ id: number; name: string; value: unknown; status: string; source: string | null; source_location: string | null }>;
}

export interface SiteStandard {
  id: number; name: string; description: string | null; scope: string;
  applicable_machine_types_json: string[]; applicable_controller_families_json: string[];
  applicable_machine_ids_json: number[]; category: string; rule: string; validation_requirements_json: string[]; source: string | null;
  status: string; reviewer: string | null; version: number; effective_date: string | null;
  notes: string | null; created_at: string; updated_at: string;
}

export interface PostStandardApplication {
  id: number; post_record_id: number; site_standard_id: number; status: string;
  conflict_status: string; conflict_note: string | null; reviewer: string | null;
  review_note: string | null; created_at: string; updated_at: string; standard: SiteStandard;
}

export interface CustomLogicItem {
  id: number; post_record_id: number; related_ofg_setting_id: number | null; name: string; category: string; reason: string;
  desired_behavior: string | null; runtime_trigger: string | null;
  implementation_type: string; status: string; evidence_ids_json: number[]; site_standard_ids_json: number[];
  source_format: string; source_reference: string | null; reviewer: string | null;
  review_note: string | null; created_at: string; updated_at: string;
}

export interface PostOpenQuestion {
  id: number; post_record_id: number; question_type: string; title: string; description: string | null;
  severity: string; related_type: string | null; related_id: number | null; source_context: string | null;
  owner: string | null; status: string; resolution: string | null; created_at: string; updated_at: string;
}

export interface PostValidationRecord {
  id: number; post_record_id: number; post_version_id: number | null; validation_type: string;
  name: string | null;
  performed_by: string; performed_at: string; environment: string | null; result: string;
  notes: string | null; attachment_reference: string | null; external_tool: string | null;
  external_reference: string | null; test_program_name: string | null; findings_count: number;
  blocking_findings_count: number; references_json: string[]; ai_used: boolean; created_at: string;
}
export interface ValidationFinding {
  id: number; validation_record_id: number; severity: string; category: string; title: string;
  description: string | null; related_ofg_setting_id: number | null; related_custom_logic_id: number | null;
  related_site_standard_id: number | null; status: string; resolution_note: string | null;
  created_at: string; updated_at: string;
}
export interface ValidationPolicy {
  id: number; post_record_id: number; name: string; required_validation_types_json: string[];
  optional_validation_types_json: string[]; source: string | null; reviewer: string | null; updated_at: string;
}
export interface GPostDiagnostic {
  id: number; validation_record_id: number; severity: string; code: string | null; message: string;
  line_reference: number | null; source_reference: string | null; custom_logic_reference_id: number | null;
  raw_excerpt: string; created_at: string;
}
export interface ValidationTimeline {
  post_record_id: number; version: number; events: Array<{ id: number; type: string; name: string | null;
    result: string; performed_by: string; performed_at: string; findings_count: number }>;
}
export interface ValidationHandoff {
  post_record_id: number; post_version: number; machine: string; controller: string;
  current_validation_status: string; outstanding_configuration_issues: number; custom_fil_status: string;
  development_package_url: string; does_not_run_vericut: boolean;
  checklist: Array<{ key: string; label: string; complete: boolean }>;
}

export interface PostRecordSummary {
  post_record_id: number; status: string;
  machine_knowledge: { reviewed: number; total: number };
  ofg_configuration: { reviewed: number; total: number };
  site_standards: { applied: number; total: number; conflicts: number };
  custom_logic: { identified: number; reviewed: number };
  open_questions: { open: number; total: number };
  validation: { count: number; status: string; required_gates?: string[]; gate_status?: Record<string, string>;
    gates_satisfied?: boolean; open_findings?: number; stages?: Record<string, string> };
  blockers: Array<{ type: string; id: number; title: string; reason: string }>;
  next_action: { label: string; path: string };
  native_gpost_integration: { status: string; label: string; explanation: string };
}
export interface ToolpathPoint { x: number | null; y: number | null; z: number | null; a?: number | null; b?: number | null; c?: number | null; }
export interface ToolpathSegment {
  id: string; source_type: "cl" | "gcode"; source_record_id: number | null; source_line_start: number; source_line_end: number;
  operation_id: string | null; tool_number: number | null; motion_type: string; start_point: ToolpathPoint | null; end_point: ToolpathPoint | null;
  center_point: ToolpathPoint | null; radius: number | null; path_points: ToolpathPoint[]; plane: string | null;
  feed_rate: number | null; spindle_speed: number | null; rapid: boolean; arc_direction: string | null; helical: boolean;
  tool_axis: ToolpathPoint | null; alignment_link_id: number | null; aligned_segment_ids: string[]; finding_ids: number[];
  sequence_index: number; visualizable: boolean; unmatched: boolean; geometry_status: string | null; metadata_json: Record<string, unknown>;
}
export interface ToolpathResponse {
  source: string; machine_type: string; default_view: "XY" | "XZ" | "YZ"; coordinate_context: string;
  segments: ToolpathSegment[]; bounds: Record<string, number | null>; summary: Record<string, number | boolean>;
  warnings: Array<{ code: string; message: string; line?: number }>; comparison_summary: Record<string, number>;
  advisory_only: true; safety_notice: string;
}

export interface TranslationAIProviderStatus {
  provider: "disabled" | "mock" | "azure_openai"; configured: boolean; reachable: boolean | null;
  authentication_mode: string | null; deployment: string | null; model: string | null;
  external_processing: boolean; public_web: false; data_source: string; mode: "R&D"; error_code: string | null;
}
export interface TranslationRetrievalRequest {
  machine_profile_id: number; machine_profile_revision_id?: number | null; controller_name?: string | null;
  controller_version?: string | null; post_processor_name?: string | null; post_processor_revision?: string | null;
  operation_type?: string | null; cl_text: string; max_examples?: number;
  allow_revision_fallback?: boolean; allow_machine_family_fallback?: boolean;
}
export interface RetrievedTranslationExample {
  example_id: number; name: string; machine_profile_id: number; machine: string; machine_profile_revision_id: number;
  controller: string | null; post_revision: string | null; operation: string; cl_excerpt: string; gcode_excerpt: string;
  cl_pattern_match: "strong" | "related" | "none"; alignment_coverage: number; verification_status: string;
  retrieval_reasons: string[]; ai_processing_allowed: boolean;
}
export interface TranslationRetrievalResponse {
  retrieval_scope: string; examples: RetrievedTranslationExample[]; eligible_count: number;
  public_web: false; ai_called: false; warnings: string[];
}
export interface TranslationExplanationResponse {
  status: string; input_cl: string; interpreted_operation: string | null; suggested_mapping_pattern: string | null;
  short_rationale: string; example_ids: number[]; uncertainties: string[]; unsupported_features: string[];
  warnings: string[]; provider_metadata: Record<string, unknown>; invocation_id: number; advisory_only: true; safety_notice: string;
}
export interface TranslationAIInvocation {
  id: number; provider: string; operation_type: string; machine_profile_id: number; machine_profile_revision_id: number | null;
  translation_example_ids_json: number[]; input_hash: string; prompt_template_version: string; response_schema_version: string;
  response_status: string; external_processing: boolean; provider_metadata_json: Record<string, unknown>;
  token_usage_json: Record<string, number>; duration_ms: number | null; created_at: string;
}
