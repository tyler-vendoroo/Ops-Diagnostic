import Link from "next/link";

import { RequireLeadGate } from "@/components/diagnostic/RequireLeadGate";
import { SurveyFlow } from "@/components/diagnostic/SurveyFlow";

function QuickDiagnosticContent() {
  return (
    <div className="mx-auto w-full max-w-3xl flex-1 bg-vendoroo-page px-4 py-10 sm:px-6 sm:py-14">
      <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-normal tracking-[-0.03em] text-vendoroo-text sm:text-2xl">
            Quick diagnostic
          </h1>
          <p className="mt-1 text-sm text-vendoroo-muted">
            Five short steps. Answer from the perspective of your maintenance and
            vendor coordination desk.
          </p>
        </div>
        <Link
          href="/diagnostic"
          className="text-sm font-medium text-vendoroo-main transition-colors hover:text-vendoroo-main-dark"
        >
          ← Back to paths
        </Link>
      </div>
      <SurveyFlow />
    </div>
  );
}

export default function QuickDiagnosticPage() {
  return (
    <RequireLeadGate returnPath="/diagnostic/quick">
      <QuickDiagnosticContent />
    </RequireLeadGate>
  );
}
