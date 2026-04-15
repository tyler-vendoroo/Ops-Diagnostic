"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import type { ClientInfo, LeadCapture, SurveyResponse } from "@/lib/types";
import { runQuickDiagnostic } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { DiagnosticProgress } from "@/components/diagnostic/DiagnosticProgress";

const LEAD_KEY = "vendoroo_ops_diagnostic_lead";
const RESULTS_SOURCE_KEY = "vendoroo_diagnostic_results_source";

const PMS_OPTIONS = [
  "AppFolio",
  "Buildium",
  "DoorLoop",
  "ManageGo",
  "Propertyware",
  "RealPage",
  "Rent Manager",
  "Rentvine",
  "Yardi Breeze",
  "Yardi Voyager",
  "Other",
] as const;

const TRADES: { id: string; label: string }[] = [
  { id: "plumbing", label: "Plumbing" },
  { id: "electrical", label: "Electrical" },
  { id: "hvac", label: "HVAC" },
  { id: "appliance_repair", label: "Appliance Repair" },
  { id: "landscaping", label: "Landscaping" },
  { id: "pest_control", label: "Pest Control" },
  { id: "roofing", label: "Roofing" },
  { id: "painting", label: "Painting" },
  { id: "flooring", label: "Flooring" },
  { id: "general_handyman", label: "General Handyman" },
  { id: "pool_spa", label: "Pool/Spa" },
  { id: "locksmith", label: "Locksmith" },
];

const RESPONSE_TIME_OPTIONS = [
  { value: "under_1hr", label: "Under 1 hour" },
  { value: "1_4hrs", label: "1–4 hours" },
  { value: "4_12hrs", label: "4–12 hours" },
  { value: "same_day", label: "Same day" },
  { value: "next_day", label: "Next day" },
  { value: "unsure", label: "Unsure" },
] as const;

const COMPLETION_TIME_OPTIONS = [
  { value: "1_3days", label: "1–3 days" },
  { value: "3_7days", label: "3–7 days" },
  { value: "7_14days", label: "7–14 days" },
  { value: "14plus", label: "14+ days" },
  { value: "unsure", label: "Unsure" },
] as const;

const PAIN_OPTIONS: { id: string; label: string }[] = [
  { id: "vendor_reliability", label: "Vendor reliability" },
  { id: "response_times", label: "Response times" },
  { id: "cost_control", label: "Cost control" },
  { id: "compliance_documentation", label: "Compliance/documentation" },
  { id: "scaling_team", label: "Scaling the team" },
  { id: "owner_communication", label: "Owner communication" },
  { id: "after_hours_coverage", label: "After-hours coverage" },
  { id: "reporting_visibility", label: "Reporting/visibility" },
];

function readLead(): LeadCapture | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(LEAD_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as LeadCapture;
  } catch {
    return null;
  }
}

function radioCardClass(active: boolean) {
  return [
    "flex min-h-[52px] cursor-pointer items-start gap-3 rounded-xl border p-4 text-left transition-colors",
    active
      ? "border-vendoroo-main bg-vendoroo-tint/50 ring-1 ring-vendoroo-main/30"
      : "border-vendoroo-border bg-vendoroo-surface hover:border-vendoroo-muted/40",
  ].join(" ");
}

function AnalyzingIndicator() {
  const stages = [
    "Mapping your vendor network",
    "Benchmarking response times",
    "Scoring operational readiness",
    "Generating your report",
  ];
  const [stageIndex, setStageIndex] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => {
      setStageIndex((prev) => Math.min(prev + 1, stages.length - 1));
    }, 2000);
    return () => clearInterval(interval);
  }, [stages.length]);

  return (
    <div className="flex flex-col items-center gap-4 py-4">
      <div className="size-8 animate-spin rounded-full border-2 border-vendoroo-main border-t-transparent" />
      <div className="flex flex-col items-center gap-2">
        {stages.map((stage, i) => (
          <p
            key={stage}
            className={[
              "text-sm transition-all duration-300",
              i < stageIndex
                ? "text-vendoroo-success"
                : i === stageIndex
                  ? "font-medium text-vendoroo-text"
                  : "text-vendoroo-muted/50",
            ].join(" ")}
          >
            {i < stageIndex ? "✓ " : ""}{stage}{i === stageIndex ? "..." : ""}
          </p>
        ))}
      </div>
    </div>
  );
}

function PolicyRadio({
  label,
  value,
  onChange,
  name,
}: {
  label: string;
  value: "yes" | "no" | "unsure" | "";
  onChange: (v: "yes" | "no" | "unsure") => void;
  name: string;
}) {
  const options: { val: "yes" | "no" | "unsure"; label: string }[] = [
    { val: "yes", label: "Yes" },
    { val: "no", label: "No" },
    { val: "unsure", label: "Unsure" },
  ];

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex gap-2">
        {options.map((opt) => (
          <button
            key={opt.val}
            type="button"
            onClick={() => onChange(opt.val)}
            aria-pressed={value === opt.val}
            className={[
              "flex-1 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all duration-150",
              value === opt.val
                ? "border-vendoroo-main bg-vendoroo-tint/30 text-vendoroo-main-dark"
                : "border-vendoroo-border bg-vendoroo-surface text-vendoroo-smoke hover:border-vendoroo-muted/50",
            ].join(" ")}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function SurveyFlow() {
  const router = useRouter();
  const [step, setStep] = React.useState(1);
  const [animating, setAnimating] = React.useState(false);
  const [lead, setLead] = React.useState<LeadCapture | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const [companyName, setCompanyName] = React.useState("");
  const [doorCount, setDoorCount] = React.useState("");
  const [propertyCount, setPropertyCount] = React.useState("");
  const [pmsPlatform, setPmsPlatform] = React.useState<string>("");
  const [pmsOther, setPmsOther] = React.useState<string>("");
  const [operationalModel, setOperationalModel] = React.useState<
    "va" | "tech" | ""
  >("");
  const [staffCount, setStaffCount] = React.useState("");

  const [vendorCount, setVendorCount] = React.useState("");
  const [trades, setTrades] = React.useState<string[]>([]);

  const [writtenEmergency, setWrittenEmergency] = React.useState<
    "yes" | "no" | "unsure" | ""
  >("");
  const [definedNtes, setDefinedNtes] = React.useState<
    "yes" | "no" | "unsure" | ""
  >("");
  const [ntesTiered, setNtesTiered] = React.useState(false);
  const [definedSlas, setDefinedSlas] = React.useState<
    "yes" | "no" | "unsure" | ""
  >("");

  const [responseTime, setResponseTime] = React.useState<string>("");
  const [completionTime, setCompletionTime] = React.useState<string>("");
  const [afterHours, setAfterHours] = React.useState<string>("");

  const [primaryGoal, setPrimaryGoal] = React.useState<
    "scale" | "optimize" | "elevate" | ""
  >("");
  const [painPoints, setPainPoints] = React.useState<string[]>([]);

  React.useEffect(() => {
    const l = readLead();
    setLead(l);
    if (l?.company) setCompanyName(l.company);
  }, []);

  function toggleTrade(id: string) {
    setTrades((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]
    );
  }

  function togglePain(id: string) {
    setPainPoints((prev) => {
      if (prev.includes(id)) return prev.filter((p) => p !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  }

  function parsePositiveInt(raw: string, label: string): number | null {
    const n = Number.parseInt(raw, 10);
    if (Number.isNaN(n) || n < 0) {
      setFormError(`Enter a valid number for ${label}.`);
      return null;
    }
    return n;
  }

  function validateStep1(): boolean {
    setFormError(null);
    if (!companyName.trim()) {
      setFormError("Company name is required.");
      return false;
    }
    const doors = parsePositiveInt(doorCount, "door count");
    if (doors === null) return false;
    const props = parsePositiveInt(propertyCount, "property count");
    if (props === null) return false;
    if (!pmsPlatform) {
      setFormError("Select a PMS platform.");
      return false;
    }
    if (!operationalModel) {
      setFormError("Select an operational model.");
      return false;
    }
    const staff = parsePositiveInt(staffCount, "staff count");
    if (staff === null) return false;
    return true;
  }

  function validateStep2(): boolean {
    setFormError(null);
    const v = parsePositiveInt(vendorCount, "vendor count");
    return v !== null;
  }

  function validateStep3(): boolean {
    setFormError(null);
    if (!writtenEmergency || !definedNtes || !definedSlas) {
      setFormError("Please answer each policy question.");
      return false;
    }
    return true;
  }

  function validateStep4(): boolean {
    setFormError(null);
    if (!responseTime || !completionTime || !afterHours) {
      setFormError("Please complete all operations fields.");
      return false;
    }
    return true;
  }

  function validateStep5(): boolean {
    setFormError(null);
    if (!primaryGoal) {
      setFormError("Select a primary goal.");
      return false;
    }
    if (painPoints.length === 0) {
      setFormError("Select at least one operational pain point (up to three).");
      return false;
    }
    return true;
  }

  function goNext() {
    if (step === 1 && !validateStep1()) return;
    if (step === 2 && !validateStep2()) return;
    if (step === 3 && !validateStep3()) return;
    if (step === 4 && !validateStep4()) return;
    setAnimating(true);
    setTimeout(() => {
      setStep((s) => Math.min(5, s + 1));
      setAnimating(false);
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }, 50);
    }, 150);
  }

  function goBack() {
    setFormError(null);
    setAnimating(true);
    setTimeout(() => {
      setStep((s) => Math.max(1, s - 1));
      setAnimating(false);
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      }, 50);
    }, 150);
  }

  async function handleSubmit() {
    if (!validateStep5()) return;
    const l = lead ?? readLead();
    if (!l) {
      setFormError("Lead data is missing. Return to the diagnostic start page.");
      return;
    }

    const doors = Number.parseInt(doorCount, 10);
    const props = Number.parseInt(propertyCount, 10);
    const staff = Number.parseInt(staffCount, 10);
    const vendors = Number.parseInt(vendorCount, 10);

    const resolvedPms = pmsPlatform === "Other" ? pmsOther.trim() : pmsPlatform;

    const survey: SurveyResponse = {
      door_count: doors,
      property_count: props,
      pms_platform: resolvedPms,
      staff_count: staff,
      vendor_count: vendors,
      trades_covered: trades,
      has_written_emergency_protocols:
        writtenEmergency as NonNullable<
          SurveyResponse["has_written_emergency_protocols"]
        >,
      has_defined_ntes: definedNtes as NonNullable<
        SurveyResponse["has_defined_ntes"]
      >,
      ntes_are_tiered: definedNtes === "yes" ? ntesTiered : false,
      has_defined_slas: definedSlas as NonNullable<
        SurveyResponse["has_defined_slas"]
      >,
      estimated_response_time:
        responseTime as SurveyResponse["estimated_response_time"],
      estimated_completion_time:
        completionTime as SurveyResponse["estimated_completion_time"],
      after_hours_method: afterHours as SurveyResponse["after_hours_method"],
      primary_goal: primaryGoal as NonNullable<
        SurveyResponse["primary_goal"]
      >,
      pain_points: painPoints,
    };

    const clientInfo: ClientInfo = {
      company_name: companyName.trim(),
      door_count: doors,
      property_count: props,
      pms_platform: resolvedPms,
      operational_model: operationalModel as "va" | "tech",
      operational_model_display:
        operationalModel === "va"
          ? "VA Coordinators"
          : operationalModel === "tech"
            ? "In-House Tech Team"
            : undefined,
      staff_count: staff,
      primary_goal: primaryGoal as NonNullable<ClientInfo["primary_goal"]>,
      contact_name: l.name,
      contact_email: l.email,
      data_source: "quick_survey",
    };

    setLoading(true);
    setFormError(null);
    try {
      if (typeof sessionStorage !== "undefined") {
        sessionStorage.setItem(RESULTS_SOURCE_KEY, "quick");
      }
      const result = await runQuickDiagnostic({
        lead: l,
        survey,
        client_info: clientInfo,
      });
      router.push(`/diagnostic/results/${result.diagnostic_id}`);
    } catch (e) {
      setFormError(
        e instanceof Error
          ? e.message
          : "We could not complete the diagnostic. Please try again."
      );
      setLoading(false);
    }
  }

  const inputClass =
    "border-vendoroo-border bg-vendoroo-surface text-vendoroo-text placeholder:text-vendoroo-muted";

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 rounded-xl border border-vendoroo-border bg-vendoroo-surface p-6 shadow-sm sm:p-8 pb-16 sm:pb-20">
      <DiagnosticProgress step={step} />

      <div
        className={[
          "transition-all duration-150 ease-in-out",
          animating ? "translate-y-1 opacity-0" : "translate-y-0 opacity-100",
        ].join(" ")}
      >
        {step === 1 ? (
          <section className="space-y-6" aria-labelledby="s1-heading">
            <div>
              <h2
                id="s1-heading"
                className="text-lg font-medium tracking-tight text-vendoroo-text"
              >
                Your portfolio
              </h2>
              <p className="mt-1 text-sm text-vendoroo-muted">
                Tell us about your operation so we can benchmark against similar portfolios.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="co-name">Company name</Label>
              <Input
                id="co-name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className={inputClass}
                autoComplete="organization"
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="doors">Door count</Label>
                <Input
                  id="doors"
                  inputMode="numeric"
                  value={doorCount}
                  onChange={(e) => setDoorCount(e.target.value)}
                  className={inputClass}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="props">Property count</Label>
                <Input
                  id="props"
                  inputMode="numeric"
                  value={propertyCount}
                  onChange={(e) => setPropertyCount(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>PMS platform</Label>
              <Select
                value={pmsPlatform || undefined}
                onValueChange={(v) => { setPmsPlatform(v ?? ""); setPmsOther(""); }}
              >
                <SelectTrigger className={`w-full ${inputClass}`}>
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {PMS_OPTIONS.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {pmsPlatform === "Other" && (
                <Input
                  id="pms-other"
                  placeholder="Which PMS do you use?"
                  value={pmsOther}
                  onChange={(e) => setPmsOther(e.target.value)}
                  className={inputClass}
                />
              )}
            </div>
            <div className="space-y-3">
              <Label>Operational model</Label>
              <RadioGroup
                value={operationalModel || undefined}
                onValueChange={(v) => setOperationalModel(v as "va" | "tech")}
                className="grid gap-3"
              >
                <label className={radioCardClass(operationalModel === "va")}>
                  <RadioGroupItem value="va" id="om-va" />
                  <span>
                    <span className="block font-medium text-vendoroo-text">
                      VA Coordinators
                    </span>
                    <span className="text-sm text-vendoroo-muted">
                      Centralized coordinators triage and dispatch vendor work.
                    </span>
                  </span>
                </label>
                <label className={radioCardClass(operationalModel === "tech")}>
                  <RadioGroupItem value="tech" id="om-tech" />
                  <span>
                    <span className="block font-medium text-vendoroo-text">
                      In-House Tech Team
                    </span>
                    <span className="text-sm text-vendoroo-muted">
                      Dedicated technicians handle a share of work orders
                      internally.
                    </span>
                  </span>
                </label>
              </RadioGroup>
            </div>
            <div className="space-y-2">
              <Label htmlFor="staff">Staff count (maintenance &amp; ops)</Label>
              <Input
                id="staff"
                inputMode="numeric"
                value={staffCount}
                onChange={(e) => setStaffCount(e.target.value)}
                className={inputClass}
              />
            </div>
          </section>
        ) : null}

        {step === 2 ? (
          <section className="space-y-6" aria-labelledby="s2-heading">
            <div>
              <h2
                id="s2-heading"
                className="text-lg font-medium tracking-tight text-vendoroo-text"
              >
                Vendor network
              </h2>
              <p className="mt-1 text-sm text-vendoroo-muted">
                How deep is your bench? Select every trade you have a vendor relationship for.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="vendors">Active vendor count</Label>
              <Input
                id="vendors"
                inputMode="numeric"
                value={vendorCount}
                onChange={(e) => setVendorCount(e.target.value)}
                className={inputClass}
              />
            </div>
            <div className="space-y-3">
              <div className="flex items-baseline justify-between gap-2">
                <Label>Trades covered</Label>
                <span className={[
                  "text-xs font-semibold tabular-nums transition-colors",
                  trades.length >= 12 ? "text-[#34ba49]" : trades.length >= 8 ? "text-vendoroo-main" : "text-vendoroo-muted",
                ].join(" ")}>
                  {trades.length} of 12 required trades
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {TRADES.map((t) => {
                  const selected = trades.includes(t.id);
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => toggleTrade(t.id)}
                      className={[
                        "flex items-center gap-2 rounded-lg border px-3 py-2.5 text-left text-sm transition-all duration-150",
                        selected
                          ? "border-vendoroo-main bg-vendoroo-tint/30 font-medium text-vendoroo-main-dark"
                          : "border-vendoroo-border bg-vendoroo-surface text-vendoroo-smoke hover:border-vendoroo-muted/50",
                      ].join(" ")}
                    >
                      <span className={[
                        "flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] transition-all duration-150",
                        selected
                          ? "bg-vendoroo-main text-white"
                          : "bg-vendoroo-border text-vendoroo-muted",
                      ].join(" ")}>
                        {selected ? "✓" : ""}
                      </span>
                      {t.label}
                    </button>
                  );
                })}
              </div>
              {trades.length === 12 && (
                <p className="text-xs font-medium text-[#34ba49]">
                  Full coverage across all required trades
                </p>
              )}
            </div>
          </section>
        ) : null}

        {step === 3 ? (
          <section className="space-y-6" aria-labelledby="s3-heading">
            <div>
              <h2
                id="s3-heading"
                className="text-lg font-medium tracking-tight text-vendoroo-text"
              >
                Policies &amp; controls
              </h2>
              <p className="mt-1 text-sm text-vendoroo-muted">
                AI needs rules to follow. The more you have documented, the faster you go live.
              </p>
            </div>
            <PolicyRadio
              label="Written emergency protocols?"
              value={writtenEmergency}
              onChange={setWrittenEmergency}
              name="emergency"
            />
            <PolicyRadio
              label="Defined not-to-exceed (NTE) limits?"
              value={definedNtes}
              onChange={setDefinedNtes}
              name="nte"
            />
            {definedNtes === "yes" ? (
              <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-vendoroo-border bg-vendoroo-surface p-4">
                <Checkbox
                  checked={ntesTiered}
                  onCheckedChange={(c) => setNtesTiered(c === true)}
                  className="mt-0.5 border-vendoroo-border"
                />
                <span className="text-sm text-vendoroo-smoke">
                  NTEs are tiered by trade or cost band (not a single flat cap).
                </span>
              </label>
            ) : null}
            <PolicyRadio
              label="Defined SLAs with vendors?"
              value={definedSlas}
              onChange={setDefinedSlas}
              name="sla"
            />
          </section>
        ) : null}

        {step === 4 ? (
          <section className="space-y-6" aria-labelledby="s4-heading">
            <div>
              <h2
                id="s4-heading"
                className="text-lg font-medium tracking-tight text-vendoroo-text"
              >
                Current performance
              </h2>
              <p className="mt-1 text-sm text-vendoroo-muted">
                How fast does your team move today? We'll benchmark these against AI-assisted portfolios.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Typical first response time</Label>
              <Select
                value={responseTime || undefined}
                onValueChange={(v) => setResponseTime(v ?? "")}
                items={RESPONSE_TIME_OPTIONS}
              >
                <SelectTrigger className={`w-full ${inputClass}`}>
                  <SelectValue placeholder="Select response window" />
                </SelectTrigger>
                <SelectContent>
                  {RESPONSE_TIME_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Typical completion time</Label>
              <Select
                value={completionTime || undefined}
                onValueChange={(v) => setCompletionTime(v ?? "")}
                items={COMPLETION_TIME_OPTIONS}
              >
                <SelectTrigger className={`w-full ${inputClass}`}>
                  <SelectValue placeholder="Select completion window" />
                </SelectTrigger>
                <SelectContent>
                  {COMPLETION_TIME_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-3">
              <Label>After-hours coverage method</Label>
              <RadioGroup
                value={afterHours || undefined}
                onValueChange={setAfterHours}
                className="grid gap-3"
              >
                <label className={radioCardClass(afterHours === "24_7_coverage")}>
                  <RadioGroupItem value="24_7_coverage" id="ah-247" />
                  <span className="text-vendoroo-text">24/7 coverage</span>
                </label>
                <label
                  className={radioCardClass(afterHours === "answering_service")}
                >
                  <RadioGroupItem value="answering_service" id="ah-ans" />
                  <span className="text-vendoroo-text">Answering service</span>
                </label>
                <label
                  className={radioCardClass(afterHours === "on_call_rotation")}
                >
                  <RadioGroupItem value="on_call_rotation" id="ah-oncall" />
                  <span className="text-vendoroo-text">On-call rotation</span>
                </label>
                <label
                  className={radioCardClass(afterHours === "voicemail_only")}
                >
                  <RadioGroupItem value="voicemail_only" id="ah-vm" />
                  <span className="text-vendoroo-text">Voicemail only</span>
                </label>
                <label className={radioCardClass(afterHours === "none")}>
                  <RadioGroupItem value="none" id="ah-none" />
                  <span className="text-vendoroo-text">None</span>
                </label>
              </RadioGroup>
            </div>
          </section>
        ) : null}

        {step === 5 ? (
          <section className="space-y-6" aria-labelledby="s5-heading">
            <div>
              <h2
                id="s5-heading"
                className="text-lg font-medium tracking-tight text-vendoroo-text"
              >
                Your goal
              </h2>
              <p className="mt-1 text-sm text-vendoroo-muted">
                What does success look like in the next two quarters? This shapes your recommended plan.
              </p>
            </div>
            <div className="space-y-3">
              <Label>Primary goal</Label>
              <RadioGroup
                value={primaryGoal || undefined}
                onValueChange={(v) =>
                  setPrimaryGoal(v as "scale" | "optimize" | "elevate")
                }
                className="grid gap-3"
              >
                <label className={radioCardClass(primaryGoal === "scale")}>
                  <RadioGroupItem value="scale" id="g-scale" />
                  <span>
                    <span className="block font-medium text-vendoroo-text">Scale</span>
                    <span className="text-sm text-vendoroo-muted">
                      Grow portfolio without adding headcount.
                    </span>
                  </span>
                </label>
                <label className={radioCardClass(primaryGoal === "optimize")}>
                  <RadioGroupItem value="optimize" id="g-opt" />
                  <span>
                    <span className="block font-medium text-vendoroo-text">
                      Optimize
                    </span>
                    <span className="text-sm text-vendoroo-muted">
                      Reduce costs and tighten response time.
                    </span>
                  </span>
                </label>
                <label className={radioCardClass(primaryGoal === "elevate")}>
                  <RadioGroupItem value="elevate" id="g-el" />
                  <span>
                    <span className="block font-medium text-vendoroo-text">Elevate</span>
                    <span className="text-sm text-vendoroo-muted">
                      Premium service positioning for higher-value properties.
                    </span>
                  </span>
                </label>
              </RadioGroup>
            </div>
            <div className="space-y-3">
              <div className="flex items-baseline justify-between gap-2">
                <Label>Biggest pain points</Label>
                <span className="text-xs text-vendoroo-muted">
                  {painPoints.length} of 3 selected
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {PAIN_OPTIONS.map((p) => {
                  const checked = painPoints.includes(p.id);
                  const disabled = !checked && painPoints.length >= 3;
                  return (
                    <label
                      key={p.id}
                      className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-sm ${
                        disabled
                          ? "cursor-not-allowed border-vendoroo-border/50 text-vendoroo-muted"
                          : "cursor-pointer border-vendoroo-border bg-vendoroo-surface text-vendoroo-smoke hover:border-vendoroo-muted/50"
                      }`}
                    >
                      <Checkbox
                        checked={checked}
                        disabled={disabled}
                        onCheckedChange={() => togglePain(p.id)}
                        className="border-vendoroo-border"
                      />
                      {p.label}
                    </label>
                  );
                })}
              </div>
            </div>
          </section>
        ) : null}
      </div>

      {formError ? (
        <p className="text-sm text-amber-700" role="alert">
          {formError}
        </p>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={goBack}
          disabled={step === 1 || loading}
          className="border-vendoroo-border text-vendoroo-text hover:bg-vendoroo-light"
        >
          Back
        </Button>
        {step < 5 ? (
          <Button
            type="button"
            onClick={goNext}
            disabled={loading}
            className="rounded-full text-sm font-medium uppercase tracking-[-0.02em] sm:min-w-40 sm:px-8"
          >
            Next
          </Button>
        ) : (
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="rounded-full text-sm font-medium uppercase tracking-[-0.02em] sm:min-w-40 sm:px-8"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="size-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Analyzing
              </span>
            ) : "Run diagnostic"}
          </Button>
        )}
      </div>

      {loading ? <AnalyzingIndicator /> : null}
    </div>
  );
}
