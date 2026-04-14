import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <section className="relative flex flex-1 flex-col justify-center overflow-hidden bg-vendoroo-page px-4 py-16 sm:px-8 sm:py-24">
        <div className="relative mx-auto max-w-3xl text-center">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-vendoroo-muted">
            Operations assessment
          </p>
          <h1 className="mt-4 text-balance text-3xl font-normal leading-[0.95] tracking-[-0.06em] text-vendoroo-text sm:text-5xl md:text-[3.25rem]">
            Get your free operations diagnostic
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-relaxed text-vendoroo-muted sm:text-lg">
            Benchmark how your team coordinates maintenance—vendors, policies,
            after-hours coverage, and response discipline—against operators
            running portfolios at scale with Vendoroo.
          </p>
          <div className="mt-10">
            <Link
              href="/diagnostic"
              className={cn(
                buttonVariants({
                  size: "lg",
                  className:
                    "h-auto min-w-[220px] rounded-full px-10 py-4 text-sm font-medium uppercase tracking-[-0.02em]",
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
