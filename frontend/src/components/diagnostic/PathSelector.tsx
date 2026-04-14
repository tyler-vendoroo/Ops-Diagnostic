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
      <Card className="border-white/10 bg-[#0B1220] ring-white/10">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-[#6366F1]/15 text-[#6366F1]">
            <Clock className="size-5" aria-hidden />
          </div>
          <CardTitle className="text-slate-100">Quick Diagnostic</CardTitle>
          <CardDescription className="text-slate-400">
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
                  "h-11 w-full bg-[#6366F1] text-white hover:bg-[#4F46E5]",
              })
            )}
          >
            Start quick diagnostic
          </Link>
        </CardContent>
      </Card>
      <Card className="border-white/10 bg-[#0B1220] ring-white/10">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-lg bg-[#6366F1]/15 text-[#6366F1]">
            <Upload className="size-5" aria-hidden />
          </div>
          <CardTitle className="text-slate-100">Full Diagnostic</CardTitle>
          <CardDescription className="text-slate-400">
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
                  "h-11 w-full border-white/20 bg-transparent text-slate-100 hover:bg-white/5",
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
