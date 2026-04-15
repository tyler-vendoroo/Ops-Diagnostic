"use client";

const STEP_LABELS = ["Portfolio", "Vendors", "Policies", "Operations", "Goals"];

export function DiagnosticProgress({ step }: { step: number }) {
  return (
    <nav aria-label="Diagnostic progress" className="flex items-center justify-between gap-1">
      {STEP_LABELS.map((label, i) => {
        const stepNum = i + 1;
        const isComplete = stepNum < step;
        const isCurrent = stepNum === step;

        return (
          <div key={label} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={[
                  "flex size-8 items-center justify-center rounded-full text-xs font-semibold transition-all duration-300",
                  isComplete
                    ? "bg-vendoroo-main text-white"
                    : isCurrent
                      ? "bg-vendoroo-main text-white ring-4 ring-vendoroo-tint/50"
                      : "bg-vendoroo-border text-vendoroo-muted",
                ].join(" ")}
              >
                {isComplete ? (
                  <svg className="size-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stepNum
                )}
              </div>
              <span
                className={[
                  "text-[11px] font-medium transition-colors duration-300",
                  isCurrent ? "text-vendoroo-main" : isComplete ? "text-vendoroo-smoke" : "text-vendoroo-muted",
                ].join(" ")}
              >
                {label}
              </span>
            </div>
            {stepNum < STEP_LABELS.length && (
              <div
                className={[
                  "mx-1 h-0.5 flex-1 rounded-full transition-colors duration-500",
                  isComplete ? "bg-vendoroo-main" : "bg-vendoroo-border",
                ].join(" ")}
              />
            )}
          </div>
        );
      })}
    </nav>
  );
}
