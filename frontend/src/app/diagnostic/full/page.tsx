import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function FullDiagnosticPage() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center px-4 py-16 sm:px-6">
      <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
        Full diagnostic
      </h1>
      <p className="mt-4 text-sm leading-relaxed text-slate-400 sm:text-base">
        The full assessment pairs Vendoroo analysts with your operational
        artifacts—work order exports, vendor rosters, after-hours runbooks, and
        policy documents—to produce a data-grounded report with benchmarks
        tailored to your portfolio.
      </p>
      <p className="mt-4 text-sm leading-relaxed text-slate-400">
        Upload instructions and secure transfer details are coordinated after you
        book an intake call. If you are at an event and need an immediate read,
        complete the quick diagnostic first; we will follow up to collect files.
      </p>
      <div className="mt-10 flex flex-col gap-3 sm:flex-row">
        <a
          href="https://vendoroo.ai/contact"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            buttonVariants({
              className:
                "bg-[#6366F1] text-white hover:bg-[#4F46E5] sm:min-w-[200px]",
            })
          )}
        >
          Schedule intake
        </a>
        <Link
          href="/diagnostic"
          className={cn(
            buttonVariants({
              variant: "outline",
              className:
                "border-white/20 text-slate-100 hover:bg-white/5 sm:min-w-[200px]",
            })
          )}
        >
          Choose a different path
        </Link>
      </div>
    </div>
  );
}
