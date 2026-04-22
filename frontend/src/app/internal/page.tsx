"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, Download, ExternalLink, FileText, Search } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "vendoroo_internal_token";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { "X-Internal-Token": token } : {};
}

interface DiagnosticSummary {
  id: string;
  type: "quick" | "full";
  status: string;
  overall_score: number | null;
  tier: string | null;
  created_at: string | null;
}

interface LeadRow {
  id: string;
  name: string;
  email: string;
  company: string;
  phone: string | null;
  pms_platform: string | null;
  door_count: number | null;
  trial_interest: boolean;
  status: string;
  created_at: string | null;
  diagnostics: DiagnosticSummary[];
}

function tierColor(tier: string | null): string {
  if (!tier) return "bg-gray-100 text-gray-600";
  const t = tier.toLowerCase();
  if (t === "command") return "bg-purple-100 text-purple-700";
  if (t === "direct") return "bg-blue-100 text-blue-700";
  return "bg-teal-100 text-teal-700";
}

function scoreColor(score: number | null): string {
  if (score === null) return "text-gray-400";
  if (score >= 70) return "text-green-600";
  if (score >= 50) return "text-yellow-600";
  return "text-red-600";
}

function statusBadge(status: string): string {
  if (status === "complete") return "bg-green-100 text-green-700";
  if (status === "failed") return "bg-red-100 text-red-700";
  if (status === "processing") return "bg-yellow-100 text-yellow-700";
  return "bg-gray-100 text-gray-600";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function LeadRowExpanded({ lead }: { lead: LeadRow }) {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <tr
        className="cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-50"
        onClick={() => setOpen(!open)}
      >
        <td className="px-4 py-3">
          {open
            ? <ChevronDown className="size-4 text-gray-400" />
            : <ChevronRight className="size-4 text-gray-400" />}
        </td>
        <td className="px-4 py-3">
          <p className="text-sm font-medium text-gray-900">{lead.name}</p>
          <p className="text-xs text-gray-500">{lead.email}</p>
        </td>
        <td className="px-4 py-3 text-sm text-gray-700">
          {lead.company}
          {lead.trial_interest && (
            <span className="ml-2 inline-flex rounded-full bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">
              trial
            </span>
          )}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500">{lead.pms_platform || "—"}</td>
        <td className="px-4 py-3 text-sm text-gray-500">
          {lead.door_count != null ? lead.door_count.toLocaleString() : "—"}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500">{formatDate(lead.created_at)}</td>
        <td className="px-4 py-3">
          {lead.diagnostics.length > 0 ? (
            <span className="inline-flex rounded-full bg-vendoroo-tint/30 px-2.5 py-0.5 text-xs font-medium text-vendoroo-main-dark">
              {lead.diagnostics.length} diagnostic{lead.diagnostics.length !== 1 ? "s" : ""}
            </span>
          ) : (
            <span className="text-xs text-gray-400">None</span>
          )}
        </td>
      </tr>

      {open && lead.diagnostics.length > 0 && (
        <tr>
          <td colSpan={7} className="bg-gray-50/80 px-4 py-3">
            <div className="ml-8 flex flex-col gap-2">
              {lead.diagnostics.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white px-4 py-3"
                >
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${statusBadge(d.status)}`}>
                    {d.status}
                  </span>
                  <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
                    {d.type}
                  </span>
                  <span className={`text-lg font-semibold tabular-nums ${scoreColor(d.overall_score)}`}>
                    {d.overall_score ?? "—"}
                  </span>
                  {d.tier && (
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tierColor(d.tier)}`}>
                      {d.tier}
                    </span>
                  )}
                  <span className="text-xs text-gray-400">{formatDate(d.created_at)}</span>
                  <div className="ml-auto flex items-center gap-2">
                    <Link
                      href={`/diagnostic/results/${d.id}`}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="size-3" />
                      Results
                    </Link>
                    {d.type === "full" && d.status === "complete" && (
                      <>
                        <a
                          href={`${API}/api/v1/diagnostic/${d.id}/report`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <FileText className="size-3" />
                          Report
                        </a>
                        <a
                          href={`${API}/api/v1/diagnostic/${d.id}/pdf`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded-md border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <Download className="size-3" />
                          PDF
                        </a>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}

      {open && lead.diagnostics.length === 0 && (
        <tr>
          <td colSpan={7} className="bg-gray-50/80 px-8 py-4">
            <p className="text-xs text-gray-400">No diagnostics submitted yet.</p>
          </td>
        </tr>
      )}
    </>
  );
}

export default function InternalDashboard() {
  const [authed, setAuthed] = React.useState<boolean | null>(null);
  const [password, setPassword] = React.useState("");
  const [loginError, setLoginError] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [leads, setLeads] = React.useState<LeadRow[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    fetch(`${API}/api/v1/internal/check`, {
      credentials: "include",
      headers: authHeaders(),
    })
      .then((r) => setAuthed(r.ok))
      .catch(() => setAuthed(false));
  }, []);

  const fetchLeads = React.useCallback(async (query: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (query.trim()) params.set("search", query.trim());
      const res = await fetch(`${API}/api/v1/leads?${params}`, {
        credentials: "include",
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = (await res.json()) as { total: number; leads: LeadRow[] };
        setLeads(data.leads);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch leads:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (!authed) return;
    void fetchLeads("");
  }, [authed, fetchLeads]);

  React.useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => void fetchLeads(search), 300);
    return () => clearTimeout(t);
  }, [search, authed, fetchLeads]);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoginError("");
    const res = await fetch(`${API}/api/v1/internal/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ password }),
    });
    if (res.ok) {
      const data = (await res.json()) as { ok: boolean; token: string };
      localStorage.setItem(TOKEN_KEY, data.token);
      setAuthed(true);
      setPassword("");
    } else {
      setLoginError("Wrong password");
    }
  }

  if (authed === null) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-sm text-gray-400">Checking access...</p>
      </div>
    );
  }

  if (!authed) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <form
          onSubmit={(e) => void handleLogin(e)}
          className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-sm"
        >
          <h2 className="text-lg font-semibold text-gray-900">Vendoroo Internal</h2>
          <p className="mt-1 text-sm text-gray-500">Enter the team password to continue.</p>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
            className="mt-6 w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm focus:border-vendoroo-main focus:outline-none focus:ring-2 focus:ring-vendoroo-main/20"
            autoFocus
          />
          {loginError && <p className="mt-2 text-xs text-red-500">{loginError}</p>}
          <button
            type="submit"
            className="mt-4 w-full rounded-lg bg-vendoroo-main px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-vendoroo-main/90"
          >
            Sign in
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-gray-900 sm:text-2xl">
            Diagnostics Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {total} lead{total !== 1 ? "s" : ""} total
          </p>
        </div>
        <div className="relative w-full sm:w-80">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, or company..."
            className="w-full rounded-lg border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm text-gray-900 placeholder:text-gray-400 focus:border-vendoroo-main focus:outline-none focus:ring-2 focus:ring-vendoroo-main/20"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50/80">
              <th className="w-10 px-4 py-3" />
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Contact</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Company</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">PMS</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Doors</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Submitted</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Diagnostics</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400">
                  Loading...
                </td>
              </tr>
            ) : leads.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400">
                  {search ? `No leads matching "${search}"` : "No leads yet"}
                </td>
              </tr>
            ) : (
              leads.map((lead) => <LeadRowExpanded key={lead.id} lead={lead} />)
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
