import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Clock, Upload } from "lucide-react";

export function PathSelector() {
  return (
    <div className="mx-auto grid w-full max-w-3xl gap-6 sm:grid-cols-2">
      <Card className="border-vendoroo-border bg-vendoroo-surface shadow-sm ring-0">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-vendoroo-tint/80 text-vendoroo-main-dark">
            <Clock className="size-5" aria-hidden />
          </div>
          <CardTitle className="text-vendoroo-text">Quick Diagnostic</CardTitle>
          <CardDescription className="text-vendoroo-muted">
            About two minutes. Structured survey to benchmark how your team
            coordinates vendors, policies, and after-hours coverage.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link
            href="/diagnostic/quick"
            className={cn(
              buttonVariants({
                className:
                  "h-12 w-full rounded-full text-sm font-medium uppercase tracking-[-0.02em]",
              })
            )}
          >
            Start quick diagnostic
          </Link>
        </CardContent>
      </Card>
      <Card className="border-vendoroo-border bg-vendoroo-surface shadow-sm ring-0">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-vendoroo-tint/80 text-vendoroo-main-dark">
            <Upload className="size-5" aria-hidden />
          </div>
          <CardTitle className="text-vendoroo-text">Full Diagnostic</CardTitle>
          <CardDescription className="text-vendoroo-muted">
            Upload work orders, vendor lists, or runbooks so we can ground the
            assessment in your real operational data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link
            href="/diagnostic/full"
            className={cn(
              buttonVariants({
                variant: "outline",
                className:
                  "h-12 w-full rounded-full border-vendoroo-border text-sm font-medium uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-light",
              })
            )}
          >
            Start full diagnostic
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
