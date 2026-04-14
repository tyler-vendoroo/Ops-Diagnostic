"use client";

import * as React from "react";

import { LeadCaptureForm } from "@/components/diagnostic/LeadCaptureForm";
import { PathSelector } from "@/components/diagnostic/PathSelector";
import type { LeadCapture } from "@/lib/types";

export default function DiagnosticPage() {
  const [lead, setLead] = React.useState<LeadCapture | null>(null);

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:px-6 sm:py-16">
      <div className="mx-auto max-w-2xl text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Operations diagnostic
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400 sm:text-base">
          Share your contact details so we can associate results with your team.
          Next, choose a quick survey or a full file-based assessment.
        </p>
      </div>
      <div className="mt-12">
        {!lead ? (
          <LeadCaptureForm onSubmitted={setLead} />
        ) : (
          <div className="space-y-10">
            <p className="text-center text-sm text-slate-400">
              Thank you,{" "}
              <span className="font-medium text-slate-200">{lead.name}</span>.
              Select how you would like to proceed.
            </p>
            <PathSelector />
          </div>
        )}
      </div>
    </div>
  );
}
