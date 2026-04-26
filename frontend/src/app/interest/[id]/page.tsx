"use client";

import * as React from "react";
import { useParams, useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export default function InterestPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const leadId = params.id as string;
  const token = searchParams.get("token") ?? "";
  const [name, setName] = React.useState("");

  React.useEffect(() => {
    if (!token || !leadId) return;
    // Fire and forget — show confirmation regardless of API result
    fetch(`${API}/api/v1/leads/${leadId}/interest?token=${encodeURIComponent(token)}`, {
      method: "POST",
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { name?: string } | null) => {
        if (data?.name) setName(data.name.split(" ")[0]);
      })
      .catch(() => {});
  }, [leadId, token]);

  return (
    <div className="flex min-h-[80vh] items-center justify-center bg-vendoroo-page px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-10 text-center shadow-lg ring-1 ring-vendoroo-border">
        <p className="mb-6 text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
          Vendoroo
        </p>
        <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-full bg-vendoroo-main/10">
          <svg
            className="size-8 text-vendoroo-main"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-vendoroo-text">
          {name ? `Thanks, ${name}!` : "You’re all set!"}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-vendoroo-muted">
          Someone from our team will reach out within 24 hours, Monday–Friday.
        </p>
        <p className="mt-6 text-sm text-vendoroo-muted">
          Or come find us at Imperial Room 5A (4th Floor), Hyatt Regency New Orleans.
        </p>
      </div>
    </div>
  );
}
