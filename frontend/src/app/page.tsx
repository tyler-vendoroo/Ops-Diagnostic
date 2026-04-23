import Link from "next/link";
import { Suspense } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { BarChart3, ClipboardList, FileStack } from "lucide-react";

import { LandingRefTracker } from "./landing-ref-tracker";

const howSteps = [
  {
    n: "Step 1",
    title: "Tell us about your operation",
    body: "5 steps covering your portfolio, vendors, policies, and goals.",
    icon: ClipboardList,
  },
  {
    n: "Step 2",
    title: "We run the diagnostics",
    body: "Benchmarked against AI-managed portfolios.",
    icon: BarChart3,
  },
  {
    n: "Step 3",
    title: "Get your prescription",
    body: "Gaps, projections, and a recommended plan.",
    icon: FileStack,
  },
] as const;

export default function Home() {
  return (
    <>
      <Suspense fallback={null}>
        <LandingRefTracker />
      </Suspense>

      <div className="flex flex-1 flex-col">
        {/* Hero */}
        <section className="relative isolate overflow-hidden bg-vendoroo-surface">
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-40%,rgba(3,156,172,0.14),transparent_55%)]"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -right-24 -top-24 size-[min(100vw,28rem)] rounded-full bg-[radial-gradient(circle_at_center,rgba(179,225,230,0.5),transparent_68%)] blur-2xl"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.3] [background-image:linear-gradient(to_right,#e1e3e4_1px,transparent_1px),linear-gradient(to_bottom,#e1e3e4_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_85%_55%_at_50%_35%,#000_50%,transparent_100%)]"
            aria-hidden
          />

          <div className="relative mx-auto max-w-4xl px-4 pb-4 pt-10 text-center sm:px-6 sm:pb-5 sm:pt-14">
            <div className="inline-flex items-center gap-2 rounded-full border border-vendoroo-border bg-vendoroo-surface/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-vendoroo-main-dark shadow-sm backdrop-blur-sm">
              <span aria-hidden>🩺</span>
              <span>NARPM Broker-Owner 2026 · Complimentary Diagnostic</span>
            </div>

            <h1 className="mt-5 text-balance font-normal leading-[1.05] tracking-[-0.05em] text-vendoroo-text sm:mt-6">
              <span className="block text-[2rem] sm:text-5xl md:text-[3.25rem]">
                Every operation has a score.
              </span>
              <span className="mt-2 block text-[2rem] sm:text-5xl md:text-[3.25rem]">
                What&apos;s yours?
              </span>
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-pretty text-base leading-relaxed text-vendoroo-muted sm:mt-6 sm:text-lg">
              5 steps. Under two minutes. We&apos;ll show you how your operation
              compares to property managers already running AI-powered
              maintenance.
            </p>

            <div className="mt-6 flex flex-col items-center sm:mt-8">
              <Link
                href="/diagnostic"
                className={cn(
                  buttonVariants({
                    size: "lg",
                    className:
                      "h-14 min-w-[280px] rounded-full px-12 text-sm font-semibold uppercase tracking-[-0.02em] shadow-lg shadow-vendoroo-text/10",
                  })
                )}
              >
                Start your diagnostic
              </Link>
              <a
                href="/sample-report.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-block text-sm font-medium text-vendoroo-main transition-colors hover:text-vendoroo-main-dark"
              >
                See a sample report →
              </a>
            </div>
          </div>

          <div className="border-t border-vendoroo-border/80 bg-vendoroo-tint/15 py-2 sm:py-2.5">
            <p className="mx-auto max-w-3xl px-4 text-center text-xs font-medium leading-snug text-vendoroo-main-dark sm:text-sm">
              Qualifying companies at NARPM Broker-Owner are eligible for 90 days
              free.{" "}
              <Link
                href="/diagnostic"
                className="font-semibold underline underline-offset-2 hover:text-vendoroo-main"
              >
                Complete your diagnostic to find out →
              </Link>
            </p>
          </div>

          {/* How it works — centered columns, tight vertical rhythm */}
          <section className="border-t border-vendoroo-border bg-vendoroo-page py-5 sm:py-6">
            <div className="mx-auto max-w-5xl px-4 sm:px-6">
              <h2 className="text-center text-xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-2xl md:text-3xl">
                How it works
              </h2>
              <div className="mt-5 grid grid-cols-1 gap-8 sm:mt-6 md:grid-cols-3 md:gap-6 lg:gap-10">
                {howSteps.map(({ n, title, body, icon: Icon }) => (
                  <div
                    key={title}
                    className="flex flex-col items-center text-center"
                  >
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-vendoroo-main">
                      {n}
                    </p>
                    <div className="mt-2.5 flex justify-center">
                      <span className="inline-flex size-11 items-center justify-center rounded-full bg-vendoroo-tint/60 text-vendoroo-main-dark ring-1 ring-vendoroo-main/15">
                        <Icon className="size-5" strokeWidth={1.75} aria-hidden />
                      </span>
                    </div>
                    <h3 className="mt-3 max-w-[16rem] text-lg font-semibold tracking-tight text-vendoroo-text">
                      {title}
                    </h3>
                    <p className="mt-2 max-w-[15.5rem] text-pretty text-sm leading-relaxed text-vendoroo-muted">
                      {body}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </section>

        {/* Two paths */}
        <section className="bg-vendoroo-surface py-8 sm:py-10">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-center text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl">
              Choose your depth
            </h2>
            <div className="mt-8 grid gap-6 md:grid-cols-2 md:gap-8">
              <div className="relative flex flex-col rounded-2xl border-2 border-vendoroo-main bg-vendoroo-surface p-8 shadow-md ring-2 ring-vendoroo-main/10">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-vendoroo-main px-4 py-1 text-[10px] font-bold uppercase tracking-widest text-white">
                  Most popular
                </span>
                <h3 className="text-lg font-bold uppercase tracking-wide text-vendoroo-text">
                  Quick diagnostic
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-vendoroo-muted">
                  Survey-based. Estimated benchmarks in under 2 minutes.
                </p>
                <Link
                  href="/diagnostic/quick"
                  className={cn(
                    buttonVariants({
                      className:
                        "mt-auto w-full rounded-full py-6 text-sm font-semibold uppercase tracking-[-0.02em] md:mt-8",
                    })
                  )}
                >
                  Start quick diagnostic
                </Link>
              </div>

              <div className="flex flex-col rounded-2xl border border-vendoroo-border bg-vendoroo-page/50 p-8 shadow-sm">
                <h3 className="text-lg font-bold uppercase tracking-wide text-vendoroo-text">
                  Full diagnostic
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-vendoroo-muted">
                  Upload your PMS data. Data-grounded analysis in under 5
                  minutes.
                </p>
                <Link
                  href="/diagnostic/full"
                  className={cn(
                    buttonVariants({
                      variant: "outline",
                      className:
                        "mt-auto w-full rounded-full border-vendoroo-border py-6 text-sm font-semibold uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-light md:mt-8",
                    })
                  )}
                >
                  Start full diagnostic
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
