import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <section className="relative flex flex-1 flex-col justify-center overflow-hidden px-4 py-20 sm:px-8 sm:py-28">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(99,102,241,0.14),_transparent_55%)]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-3xl text-center">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-[#6366F1]">
            Vendoroo · vendoroo.ai
          </p>
          <h1 className="mt-4 text-balance text-3xl font-semibold tracking-tight text-white sm:text-4xl md:text-5xl">
            Get Your Free Operations Diagnostic
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-relaxed text-slate-300 sm:text-lg">
            Vendoroo helps property operators coordinate maintenance with
            discipline—clear vendors, accountable spend, and predictable
            response when residents need help. This diagnostic benchmarks your
            current operating model against teams running portfolios at scale.
          </p>
          <div className="mt-10">
            <Link
              href="/diagnostic"
              className={cn(
                buttonVariants({
                  size: "lg",
                  className:
                    "h-12 min-w-[200px] bg-[#6366F1] px-8 text-base text-white hover:bg-[#4F46E5]",
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
