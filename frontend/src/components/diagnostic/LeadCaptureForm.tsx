"use client";

import * as React from "react";

import type { LeadCapture } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const STORAGE_KEY = "vendoroo_ops_diagnostic_lead";

function saveLeadToStorage(lead: LeadCapture) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(lead));
}

export function LeadCaptureForm({
  onSubmitted,
}: {
  onSubmitted: (lead: LeadCapture) => void;
}) {
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [termsAccepted, setTermsAccepted] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  function handleSubmit(e: React.FormEvent) {
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
    };
    saveLeadToStorage(lead);
    onSubmitted(lead);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto flex w-full max-w-lg flex-col gap-5"
    >
      <div className="space-y-2">
        <Label htmlFor="lead-name" className="text-slate-200">
          Full name
        </Label>
        <Input
          id="lead-name"
          name="name"
          autoComplete="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border-white/15 bg-[#0B1220] text-slate-100 placeholder:text-slate-500"
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-email" className="text-slate-200">
          Work email
        </Label>
        <Input
          id="lead-email"
          name="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border-white/15 bg-[#0B1220] text-slate-100 placeholder:text-slate-500"
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-company" className="text-slate-200">
          Company name
        </Label>
        <Input
          id="lead-company"
          name="company"
          autoComplete="organization"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="border-white/15 bg-[#0B1220] text-slate-100 placeholder:text-slate-500"
          required
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="lead-phone" className="text-slate-200">
          Phone <span className="font-normal text-slate-500">(optional)</span>
        </Label>
        <Input
          id="lead-phone"
          name="phone"
          type="tel"
          autoComplete="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="border-white/15 bg-[#0B1220] text-slate-100 placeholder:text-slate-500"
        />
      </div>
      <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-[#0B1220]/80 p-4">
        <Checkbox
          id="lead-terms"
          checked={termsAccepted}
          onCheckedChange={(c) => setTermsAccepted(c === true)}
          className="mt-0.5 border-white/25"
        />
        <Label
          htmlFor="lead-terms"
          className="cursor-pointer text-sm font-normal leading-snug text-slate-300"
        >
          I agree to Vendoroo contacting me about this diagnostic and related
          operations services. I understand my responses inform a
          confidential assessment.
        </Label>
      </div>
      {error ? (
        <p className="text-sm text-amber-400" role="alert">
          {error}
        </p>
      ) : null}
      <Button
        type="submit"
        className="h-11 w-full bg-[#6366F1] text-base font-medium text-white hover:bg-[#4F46E5] sm:w-auto sm:self-start"
      >
        Continue
      </Button>
    </form>
  );
}
