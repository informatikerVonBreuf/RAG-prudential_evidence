export type Mode = "quick" | "deep" | "summary";
export type AnswerStatus = "COMPLETE" | "PARTIAL" | "NOT_FOUND" | "CONFLICT";

export interface DocumentView {
  id: string;
  folder: string;
  title: string;
  entity: string;
  year: number;
  document_type: string;
  version: string;
  source_url: string;
  status: "indexed" | "reviewed" | "synthetic";
  pages: number;
  description: string;
}

export interface SuggestedQuestion {
  label: string;
  question: string;
}

export interface SourceLocator {
  document_id: string;
  document_title: string;
  version: string;
  source_url: string;
  page: number;
  section_path: string[];
  table_id?: string | null;
  row?: number | string | null;
  column?: number | string | null;
  bbox?: number[] | null;
}

export interface Fact {
  field_id: string;
  label: string;
  value: string | number;
  formatted_value: string;
  value_type: string;
  unit?: string | null;
  period?: string | null;
  entity: string;
}

export interface ScoreTrace {
  lexical_rank?: number | null;
  dense_rank?: number | null;
  lexical_score: number;
  dense_score: number;
  rrf_score: number;
}

export interface EvidenceView {
  id: string;
  field_id: string;
  field_label: string;
  state: "ACCEPTED" | "MISSING" | "REJECTED" | "CONFLICT";
  excerpt?: string | null;
  fact?: Fact | null;
  source?: SourceLocator | null;
  score?: ScoreTrace | null;
  reason?: string | null;
}

export interface Claim {
  id: string;
  text: string;
  evidence_ids: string[];
}

export interface CoverageItem {
  field_id: string;
  label: string;
  state: "COVERED" | "MISSING" | "CONFLICT";
  evidence_ids: string[];
}

export interface QueryTrace {
  field_id: string;
  query: string;
  candidate_count: number;
  consulted_document_ids: string[];
}

export interface ModelCallTrace {
  provider: string;
  model?: string | null;
  purpose: string;
  status: "DISABLED" | "SUCCESS" | "FALLBACK" | "ERROR";
  attempts: number;
  latency_ms: number;
  detail: string;
}

export interface MappingTrace {
  profile_id: string;
  entity?: string | null;
  period?: string | null;
  confidence: number;
  decision_source: "explicit" | "rules" | "hybrid_dense" | "llm_judge" | "abstention";
  lexical_scores: Record<string, number>;
  dense_scores: Record<string, number>;
  ambiguities: string[];
  model_calls: ModelCallTrace[];
}

export interface RetrievalRunTrace {
  strategy: "sequential_top1" | "batch_multi_field";
  dense_provider: string;
  rounds: number;
  k_history: number[];
  stop_reason: "contract_complete" | "conflict" | "budget_exhausted";
  resolved_references: string[];
  unresolved_references: string[];
}

export interface AnswerPayload {
  request_id: string;
  mode: Mode;
  status: AnswerStatus;
  profile_id: string;
  profile_label: string;
  summary: string;
  claims: Claim[];
  evidence: EvidenceView[];
  coverage: CoverageItem[];
  missing_fields: string[];
  corpus_version: string;
  query_trace: QueryTrace[];
  latency_ms: number;
  generation_provider: string;
  model_calls: ModelCallTrace[];
  mapping_trace: MappingTrace;
  retrieval_run: RetrievalRunTrace;
}

export interface SessionEntry {
  id: string;
  createdAt: string;
  question: string;
  answer: AnswerPayload;
}
