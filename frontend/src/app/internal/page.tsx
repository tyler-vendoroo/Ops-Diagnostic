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
  trial_interest: boolean;
  status: string;
  created_at: string | null;
  referral_code: string | null;
  referred_by: string | null;
  reminder_count: number;
  last_reminder_sent_at: string | null;
  // Enrichment — populated after diagnostic completes
  door_count: number | null;
  property_count: number | null;
  staff_count: number | null;
  operational_model: string | null;
  primary_goal: string | null;
  overall_score: number | null;
  recommended_tier: string | null;
  gap_count: number | null;
  top_gap: string | null;
  pain_points: string | null;
  after_hours_method: string | null;
  avg_response_time: string | null;
  projected_score: number | null;
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

function LeadRowExpanded({ lead, allLeads }: { lead: LeadRow; allLeads: LeadRow[] }) {
  const [open, setOpen] = React.useState(false);
  const referralCount = allLeads.filter((l) => l.referred_by === lead.id).length;

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
          <p className="text-xs text-gray-500">{lead.company}</p>
          <p className="text-xs text-gray-400">{lead.email}</p>
        </td>
        <td className="px-4 py-3">
          {lead.door_count ? (
            <div>
              <p className="text-sm font-medium text-gray-900">{lead.door_count.toLocaleString()} doors</p>
              <p className="text-xs text-gray-500">
                {lead.staff_count ?? "?"}{" "}
                {lead.operational_model === "tech" ? "techs" : lead.operational_model === "blended" ? "staff" : "coordinators"}
                {" · "}{lead.pms_platform || "—"}
              </p>
            </div>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          {lead.overall_score != null ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className={`text-lg font-semibold tabular-nums ${scoreColor(lead.overall_score)}`}>
                {lead.overall_score}
              </span>
              {lead.projected_score && (
                <span className="text-xs text-vendoroo-muted">→ {lead.projected_score}</span>
              )}
              {lead.recommended_tier && (
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${tierColor(lead.recommended_tier)}`}>
                  {lead.recommended_tier}
                </span>
              )}
            </div>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          {lead.primary_goal ? (
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600 capitalize">
              {lead.primary_goal}
            </span>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          {lead.top_gap ? (
            <div>
              <p className="text-xs font-medium text-rose-600">{lead.top_gap}</p>
              {lead.gap_count != null && lead.gap_count > 1 && (
                <p className="text-[10px] text-gray-400">+{lead.gap_count - 1} more</p>
              )}
            </div>
          ) : (
            <span className="text-xs text-gray-400">—</span>
          )}
        </td>
        <td className="px-4 py-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {lead.diagnostics.length > 0 ? (
              <span className="inline-flex rounded-full bg-vendoroo-tint/30 px-2.5 py-0.5 text-xs font-medium text-vendoroo-main-dark">
                {lead.diagnostics.length} diagnostic{lead.diagnostics.length !== 1 ? "s" : ""}
              </span>
            ) : (
              <span className="text-xs text-gray-400">None</span>
            )}
            {lead.trial_interest && (
              <span className="inline-flex rounded-full bg-teal-50 px-1.5 py-0.5 text-[10px] font-semibold text-teal-700">
                trial
              </span>
            )}
            {lead.reminder_count > 0 && (
              <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
                {lead.reminder_count}/3 reminders
              </span>
            )}
            {referralCount > 0 && (
              <span className="inline-flex rounded-full bg-teal-100 px-2 py-0.5 text-[10px] font-semibold text-teal-700">
                {referralCount} referral{referralCount !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        </td>
      </tr>

      {open && (lead.pain_points || lead.after_hours_method || lead.avg_response_time || lead.projected_score) && (
        <tr>
          <td colSpan={7} className="border-b border-gray-100 bg-gray-50/50 px-4 py-3">
            <div className="ml-8 grid grid-cols-2 gap-x-8 gap-y-2 sm:grid-cols-4">
              {lead.pain_points && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Pain Points</p>
                  <p className="text-xs text-gray-700">{lead.pain_points}</p>
                </div>
              )}
              {lead.after_hours_method && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">After-Hours</p>
                  <p className="text-xs text-gray-700">{lead.after_hours_method}</p>
                </div>
              )}
              {lead.avg_response_time && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Response Time</p>
                  <p className="text-xs text-gray-700">{lead.avg_response_time}</p>
                </div>
              )}
              {lead.projected_score != null && lead.overall_score != null && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Projected Score</p>
                  <p className="text-xs font-medium text-vendoroo-main">{lead.overall_score} → {lead.projected_score}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}

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
                        <DiagnosticSendButton diagnosticId={d.id} />
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

interface BookingRow {
  id: string;
  name: string;
  email: string;
  company: string | null;
  date: string;
  date_display: string;
  time: string;
  time_display: string;
  notes: string | null;
  status: string;
  lead_id: string | null;
  diagnostic_id: string | null;
  diagnostic_score: number | null;
}


function DiagnosticSendButton({ diagnosticId }: { diagnosticId: string }) {
  const [state, setState] = React.useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleSend(e: React.MouseEvent) {
    e.stopPropagation();
    setState("sending");
    try {
      const res = await fetch(`${API}/api/v1/diagnostic/${diagnosticId}/send-results`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json() as { detail?: string };
        throw new Error(err.detail ?? "Failed");
      }
      setState("sent");
    } catch {
      setState("error");
    }
  }

  return (
    <button
      type="button"
      onClick={handleSend}
      disabled={state === "sending" || state === "sent"}
      className={`inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
        state === "sent"
          ? "border-green-200 bg-green-50 text-green-700"
          : state === "error"
            ? "border-rose-200 bg-rose-50 text-rose-600"
            : "border-gray-200 text-gray-700 hover:bg-gray-100 disabled:opacity-50"
      }`}
    >
      {state === "sending" ? "Sending…" : state === "sent" ? "Sent ✓" : state === "error" ? "Retry" : "Send results"}
    </button>
  );
}

function BookingTableRow({
  booking,
  diagId,
  diagScore,
  onViewLead,
}: {
  booking: BookingRow;
  diagId: string | null;
  diagScore: number | null;
  onViewLead: () => void;
}) {
  const [sending, setSending] = React.useState(false);
  const [sent, setSent] = React.useState(false);
  const [sendError, setSendError] = React.useState<string | null>(null);

  async function handleSend() {
    setSending(true);
    setSendError(null);
    try {
      const res = await fetch(`${API}/api/v1/bookings/${booking.id}/send-results`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json() as { detail?: string };
        throw new Error(err.detail ?? "Send failed");
      }
      setSent(true);
    } catch (e) {
      setSendError(e instanceof Error ? e.message : "Failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="px-4 py-3">
        <p className="text-sm font-semibold text-gray-900">{booking.time_display}</p>
        <p className="text-xs text-gray-400">{booking.date_display}</p>
      </td>
      <td className="px-4 py-3">
        <button
          type="button"
          onClick={onViewLead}
          className="text-left text-sm font-medium text-vendoroo-main hover:underline"
        >
          {booking.name}
        </button>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{booking.company || "—"}</td>
      <td className="px-4 py-3 text-sm text-gray-400">{booking.email}</td>
      <td className="px-4 py-3">
        {diagId ? (
          <a
            href={`/diagnostic/results/${diagId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-medium text-vendoroo-main hover:underline"
          >
            View {diagScore != null ? `(${diagScore})` : ""}
          </a>
        ) : (
          <span className="text-xs text-gray-400">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">{booking.notes || "—"}</td>
      <td className="px-4 py-3">
        {diagId ? (
          <div className="flex flex-col gap-0.5">
            <button
              type="button"
              onClick={handleSend}
              disabled={sending || sent}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                sent
                  ? "bg-green-100 text-green-700"
                  : "bg-vendoroo-main text-white hover:bg-vendoroo-main/90 disabled:opacity-50"
              }`}
            >
              {sending ? "Sending…" : sent ? "Sent ✓" : "Send results"}
            </button>
            {sendError && <p className="text-[10px] text-rose-500">{sendError}</p>}
          </div>
        ) : (
          <span className="text-xs text-gray-300">No diagnostic</span>
        )}
      </td>
    </tr>
  );
}

export default function InternalDashboard() {
  const [authed, setAuthed] = React.useState<boolean | null>(null);
  const [password, setPassword] = React.useState("");
  const [loginError, setLoginError] = React.useState("");
  const [activeTab, setActiveTab] = React.useState<"leads" | "bookings">("leads");
  const [search, setSearch] = React.useState("");
  const [leads, setLeads] = React.useState<LeadRow[]>([]);
  const [total, setTotal] = React.useState(0);
  const [loading, setLoading] = React.useState(false);
  const [bookings, setBookings] = React.useState<BookingRow[]>([]);
  const [bookingsLoading, setBookingsLoading] = React.useState(false);

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

  const fetchBookings = React.useCallback(async () => {
    setBookingsLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/bookings/admin`, {
        credentials: "include",
        headers: authHeaders(),
      });
      if (res.ok) {
        const data = (await res.json()) as { bookings: BookingRow[] };
        setBookings(data.bookings);
      }
    } catch (err) {
      console.error("Failed to fetch bookings:", err);
    } finally {
      setBookingsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (!authed) return;
    void fetchBookings();
  }, [authed, fetchBookings]);

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
            Vendoroo Internal
          </h1>
          <div className="mt-3 flex gap-1">
            <button
              type="button"
              onClick={() => setActiveTab("leads")}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === "leads"
                  ? "bg-vendoroo-main text-white"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              Leads
              <span className="ml-1.5 text-xs opacity-70">{total}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("bookings")}
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === "bookings"
                  ? "bg-vendoroo-main text-white"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              NARPM Bookings
              <span className="ml-1.5 text-xs opacity-70">{bookings.length}</span>
            </button>
          </div>
        </div>
        {activeTab === "leads" && (
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
        )}
      </div>

      {activeTab === "leads" && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50/80">
                <th className="w-10 px-4 py-3" />
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Contact</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Portfolio</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Score</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Goal</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Top Gap</th>
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
                leads.map((lead) => <LeadRowExpanded key={lead.id} lead={lead} allLeads={leads} />)
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "bookings" && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50/80">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Time</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Name</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Company</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Email</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Diagnostic</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Notes</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Send</th>
              </tr>
            </thead>
            <tbody>
              {bookingsLoading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400">Loading...</td>
                </tr>
              ) : bookings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400">No bookings yet</td>
                </tr>
              ) : (
                bookings.map((b) => {
                  const matchedLead = leads.find((l) => l.email === b.email);
                  const diagId = b.diagnostic_id ?? matchedLead?.diagnostics[0]?.id ?? null;
                  const diagScore = b.diagnostic_score ?? matchedLead?.diagnostics[0]?.overall_score ?? null;
                  return (
                    <BookingTableRow
                      key={b.id}
                      booking={b}
                      diagId={diagId}
                      diagScore={diagScore}
                      onViewLead={() => { setActiveTab("leads"); setSearch(b.email); }}
                    />
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
