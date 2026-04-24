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
  trial_interest?: boolean;
  referral_source?: string;
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
  annual_cost_per_staff?: number | null;
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

  // Cost
  annual_cost_per_staff?: number;
}

// ─── Diagnostic ───────────────────────────────────────────────────────────────

export interface DiagnosticInsight {
  icon: string;
  title: string;
  detail: string;
}

export type DiagnosticTier = "engage" | "direct" | "command";
export type DiagnosticStatus = "pending" | "processing" | "complete" | "failed";

export interface KeyFinding {
  title: string;
  description: string;
  impact?: string;
  category?: string;
  color?: string;
}

export interface GapFinding {
  title: string;
  description?: string;
  detail?: string;
  severity?: string;
  recommendation?: string;
  category?: string;
}

export interface CategoryScoreEntry {
  name: string;
  key: string;
  score: number;
  tier: string;
  tier_css: string;
}

export interface ImpactRow {
  metric: string;
  current_value: string;
  current_is_bad?: boolean;
  projected_value: string;
  benchmark_range?: string;
  improvement: string | null;
  note?: string | null;
}

export interface CostEstimates {
  recommended_cost: number;
  recommended_tier_name?: string;
  next_tier_cost?: number;
  next_tier_name?: string;
  rescueroo_cost?: number;
}

export interface PathData {
  stat_value: string;
  stat_label: string;
  description: string;
  best_tier: string;
}

export interface StaffingData {
  current_staff: number;
  current_doors: number;
  doors_per_staff: number;
  staff_benchmark?: number;
  scale_doors?: number;
  optimize_staff?: number;
  fte_savings?: number;
}

export interface DiagnosticSummary {
  category_scores: CategoryScoreEntry[];
  projected_score: number;
  impact_rows: ImpactRow[];
  cost_estimates: CostEstimates;
  staffing: StaffingData;
  paths: {
    scale: PathData;
    optimize: PathData;
    elevate: PathData;
  };
  company_name: string;
  door_count: number;
  staff_count: number;
  staff_label: string;
  primary_goal: string;
  operational_model: string;
  pms_platform?: string;
  pain_points?: string[];
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
  summary?: DiagnosticSummary;
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
  referral_source?: string;
}

// ─── API Responses ────────────────────────────────────────────────────────────

export interface CreateLeadResponse {
  lead_id: string;
}

export interface DiagnosticStatusResponse {
  id?: string;
  diagnostic_id?: string;
  diagnostic_type?: "quick" | "full";
  status: DiagnosticStatus;
  error?: string | null;
  overall_score?: number;
  scores?: Record<string, number>;
  tier?: DiagnosticTier;
  key_findings?: KeyFinding[];
  gaps?: GapFinding[];
  pdf_url?: string;
  summary?: {
    // Quick-only
    insights?: DiagnosticInsight[];
    vendor_count?: number;
    trades_covered?: number;
    trades_required?: number;
    // Both paths
    category_scores?: CategoryScoreEntry[];
    company_name?: string;
    door_count?: number;
    staff_count?: number;
    staff_label?: string;
    primary_goal?: string;
    operational_model?: string;
    pms_platform?: string;
    pain_points?: string[];
    // Full-only
    projected_score?: number;
    impact_rows?: ImpactRow[];
    cost_estimates?: CostEstimates;
    staffing?: StaffingData;
    paths?: {
      scale: PathData;
      optimize: PathData;
      elevate: PathData;
    };
    wo_metrics?: {
      total_work_orders?: number;
      maintenance_wos?: number;
      monthly_avg?: number;
      avg_first_response_hours?: number;
      response_time_method?: string;
      median_completion_days?: number;
      open_wo_rate_pct?: number;
      open_wo_count?: number;
      unique_vendors?: number;
      trades_covered_count?: number;
      trades_required_count?: number;
      covered_trades?: string[];
      missing_trades?: string[];
      after_hours_pct?: number;
      after_hours_time_available?: boolean;
      months_spanned?: number;
      date_range_start_short?: string;
      date_range_end_short?: string;
    };
    benchmark_rows?: Array<{
      metric: string;
      current_value: string;
      current_css: string;
      vendoroo_avg: string;
      top_performers: string;
    }>;
    repeat_units?: Record<string, {
      wo_count: number;
      primary_trades?: string[];
      total_cost?: number;
      span_days?: number;
      first_wo?: string;
      last_wo?: string;
    }>;
    current_cost_per_door?: number;
    annual_cost_per_staff?: number;
    cost_source?: string;
    referral_code?: string | null;
    [key: string]: unknown;
  };
}
