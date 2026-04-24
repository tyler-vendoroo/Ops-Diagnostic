"use client";

import * as React from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface Slot {
  time: string;
  display: string;
  available: boolean;
}

interface Day {
  date: string;
  display: string;
  slots: Slot[];
}

const inputClass =
  "w-full rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30";

export default function SchedulePage() {
  const [days, setDays] = React.useState<Day[]>([]);
  const [selectedDay, setSelectedDay] = React.useState("");
  const [selectedTime, setSelectedTime] = React.useState("");
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [leadId, setLeadId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [fetching, setFetching] = React.useState(true);
  const [booked, setBooked] = React.useState<{ date: string; time: string; diagnosticId: string | null } | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlLeadId = params.get("lead");
    if (urlLeadId) {
      fetch(`${API}/api/v1/leads/${urlLeadId}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((data: { name?: string; email?: string; company?: string } | null) => {
          if (data) {
            setName(data.name ?? "");
            setEmail(data.email ?? "");
            setCompany(data.company ?? "");
            setLeadId(urlLeadId);
          }
        })
        .catch(() => {});
      return;
    }
    try {
      const stored = localStorage.getItem("vendoroo_ops_diagnostic_lead");
      if (stored) {
        const lead = JSON.parse(stored) as { name?: string; email?: string; company?: string; lead_id?: string };
        setName(lead.name ?? "");
        setEmail(lead.email ?? "");
        setCompany(lead.company ?? "");
        if (lead.lead_id) setLeadId(lead.lead_id);
      }
    } catch {}
  }, []);

  React.useEffect(() => {
    fetch(`${API}/api/v1/bookings/slots`)
      .then((r) => r.json())
      .then((data: { days: Day[] }) => {
        setDays(data.days ?? []);
        if (data.days?.length) setSelectedDay(data.days[0].date);
      })
      .catch(() => {})
      .finally(() => setFetching(false));
  }, []);

  async function handleBook() {
    if (!name.trim() || !email.trim() || !selectedDay || !selectedTime) {
      setError("Please fill in your name, email, and select a time.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/bookings/book`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          company: company.trim() || null,
          booking_date: selectedDay,
          booking_time: selectedTime,
          notes: notes.trim() || null,
          lead_id: leadId || null,
        }),
      });
      const data = await res.json() as { date: string; time: string; diagnostic_id?: string | null; detail?: string };
      if (!res.ok) throw new Error(data.detail || "Booking failed");
      setBooked({ date: data.date, time: data.time, diagnosticId: data.diagnostic_id ?? null });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (booked) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center bg-vendoroo-page px-4">
        <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-lg ring-1 ring-vendoroo-border">
          <div className="mx-auto mb-4 flex size-16 items-center justify-center rounded-full bg-vendoroo-main/10">
            <svg className="size-8 text-vendoroo-main" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-vendoroo-text">You&apos;re booked!</h1>
          <p className="mt-2 text-vendoroo-smoke">
            {booked.date} at {booked.time} CT
          </p>
          <p className="mt-1 text-sm text-vendoroo-muted">
            Vendoroo &middot; Imperial Room 5A (4th Floor) &middot; Hyatt Regency New Orleans
          </p>
          <p className="mt-6 text-xs text-vendoroo-muted">
            Check your email for confirmation. See you there!
          </p>
          {booked.diagnosticId && (
            <a
              href={`/diagnostic/results/${booked.diagnosticId}`}
              className="mt-4 inline-block text-sm font-medium text-vendoroo-main hover:underline"
            >
              View your diagnostic results →
            </a>
          )}
        </div>
      </div>
    );
  }

  const currentDay = days.find((d) => d.date === selectedDay);

  return (
    <div className="flex min-h-[80vh] items-center justify-center bg-vendoroo-page px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="mb-8 text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            NARPM Broker/Owner 2026
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-vendoroo-text">
            Meet the Vendoroo team
          </h1>
          <p className="mt-2 text-sm text-vendoroo-muted">
            Book a 15-minute slot at Imperial Room 5A (4th Floor). We&apos;ll walk you through your diagnostic
            results or show you a live demo.
          </p>
        </div>

        <div className="rounded-2xl border border-vendoroo-border bg-white p-6 shadow-sm">
          {fetching ? (
            <div className="flex justify-center py-8">
              <div className="size-6 animate-spin rounded-full border-2 border-vendoroo-main border-t-transparent" />
            </div>
          ) : (
            <>
              {/* Day tabs */}
              <div className="mb-6 flex gap-2">
                {days.map((day) => {
                  const [weekday, monthDay] = day.display.split(", ");
                  return (
                    <button
                      key={day.date}
                      type="button"
                      onClick={() => { setSelectedDay(day.date); setSelectedTime(""); }}
                      className={[
                        "flex-1 rounded-xl px-3 py-3 text-center text-sm font-medium transition-colors",
                        selectedDay === day.date
                          ? "bg-vendoroo-main text-white"
                          : "bg-vendoroo-light text-vendoroo-smoke hover:bg-vendoroo-border",
                      ].join(" ")}
                    >
                      {weekday}
                      <br />
                      <span className="text-xs opacity-80">{monthDay}</span>
                    </button>
                  );
                })}
              </div>

              {/* Time grid */}
              {currentDay && (
                <div className="mb-6">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-vendoroo-muted">
                    Select a time (CT)
                  </p>
                  {currentDay.slots.length === 0 ? (
                    <p className="py-4 text-center text-sm text-vendoroo-muted">No slots available for this day.</p>
                  ) : (
                    <div className="grid grid-cols-4 gap-2">
                      {currentDay.slots.map((slot) => (
                        <button
                          key={slot.time}
                          type="button"
                          disabled={!slot.available}
                          onClick={() => setSelectedTime(slot.time)}
                          className={[
                            "rounded-lg px-2 py-2 text-xs font-medium transition-colors",
                            selectedTime === slot.time
                              ? "bg-vendoroo-main text-white"
                              : slot.available
                                ? "bg-vendoroo-light text-vendoroo-smoke hover:bg-vendoroo-border"
                                : "cursor-not-allowed bg-gray-100 text-gray-300 line-through",
                          ].join(" ")}
                        >
                          {slot.display}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Contact fields */}
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Your name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputClass}
                />
                <input
                  type="email"
                  placeholder="Work email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                />
                <input
                  type="text"
                  placeholder="Company (optional)"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  className={inputClass}
                />
                <input
                  type="text"
                  placeholder="Anything you'd like to discuss? (optional)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className={inputClass}
                />
              </div>

              {error && (
                <p className="mt-3 text-xs text-rose-500">{error}</p>
              )}

              <button
                type="button"
                onClick={handleBook}
                disabled={loading || !selectedTime}
                className="mt-6 w-full rounded-full bg-vendoroo-main px-6 py-3 text-sm font-semibold uppercase tracking-wider text-white transition-colors hover:bg-vendoroo-main/90 disabled:opacity-50"
              >
                {loading ? "Booking…" : "Confirm booking"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
