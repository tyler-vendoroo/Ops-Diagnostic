"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { DiagnosticProgress } from "@/components/diagnostic/DiagnosticProgress";
import { RequireLeadGate } from "@/components/diagnostic/RequireLeadGate";

const LEAD_KEY = "vendoroo_ops_diagnostic_lead";
const CLIENT_INFO_KEY = "vendoroo_diagnostic_client_info";

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

const STATUS_MESSAGES = [
  "Uploading files...",
  "Processing work orders...",
  "Analyzing documents...",
  "Generating report...",
];

interface StoredLead {
  name?: string;
  email?: string;
  company?: string;
  phone?: string;
  lead_id?: string;
  terms_accepted?: boolean;
}

interface StoredClientInfo {
  company_name?: string;
  door_count?: number | string;
  property_count?: number | string;
  pms_platform?: string;
  operational_model?: string;
  staff_count?: number | string;
  primary_goal?: string;
}

function readLocalStorage<T>(key: string): T | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface DropzoneProps {
  label: string;
  helper: string;
  accept: string;
  file: File | null;
  onFile: (file: File | null) => void;
  required?: boolean;
}

function Dropzone({ label, helper, accept, file, onFile, required }: DropzoneProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = React.useState(false);

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) onFile(dropped);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    if (selected) onFile(selected);
    // Reset input so the same file can be re-selected after removal
    e.target.value = "";
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1.5">
        <span className="text-sm font-medium text-vendoroo-text">{label}</span>
        {required && (
          <span className="text-xs font-medium uppercase tracking-wide text-vendoroo-main">
            required
          </span>
        )}
      </div>
      <p className="text-xs text-vendoroo-muted">{helper}</p>

      {file ? (
        <div className="flex items-center justify-between rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-vendoroo-text">
              {file.name}
            </p>
            <p className="text-xs text-vendoroo-muted">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={() => onFile(null)}
            className="ml-4 shrink-0 text-xs font-medium text-vendoroo-muted transition-colors hover:text-vendoroo-text"
          >
            Remove
          </button>
        </div>
      ) : (
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={[
            "flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors",
            dragOver
              ? "border-vendoroo-main bg-vendoroo-light"
              : "border-vendoroo-border bg-vendoroo-surface hover:border-vendoroo-muted/50",
          ].join(" ")}
        >
          <svg
            className="h-6 w-6 text-vendoroo-muted"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
          <p className="text-sm text-vendoroo-muted">
            <span className="font-medium text-vendoroo-main">Click to browse</span>
            {" "}or drag and drop
          </p>
          <p className="text-xs text-vendoroo-muted/70">
            {accept.split(",").join(", ")}
          </p>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={handleChange}
      />
    </div>
  );
}

function FullDiagnosticContent() {
  const router = useRouter();

  // ── Determine initial step ─────────────────────────────────────────────────
  const [step, setStep] = React.useState<1 | 2>(1);

  // ── Company info fields ────────────────────────────────────────────────────
  const [companyName, setCompanyName] = React.useState("");
  const [doorCount, setDoorCount] = React.useState("");
  const [propertyCount, setPropertyCount] = React.useState("");
  const [pmsPlatform, setPmsPlatform] = React.useState("");
  const [pmsOther, setPmsOther] = React.useState("");
  const [operationalModel, setOperationalModel] = React.useState<"va" | "tech" | "">("");
  const [staffCount, setStaffCount] = React.useState("");
  const [primaryGoal, setPrimaryGoal] = React.useState<"scale" | "optimize" | "elevate" | "">("");

  // ── File state ─────────────────────────────────────────────────────────────
  const [workOrderFile, setWorkOrderFile] = React.useState<File | null>(null);
  const [leaseFile, setLeaseFile] = React.useState<File | null>(null);
  const [pmaFile, setPmaFile] = React.useState<File | null>(null);
  const [vendorDirFile, setVendorDirFile] = React.useState<File | null>(null);

  // ── UI state ───────────────────────────────────────────────────────────────
  const [submitting, setSubmitting] = React.useState(false);
  const [statusMsg, setStatusMsg] = React.useState(STATUS_MESSAGES[0]);
  const [error, setError] = React.useState<string | null>(null);

  // ── Pre-fill from localStorage ─────────────────────────────────────────────
  React.useEffect(() => {
    const lead = readLocalStorage<StoredLead>(LEAD_KEY);
    const saved = readLocalStorage<StoredClientInfo>(CLIENT_INFO_KEY);

    if (lead?.company) setCompanyName(lead.company);

    if (saved) {
      if (saved.company_name) setCompanyName(saved.company_name);
      if (saved.door_count != null) setDoorCount(String(saved.door_count));
      if (saved.property_count != null) setPropertyCount(String(saved.property_count));
      if (saved.pms_platform) setPmsPlatform(saved.pms_platform);
      if (saved.operational_model === "va" || saved.operational_model === "tech") {
        setOperationalModel(saved.operational_model);
      }
      if (saved.staff_count != null) setStaffCount(String(saved.staff_count));
      if (
        saved.primary_goal === "scale" ||
        saved.primary_goal === "optimize" ||
        saved.primary_goal === "elevate"
      ) {
        setPrimaryGoal(saved.primary_goal);
      }
    }
    // Always show step 1 so the user can verify pre-filled data before uploading
  }, []);

  // ── Status message cycling ─────────────────────────────────────────────────
  React.useEffect(() => {
    if (!submitting) return;
    let idx = 0;
    setStatusMsg(STATUS_MESSAGES[0]);
    const interval = setInterval(() => {
      idx = Math.min(idx + 1, STATUS_MESSAGES.length - 1);
      setStatusMsg(STATUS_MESSAGES[idx]);
    }, 4000);
    return () => clearInterval(interval);
  }, [submitting]);

  // ── Step 1 submit ──────────────────────────────────────────────────────────
  function handleContinue(e: React.FormEvent) {
    e.preventDefault();
    setStep(2);
  }

  // ── Step 2 submit ──────────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!workOrderFile) return;

    setError(null);
    setSubmitting(true);

    const lead = readLocalStorage<StoredLead>(LEAD_KEY);

    const resolvedPms = pmsPlatform === "Other" ? pmsOther.trim() || "Other" : pmsPlatform || "Other";

    const clientInfo = {
      company_name: companyName || "Unknown Company",
      door_count: doorCount ? Number(doorCount) : 100,
      property_count: propertyCount ? Number(propertyCount) : 1,
      pms_platform: resolvedPms,
      operational_model: operationalModel || "va",
      staff_count: staffCount ? Number(staffCount) : 1,
      primary_goal: primaryGoal || "scale",
    };

    const formData = new FormData();
    formData.append("work_order_file", workOrderFile);
    if (leaseFile) formData.append("lease_file", leaseFile);
    if (pmaFile) formData.append("pma_file", pmaFile);
    if (vendorDirFile) formData.append("vendor_directory_file", vendorDirFile);
    formData.append("client_info", JSON.stringify(clientInfo));
    if (lead?.lead_id) formData.append("lead_id", lead.lead_id);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/diagnostic/full`,
        {
          method: "POST",
          body: formData,
          // No Content-Type header — let the browser set multipart/form-data with boundary
        }
      );

      if (!res.ok) {
        const text = await res.text().catch(() => "Unknown error");
        throw new Error(text || `Server error ${res.status}`);
      }

      const data = (await res.json()) as { diagnostic_id: string };
      router.push(`/diagnostic/results/${data.diagnostic_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  // ── Processing overlay ─────────────────────────────────────────────────────
  if (submitting) {
    return (
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
        <div className="flex flex-col items-center justify-center gap-6 py-24">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-vendoroo-border border-t-vendoroo-main" />
          <p className="text-sm font-medium text-vendoroo-text transition-all duration-500">
            {statusMsg}
          </p>
          <p className="text-xs text-vendoroo-muted">This may take up to a minute.</p>
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
        <div className="flex flex-col items-center gap-4 py-24 text-center">
          <p className="text-sm font-medium text-vendoroo-text">
            Something went wrong
          </p>
          <p className="max-w-sm text-xs text-vendoroo-muted">{error}</p>
          <button
            type="button"
            onClick={() => setError(null)}
            className="mt-2 rounded-full border border-vendoroo-border bg-vendoroo-surface px-6 py-2.5 text-sm font-medium text-vendoroo-text transition-colors hover:bg-vendoroo-light"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  // ── Main layout ────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-normal tracking-[-0.03em] text-vendoroo-text sm:text-2xl">
            Full diagnostic
          </h1>
          <p className="mt-1 text-sm text-vendoroo-muted">
            Upload your operational files for a complete data-grounded analysis.
          </p>
        </div>
        <Link
          href="/diagnostic"
          className="text-sm font-medium text-vendoroo-main transition-colors hover:text-vendoroo-main-dark"
        >
          ← Back to paths
        </Link>
      </div>

      {/* Progress */}
      <div className="mb-8">
        <DiagnosticProgress step={step === 1 ? 4 : 5} />
      </div>

      {/* Step 1 — Company info */}
      {step === 1 && (
        <form onSubmit={handleContinue} className="flex flex-col gap-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {/* Company name */}
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-sm font-medium text-vendoroo-text" htmlFor="company">
                Company name
              </label>
              <input
                id="company"
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
                placeholder="Acme Property Management"
              />
            </div>

            {/* Door count */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-vendoroo-text" htmlFor="door-count">
                Door count
              </label>
              <input
                id="door-count"
                type="number"
                min={1}
                required
                value={doorCount}
                onChange={(e) => setDoorCount(e.target.value)}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
                placeholder="500"
              />
            </div>

            {/* Property count */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-vendoroo-text" htmlFor="property-count">
                Property count
              </label>
              <input
                id="property-count"
                type="number"
                min={1}
                required
                value={propertyCount}
                onChange={(e) => setPropertyCount(e.target.value)}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
                placeholder="120"
              />
            </div>

            {/* PMS platform */}
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-sm font-medium text-vendoroo-text" htmlFor="pms">
                PMS platform
              </label>
              <select
                id="pms"
                required
                value={pmsPlatform}
                onChange={(e) => { setPmsPlatform(e.target.value); setPmsOther(""); }}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
              >
                <option value="" disabled>Select platform</option>
                {PMS_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
              {pmsPlatform === "Other" && (
                <input
                  id="pms-other"
                  type="text"
                  placeholder="Which PMS do you use?"
                  value={pmsOther}
                  onChange={(e) => setPmsOther(e.target.value)}
                  className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
                />
              )}
            </div>

            {/* Staff count */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-vendoroo-text" htmlFor="staff-count">
                Staff count
              </label>
              <input
                id="staff-count"
                type="number"
                min={1}
                value={staffCount}
                onChange={(e) => setStaffCount(e.target.value)}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-4 py-2.5 text-sm text-vendoroo-text placeholder:text-vendoroo-muted focus:outline-none focus:ring-2 focus:ring-vendoroo-main/30"
                placeholder="8"
              />
            </div>
          </div>

          {/* Operational model */}
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-vendoroo-text">Operational model</span>
            <div className="grid gap-3 sm:grid-cols-2">
              {(
                [
                  { value: "va", label: "VA Coordinators", desc: "Offshore or contract coordinators handle dispatch" },
                  { value: "tech", label: "In-House Tech Team", desc: "Dedicated internal maintenance staff" },
                ] as const
              ).map(({ value, label, desc }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setOperationalModel(value)}
                  className={[
                    "flex cursor-pointer items-start gap-3 rounded-xl border p-4 text-left transition-colors",
                    operationalModel === value
                      ? "border-vendoroo-main bg-vendoroo-light ring-1 ring-vendoroo-main/30"
                      : "border-vendoroo-border bg-vendoroo-surface hover:border-vendoroo-muted/40",
                  ].join(" ")}
                >
                  <div>
                    <p className="text-sm font-medium text-vendoroo-text">{label}</p>
                    <p className="mt-0.5 text-xs text-vendoroo-muted">{desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Primary goal */}
          <div className="flex flex-col gap-2">
            <span className="text-sm font-medium text-vendoroo-text">Primary goal</span>
            <div className="grid gap-3 sm:grid-cols-3">
              {(
                [
                  { value: "scale", label: "Scale", desc: "Grow without adding headcount" },
                  { value: "optimize", label: "Optimize", desc: "Improve ops efficiency" },
                  { value: "elevate", label: "Elevate", desc: "Raise service quality" },
                ] as const
              ).map(({ value, label, desc }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setPrimaryGoal(value)}
                  className={[
                    "flex cursor-pointer flex-col rounded-xl border p-4 text-left transition-colors",
                    primaryGoal === value
                      ? "border-vendoroo-main bg-vendoroo-light ring-1 ring-vendoroo-main/30"
                      : "border-vendoroo-border bg-vendoroo-surface hover:border-vendoroo-muted/40",
                  ].join(" ")}
                >
                  <p className="text-sm font-medium text-vendoroo-text">{label}</p>
                  <p className="mt-0.5 text-xs text-vendoroo-muted">{desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <button
              type="submit"
              className="rounded-full bg-vendoroo-main px-8 py-3 text-sm font-medium text-white transition-colors hover:bg-vendoroo-main/90 disabled:opacity-50"
            >
              Continue to uploads
            </button>
          </div>
        </form>
      )}

      {/* Step 2 — File uploads */}
      {step === 2 && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-8">
          <Dropzone
            label="Work Order History"
            helper="Export from your PMS. 12 months of data recommended."
            accept=".csv,.xlsx,.xls,.tsv,.json"
            file={workOrderFile}
            onFile={setWorkOrderFile}
            required
          />
          <Dropzone
            label="Lease Agreement"
            helper="Template, not executed copy."
            accept=".pdf"
            file={leaseFile}
            onFile={setLeaseFile}
          />
          <Dropzone
            label="PMA"
            helper="Template, not executed copy."
            accept=".pdf"
            file={pmaFile}
            onFile={setPmaFile}
          />
          <Dropzone
            label="Vendor Directory"
            helper="Vendor name and trade minimum."
            accept=".csv,.xlsx,.xls"
            file={vendorDirFile}
            onFile={setVendorDirFile}
          />

          <div className="flex items-center gap-4 pt-2">
            <button
              type="submit"
              disabled={!workOrderFile}
              className="rounded-full bg-vendoroo-main px-8 py-3 text-sm font-medium text-white transition-colors hover:bg-vendoroo-main/90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Run Full Diagnostic
            </button>
            <button
              type="button"
              onClick={() => setStep(1)}
              className="text-sm font-medium text-vendoroo-muted transition-colors hover:text-vendoroo-text"
            >
              ← Back
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default function FullDiagnosticPage() {
  return (
    <RequireLeadGate returnPath="/diagnostic/full">
      <FullDiagnosticContent />
    </RequireLeadGate>
  );
}
