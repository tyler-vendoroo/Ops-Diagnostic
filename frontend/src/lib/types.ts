// ─── Lead ────────────────────────────────────────────────────────────────────

export type LeadStatus =
  | "new"
  | "engaged"
  | "diagnostic_started"
  | "diagnostic_complete"
  | "abandoned";

export interface LeadCapture {
  name: string;
  email: string;
  company: string;
  phone?: string;
  event_source?: string;
  terms_accepted: boolean;
}

// ─── Client Info ─────────────────────────────────────────────────────────────

export interface ClientInfo {
  company_name: string;
  door_count: number;
  property_count: number;
  pms_platform: string; // AppFolio | Buildium | RentManager | Other
  operational_model: string; // va | tech
  operational_model_display?: string;
  staff_count?: number;
  primary_goal?: "scale" | "optimize" | "elevate";
  primary_goal_display?: string;
  goal_description?: string;
  contact_name?: string;
  contact_email?: string;
  event_source?: string;
  lead_id?: string;
  data_source?: string;
}

// ─── Survey ───────────────────────────────────────────────────────────────────

export interface SurveyResponse {
  // Company basics
  door_count: number;
  property_count?: number;
  pms_platform?: string;
  portfolio_model?: "sfr" | "mfr" | "mixed";
  staff_count?: number;

  // Vendor coverage
  vendor_count?: number;
  trades_covered: string[];

  // Policies
  has_written_emergency_protocols?: "yes" | "no" | "unsure";
  has_defined_ntes?: "yes" | "no" | "unsure";
  ntes_are_tiered: boolean;
  has_defined_slas?: "yes" | "no" | "unsure";

  // Operations
  estimated_monthly_wos?: number;
  estimated_open_rate?: number;
  estimated_response_time?:
    | "under_1hr"
    | "1_4hrs"
    | "4_12hrs"
    | "same_day"
    | "next_day"
    | "unsure";
  estimated_completion_time?:
    | "1_3days"
    | "3_7days"
    | "7_14days"
    | "14plus"
    | "unsure";
  after_hours_method?:
    | "24_7_coverage"
    | "answering_service"
    | "on_call_rotation"
    | "voicemail_only"
    | "none";

  // Goals
  primary_goal?: "scale" | "optimize" | "elevate";
  pain_points: string[];
}

// ─── Diagnostic ───────────────────────────────────────────────────────────────

export type DiagnosticTier = "engage" | "direct" | "command";
export type DiagnosticStatus = "pending" | "processing" | "complete" | "failed";

export interface KeyFinding {
  title: string;
  description: string;
  impact?: string;
  category?: string;
}

export interface GapFinding {
  title: string;
  description: string;
  severity?: "high" | "medium" | "low";
  category?: string;
}

export interface DiagnosticResult {
  diagnostic_id: string;
  overall_score: number;
  scores: Record<string, number>;
  tier: DiagnosticTier;
  key_findings: KeyFinding[];
  gaps: GapFinding[];
  pdf_url: string | null;
  status: DiagnosticStatus;
}

// ─── API Request Payloads ─────────────────────────────────────────────────────

export interface QuickDiagnosticRequest {
  lead: LeadCapture;
  survey: SurveyResponse;
  client_info: ClientInfo;
}

export interface CreateLeadRequest {
  name: string;
  email: string;
  company: string;
  phone?: string;
  event_source?: string;
  terms_accepted: boolean;
}

// ─── API Responses ────────────────────────────────────────────────────────────

export interface CreateLeadResponse {
  lead_id: string;
}

export interface DiagnosticStatusResponse {
  id?: string;
  diagnostic_id?: string;
  status: DiagnosticStatus;
  overall_score?: number;
  scores?: Record<string, number>;
  tier?: DiagnosticTier;
  key_findings?: KeyFinding[];
  gaps?: GapFinding[];
  pdf_url?: string;
}
