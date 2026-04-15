import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ArrowRight,
  BarChart3,
  ClipboardCheck,
  Gauge,
  Sparkles,
} from "lucide-react";

const stats = [
  {
    line1: "5",
    line2: "",
    showFraction: false,
    label: "Structured steps",
    hint: "Coverage, policies, ops, goals",
  },
  {
    line1: "2",
    line2: "",
    showFraction: false,
    label: "Assessment paths",
    hint: "Quick survey or full upload",
  },
  {
    line1: "100",
    line2: "/100",
    showFraction: true,
    label: "Point ops score",
    hint: "Tiered benchmark vs best practice",
  },
] as const;

const pillars = [
  {
    icon: ClipboardCheck,
    title: "Vendor & coverage",
    body: "How deep your bench is across trades, and how consistently work gets triaged.",
  },
  {
    icon: Gauge,
    title: "Policies & response",
    body: "Written protocols, NTEs, SLAs, and real-world first-response behavior.",
  },
  {
    icon: BarChart3,
    title: "Clear next steps",
    body: "A scored readout with gaps, findings, and a path to a deeper data review.",
  },
] as const;

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      {/* Hero */}
      <section className="relative isolate overflow-hidden bg-vendoroo-surface">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-40%,rgba(3,156,172,0.16),transparent_55%)]"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -right-24 -top-24 size-[min(100vw,28rem)] rounded-full bg-[radial-gradient(circle_at_center,rgba(179,225,230,0.55),transparent_68%)] blur-2xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-32 -left-16 size-[min(90vw,24rem)] rounded-full bg-[radial-gradient(circle_at_center,rgba(1,104,250,0.08),transparent_70%)] blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.35] [background-image:linear-gradient(to_right,#e1e3e4_1px,transparent_1px),linear-gradient(to_bottom,#e1e3e4_1px,transparent_1px)] [background-size:32px_32px] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_40%,#000_45%,transparent_100%)]"
          aria-hidden
        />

        <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pb-28 sm:pt-24">
          <div className="mx-auto max-w-4xl text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-vendoroo-border bg-vendoroo-surface/80 px-4 py-1.5 text-xs font-medium uppercase tracking-[0.18em] text-vendoroo-main-dark shadow-sm backdrop-blur-sm">
              <Sparkles className="size-3.5 text-vendoroo-main" aria-hidden />
              Vendoroo · Operations lab
            </div>
            <h1 className="mt-6 text-balance font-normal leading-[0.98] tracking-[-0.055em] text-vendoroo-text sm:mt-8">
              <span className="block text-4xl sm:text-6xl md:text-[3.5rem]">
                Know where your maintenance desk{" "}
                <span className="relative inline-block whitespace-nowrap">
                  <span className="relative z-10">stands today</span>
                  <span
                    className="absolute -bottom-1 left-0 right-0 -z-0 h-3 rounded-sm bg-gradient-to-r from-vendoroo-tint via-vendoroo-tint/50 to-transparent sm:h-3.5"
                    aria-hidden
                  />
                </span>
              </span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-pretty text-lg leading-relaxed text-vendoroo-muted sm:text-xl">
              A free, clinical assessment of vendors, policies, after-hours
              coverage, and response discipline—benchmarked the way Vendoroo
              runs maintenance at scale.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row sm:gap-5">
              <Link
                href="/diagnostic"
                className={cn(
                  buttonVariants({
                    size: "lg",
                    className:
                      "h-14 min-w-[240px] rounded-full px-10 text-sm font-semibold uppercase tracking-[-0.02em] shadow-lg shadow-vendoroo-text/10 transition-shadow hover:shadow-xl hover:shadow-vendoroo-main/15",
                  })
                )}
              >
                Start free diagnostic
              </Link>
              <a
                href="https://vendoroo.ai/demo"
                target="_blank"
                rel="noopener noreferrer"
                className="group inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-vendoroo-main-dark transition-colors hover:text-vendoroo-main"
              >
                Book a live demo
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </a>
            </div>
          </div>

          {/* Stats */}
          <div className="mx-auto mt-16 grid max-w-4xl gap-4 sm:mt-20 sm:grid-cols-3 sm:gap-6">
            {stats.map((s) => (
              <div
                key={s.label}
                className="rounded-2xl border border-vendoroo-border bg-vendoroo-surface/90 px-6 py-5 text-center shadow-sm backdrop-blur-sm transition-shadow hover:shadow-md"
              >
                <p className="text-4xl font-semibold tabular-nums tracking-tight text-vendoroo-text sm:text-5xl">
                  <span className="font-mono">{s.line1}</span>
                  {s.showFraction ? (
                    <span className="text-2xl font-normal text-vendoroo-muted sm:text-3xl">
                      {s.line2}
                    </span>
                  ) : null}
                </p>
                <p className="mt-2 text-sm font-semibold uppercase tracking-wide text-vendoroo-smoke">
                  {s.label}
                </p>
                <p className="mt-1 text-xs leading-snug text-vendoroo-muted">
                  {s.hint}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What we measure */}
      <section className="border-t border-vendoroo-border bg-vendoroo-light/80 py-16 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-vendoroo-main">
              Inside the diagnostic
            </p>
            <h2 className="mt-3 text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl md:text-4xl">
              Built like a clinical workup—not a generic survey
            </h2>
            <p className="mt-4 text-base leading-relaxed text-vendoroo-muted sm:text-lg">
              Short questions, precise scoring, and language your ops team
              already uses. Results map to how Vendoroo coordinates maintenance
              in the field.
            </p>
          </div>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {pillars.map(({ icon: Icon, title, body }) => (
              <div
                key={title}
                className="group relative overflow-hidden rounded-2xl border border-vendoroo-border bg-vendoroo-surface p-8 shadow-sm transition-all hover:-translate-y-0.5 hover:border-vendoroo-main/25 hover:shadow-lg"
              >
                <div className="mb-5 inline-flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-vendoroo-tint/90 to-vendoroo-tint/30 text-vendoroo-main-dark ring-1 ring-vendoroo-main/10">
                  <Icon className="size-6" strokeWidth={1.75} aria-hidden />
                </div>
                <h3 className="text-lg font-semibold tracking-tight text-vendoroo-text">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-vendoroo-muted">
                  {body}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-14 flex flex-col items-center justify-center gap-4 rounded-2xl border border-vendoroo-border bg-gradient-to-br from-vendoroo-surface via-vendoroo-surface to-vendoroo-tint/30 px-6 py-10 text-center sm:px-12">
            <p className="max-w-xl text-base font-medium leading-relaxed text-vendoroo-smoke">
              Ready when you are—on a phone at an event or at your desk. No
              prep required for the quick path.
            </p>
            <Link
              href="/diagnostic"
              className={cn(
                buttonVariants({
                  size: "lg",
                  className:
                    "h-12 rounded-full px-10 text-sm font-semibold uppercase tracking-[-0.02em]",
                })
              )}
            >
              Begin diagnostic
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
