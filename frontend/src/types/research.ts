import type { IndicatorResult } from './indicators'
export interface ResearchDraft { question: string; hypothesis: string; horizon: string }
export interface ResearchProject {
  id: number; security_id: number; question: string; hypothesis: string | null; horizon: string | null
  status: 'active' | 'archived'; version: number; created_at: string; updated_at: string
}
export interface ResearchEvidence {
  evidence_id: string; kind: string; content: Record<string, unknown>; source_name: string | null; source_url: string | null
  observed_at: string | null; published_at: string | null; retrieved_at: string | null; unit: string | null; price_basis: string
  provenance_known: boolean; title_only: boolean; dataset_source_key?: string | null; field_units?: Record<string, string>
  source_time_note?: string; provenance_warnings?: string[]; health?: string; context_disclosures?: string[]
}
export interface ResearchSnapshot {
  snapshot_version: string; as_of_snapshot: string
  project: { id: number; version: number; question: string; hypothesis: string | null; horizon: string | null }
  security: { id: number; market: string; code: string; name: string }
  metadata: Record<string, unknown>; ledger: ResearchEvidence[]; metrics: IndicatorResult[]
  data_gaps: string[]; context: Record<string, unknown>
}
export interface ResearchClaim {
  kind: 'fact' | 'inference' | 'hypothesis'; statement: string; evidence_ids: string[]; counter_evidence_ids: string[]
  metric_refs: { metric_key: string; reported_value: string | null }[]
}
export interface ResearchCondition { description: string; metric_key: string | null; operator: string | null; threshold: string | null }
export interface ResearchOutput {
  research: { executive_summary: string; claims: ResearchClaim[]; risks: string[]; data_gaps: string[]; invalidation_conditions: ResearchCondition[]; next_checks: string[] }
  diagnostics: { claim_index: number; reference_check: 'passed'; numeric_check: 'matched' | 'mismatch' | 'not_reported'; semantic_support: 'not_assessed'; codes: string[] }[]
  model_review: { status: 'not_requested' | 'available' | 'unavailable'; label: string; error_code?: string; claims?: { claim_index: number; support: 'supported' | 'unsupported' | 'uncertain'; explanation: string }[] }
}
export interface ResearchRun {
  id: number; project_id: number; project_version: number; status: 'completed' | 'failed'
  input_snapshot: ResearchSnapshot; input_fingerprint: string; output: ResearchOutput | null
  model_name: string; prompt_version: string; error_code: string | null; created_at: string
}
export interface ResearchConditionCheck {
  index: number; status: 'triggered' | 'not_triggered' | 'uncheckable'; metric_key: string | null
  previous_value?: string | null; current_value?: string; as_of?: string | null
}
export interface ResearchEvent {
  id: number; project_id: number; run_id: number; input_fingerprint: string
  reason_code: 'data_changed' | 'condition_triggered' | 'data_unavailable'; status: 'open' | 'resolved'
  details: { changed_fields?: Record<string, unknown>[]; conditions?: ResearchConditionCheck[]; [key: string]: unknown }
  created_at: string; resolved_at: string | null
}
export interface ResearchCheck {
  run_id: number | null; changed: boolean; events: ResearchEvent[]; conditions: ResearchConditionCheck[]
  status: 'no_completed_run' | 'unchanged' | 'needs_review'
}
