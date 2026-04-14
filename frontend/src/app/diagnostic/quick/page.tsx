import Link from "next/link";

import { SurveyFlow } from "@/components/diagnostic/SurveyFlow";

export default function QuickDiagnosticPage() {
  return (
    <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-10 sm:px-6 sm:py-14">
      <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
            Quick diagnostic
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Five short steps. Answer from the perspective of your maintenance and
            vendor coordination desk.
          </p>
        </div>
        <Link
          href="/diagnostic"
          className="text-sm text-[#6366F1] hover:text-[#818cf8]"
        >
          ← Back to paths
        </Link>
      </div>
      <SurveyFlow />
    </div>
  );
}
