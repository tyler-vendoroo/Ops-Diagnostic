"use client";

import * as React from "react";

import type { LeadCapture } from "@/lib/types";
import { createLead } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STORAGE_KEY = "vendoroo_ops_diagnostic_lead";

function saveLeadToStorage(lead: LeadCapture & { lead_id?: string }) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(lead));
}

const inputClassName =
  "border-vendoroo-border bg-vendoroo-surface text-vendoroo-text placeholder:text-vendoroo-muted";

export function LeadCaptureForm({
  onSubmitted,
}: {
  onSubmitted: (lead: LeadCapture) => void;
}) {
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [trialInterest, setTrialInterest] = React.useState(false);
  const [termsAccepted, setTermsAccepted] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [referralSource, setReferralSource] = React.useState<string | null>(null);

  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ref = params.get("ref");
    if (ref) setReferralSource(ref);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name.trim() || !email.trim() || !company.trim()) {
      setError("Please complete name, email, and company.");
      return;
    }
    if (!termsAccepted) {
      setError("Please confirm you agree to the terms to continue.");
      return;
    }
    const lead: LeadCapture = {
      name: name.trim(),
      email: email.trim(),
      company: company.trim(),
      phone: phone.trim() || undefined,
      terms_accepted: true,
      trial_interest: trialInterest,
      referral_source: referralSource ?? undefined,
    };
    setLoading(true);
    try {
      const { lead_id } = await createLead(lead);
      saveLeadToStorage({ ...lead, lead_id, trial_interest: trialInterest });
      onSubmitted(lead);
    } catch (err) {
      console.error("Lead capture failed:", err);
      // Still proceed — don't block the user if API is down
      saveLeadToStorage(lead);
      onSubmitted(lead);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex w-full max-w-lg flex-col gap-5 rounded-xl border border-vendoroo-border bg-vendoroo-surface p-6 shadow-sm sm:p-8"
    >
      <div className="space-y-2">
        <Label htmlFor="lead-name" className="text-vendoroo-text">
          Full name
        </Label>
        <Input
          id="lead-name"
          name="name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClassName}
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-email" className="text-vendoroo-text">
          Work email
        </Label>
        <Input
          id="lead-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className={inputClassName}
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-company" className="text-vendoroo-text">
          Company name
        </Label>
        <Input
          id="lead-company"
          name="company"
          autoComplete="organization"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className={inputClassName}
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-phone" className="text-vendoroo-text">
          Phone <span className="font-normal text-vendoroo-muted">(optional)</span>
        </Label>
        <Input
          id="lead-phone"
          name="phone"
          type="tel"
          autoComplete="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className={inputClassName}
        />
      </div>
      <div className="flex items-start gap-3 rounded-lg border border-vendoroo-main/20 bg-vendoroo-tint/10 p-4">
        <Checkbox
          id="trial-interest"
          checked={trialInterest}
          onCheckedChange={(c) => setTrialInterest(c === true)}
          className="mt-0.5 shrink-0 border-vendoroo-main"
        />
        <Label
          htmlFor="trial-interest"
          className="block min-w-0 flex-1 cursor-pointer text-left text-sm font-normal leading-relaxed text-vendoroo-smoke"
        >
          I&apos;m interested in{" "}
          <span className="font-semibold text-vendoroo-main">90 days free</span>{" "}
          with Vendoroo AI maintenance coordination.
        </Label>
      </div>
      <div className="flex items-start gap-3 rounded-lg border border-vendoroo-border bg-vendoroo-light p-4">
        <Checkbox
          id="lead-terms"
          checked={termsAccepted}
          onCheckedChange={(c) => setTermsAccepted(c === true)}
          className="mt-0.5 border-vendoroo-border"
        />
        <Label
          htmlFor="lead-terms"
          className="cursor-pointer text-sm font-normal leading-snug text-vendoroo-smoke"
        >
          I agree to Vendoroo contacting me about this diagnostic and related
          operations services. I understand my responses inform a confidential
          assessment.
        </Label>
      </div>
      {error ? (
        <p className="text-sm text-amber-700" role="alert">
          {error}
        </p>
      ) : null}
      <Button
        type="submit"
        disabled={loading}
        className="h-12 w-full rounded-full text-sm font-medium uppercase tracking-[-0.02em] sm:w-auto sm:self-start sm:px-10"
      >
        {loading ? "Saving…" : "Continue"}
      </Button>
    </form>
  );
}
