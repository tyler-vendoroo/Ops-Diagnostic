"use client";

import { Progress } from "@/components/ui/progress";

export function DiagnosticProgress({ step }: { step: number }) {
  const total = 5;
  const pct = Math.min(100, Math.round((step / total) * 100));

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>
          Step {step} of {total}
        </span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <Progress
        value={pct}
        className="[&_[data-slot=progress-indicator]]:bg-[#6366F1]"
      />
    </div>
  );
}
