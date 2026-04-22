import type {
  QuickDiagnosticRequest,
  DiagnosticResult,
  DiagnosticStatusResponse,
  CreateLeadRequest,
  CreateLeadResponse,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ─── Diagnostic ───────────────────────────────────────────────────────────────

export async function runQuickDiagnostic(
  payload: QuickDiagnosticRequest
): Promise<DiagnosticResult> {
  return request<DiagnosticResult>("/diagnostic/quick", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getDiagnostic(
  id: string
): Promise<DiagnosticStatusResponse> {
  return request<DiagnosticStatusResponse>(`/diagnostic/${id}`);
}

export function getDiagnosticPdfUrl(id: string): string {
  return `${API_URL}/api/v1/diagnostic/${id}/pdf`;
}

export function getDiagnosticReportUrl(id: string): string {
  return `${API_URL}/api/v1/diagnostic/${id}/report`;
}

// ─── Leads ────────────────────────────────────────────────────────────────────

export async function createLead(
  payload: CreateLeadRequest
): Promise<CreateLeadResponse> {
  return request<CreateLeadResponse>("/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
