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

const PMS_OPTIONS = ["AppFolio", "Buildium", "RentManager", "Other"] as const;

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
    "flex cursor-pointer items-start gap-3 rounded-xl border p-4 text-left transition-colors",
    active
      ? "border-[#6366F1] bg-[#6366F1]/10 ring-1 ring-[#6366F1]/40"
      : "border-white/10 bg-[#0B1220] hover:border-white/20",
  ].join(" ");
}

export function SurveyFlow() {
  const router = useRouter();
  const [step, setStep] = React.useState(1);
  const [lead, setLead] = React.useState<LeadCapture | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const [companyName, setCompanyName] = React.useState("");
  const [doorCount, setDoorCount] = React.useState("");
  const [propertyCount, setPropertyCount] = React.useState("");
  const [pmsPlatform, setPmsPlatform] = React.useState<string>("");
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
    setStep((s) => Math.min(5, s + 1));
  }

  function goBack() {
    setFormError(null);
    setStep((s) => Math.max(1, s - 1));
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

    const survey: SurveyResponse = {
      door_count: doors,
      property_count: props,
      pms_platform: pmsPlatform,
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
      pms_platform: pmsPlatform,
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
    "border-white/15 bg-[#0B1220] text-slate-100 placeholder:text-slate-500";

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 pb-16">
      <DiagnosticProgress step={step} />

      {step === 1 ? (
        <section className="space-y-6" aria-labelledby="s1-heading">
          <div>
            <h2
              id="s1-heading"
              className="text-lg font-medium tracking-tight text-slate-100"
            >
              Company basics
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Establish scope and how your maintenance desk is staffed.
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
              onValueChange={(v) => setPmsPlatform(v ?? "")}
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
                  <span className="block font-medium text-slate-100">
                    VA Coordinators
                  </span>
                  <span className="text-sm text-slate-400">
                    Centralized coordinators triage and dispatch vendor work.
                  </span>
                </span>
              </label>
              <label className={radioCardClass(operationalModel === "tech")}>
                <RadioGroupItem value="tech" id="om-tech" />
                <span>
                  <span className="block font-medium text-slate-100">
                    In-House Tech Team
                  </span>
                  <span className="text-sm text-slate-400">
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
              className="text-lg font-medium tracking-tight text-slate-100"
            >
              Vendor coverage
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Quantify vendor depth across the trades you rely on most.
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
            <Label>Trades covered</Label>
            <div className="grid gap-3 sm:grid-cols-2">
              {TRADES.map((t) => (
                <label
                  key={t.id}
                  className="flex cursor-pointer items-center gap-3 rounded-lg border border-white/10 bg-[#0B1220] px-3 py-2 text-sm text-slate-200 hover:border-white/20"
                >
                  <Checkbox
                    checked={trades.includes(t.id)}
                    onCheckedChange={() => toggleTrade(t.id)}
                    className="border-white/25"
                  />
                  {t.label}
                </label>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {step === 3 ? (
        <section className="space-y-6" aria-labelledby="s3-heading">
          <div>
            <h2
              id="s3-heading"
              className="text-lg font-medium tracking-tight text-slate-100"
            >
              Policies
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Documented rules reduce variance when urgency is high.
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
            <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-white/10 bg-[#0B1220] p-4">
              <Checkbox
                checked={ntesTiered}
                onCheckedChange={(c) => setNtesTiered(c === true)}
                className="mt-0.5 border-white/25"
              />
              <span className="text-sm text-slate-200">
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
              className="text-lg font-medium tracking-tight text-slate-100"
            >
              Operations
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Typical response behavior across the work order lifecycle.
            </p>
          </div>
          <div className="space-y-2">
            <Label>Typical first response time</Label>
            <Select
              value={responseTime || undefined}
              onValueChange={(v) => setResponseTime(v ?? "")}
            >
              <SelectTrigger className={`w-full ${inputClass}`}>
                <SelectValue placeholder="Select response window" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="under_1hr">Under 1 hour</SelectItem>
                <SelectItem value="1_4hrs">1–4 hours</SelectItem>
                <SelectItem value="4_12hrs">4–12 hours</SelectItem>
                <SelectItem value="same_day">Same day</SelectItem>
                <SelectItem value="next_day">Next day</SelectItem>
                <SelectItem value="unsure">Unsure</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Typical completion time</Label>
            <Select
              value={completionTime || undefined}
              onValueChange={(v) => setCompletionTime(v ?? "")}
            >
              <SelectTrigger className={`w-full ${inputClass}`}>
                <SelectValue placeholder="Select completion window" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1_3days">1–3 days</SelectItem>
                <SelectItem value="3_7days">3–7 days</SelectItem>
                <SelectItem value="7_14days">7–14 days</SelectItem>
                <SelectItem value="14plus">14+ days</SelectItem>
                <SelectItem value="unsure">Unsure</SelectItem>
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
                <span className="text-slate-100">24/7 coverage</span>
              </label>
              <label
                className={radioCardClass(afterHours === "answering_service")}
              >
                <RadioGroupItem value="answering_service" id="ah-ans" />
                <span className="text-slate-100">Answering service</span>
              </label>
              <label
                className={radioCardClass(afterHours === "on_call_rotation")}
              >
                <RadioGroupItem value="on_call_rotation" id="ah-oncall" />
                <span className="text-slate-100">On-call rotation</span>
              </label>
              <label
                className={radioCardClass(afterHours === "voicemail_only")}
              >
                <RadioGroupItem value="voicemail_only" id="ah-vm" />
                <span className="text-slate-100">Voicemail only</span>
              </label>
              <label className={radioCardClass(afterHours === "none")}>
                <RadioGroupItem value="none" id="ah-none" />
                <span className="text-slate-100">None</span>
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
              className="text-lg font-medium tracking-tight text-slate-100"
            >
              Goals
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Prioritize what success looks like over the next two quarters.
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
                  <span className="block font-medium text-slate-100">Scale</span>
                  <span className="text-sm text-slate-400">
                    Grow portfolio without adding headcount.
                  </span>
                </span>
              </label>
              <label className={radioCardClass(primaryGoal === "optimize")}>
                <RadioGroupItem value="optimize" id="g-opt" />
                <span>
                  <span className="block font-medium text-slate-100">
                    Optimize
                  </span>
                  <span className="text-sm text-slate-400">
                    Reduce costs and tighten response time.
                  </span>
                </span>
              </label>
              <label className={radioCardClass(primaryGoal === "elevate")}>
                <RadioGroupItem value="elevate" id="g-el" />
                <span>
                  <span className="block font-medium text-slate-100">Elevate</span>
                  <span className="text-sm text-slate-400">
                    Premium service positioning for higher-value properties.
                  </span>
                </span>
              </label>
            </RadioGroup>
          </div>
          <div className="space-y-3">
            <div className="flex items-baseline justify-between gap-2">
              <Label>Biggest pain points</Label>
              <span className="text-xs text-slate-500">
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
                        ? "cursor-not-allowed border-white/5 text-slate-500"
                        : "cursor-pointer border-white/10 bg-[#0B1220] text-slate-200 hover:border-white/20"
                    }`}
                  >
                    <Checkbox
                      checked={checked}
                      disabled={disabled}
                      onCheckedChange={() => togglePain(p.id)}
                      className="border-white/25"
                    />
                    {p.label}
                  </label>
                );
              })}
            </div>
          </div>
        </section>
      ) : null}

      {formError ? (
        <p className="text-sm text-amber-400" role="alert">
          {formError}
        </p>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={goBack}
          disabled={step === 1 || loading}
          className="border-white/20 text-slate-200 hover:bg-white/5"
        >
          Back
        </Button>
        {step < 5 ? (
          <Button
            type="button"
            onClick={goNext}
            disabled={loading}
            className="bg-[#6366F1] text-white hover:bg-[#4F46E5] sm:min-w-40"
          >
            Next
          </Button>
        ) : (
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="bg-[#6366F1] text-white hover:bg-[#4F46E5] sm:min-w-40"
          >
            {loading ? "Analyzing your operations..." : "Submit diagnostic"}
          </Button>
        )}
      </div>

      {loading ? (
        <p className="text-center text-sm text-slate-400">
          Analyzing your operations…
        </p>
      ) : null}
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
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <RadioGroup
        value={value || undefined}
        onValueChange={(v) => onChange(v as "yes" | "no" | "unsure")}
        className="flex flex-wrap gap-4"
      >
        <label className="flex items-center gap-2 text-sm text-slate-200">
          <RadioGroupItem value="yes" id={`${name}-yes`} />
          Yes
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-200">
          <RadioGroupItem value="no" id={`${name}-no`} />
          No
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-200">
          <RadioGroupItem value="unsure" id={`${name}-un`} />
          Unsure
        </label>
      </RadioGroup>
    </div>
  );
}
