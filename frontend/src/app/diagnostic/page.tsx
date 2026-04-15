import { Suspense } from "react";

import { DiagnosticPageClient } from "./diagnostic-page-client";

export default function DiagnosticPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[50vh] flex-1 bg-vendoroo-page px-4 py-24 text-center text-sm text-vendoroo-muted">
          Loading…
        </div>
      }
    >
      <DiagnosticPageClient />
    </Suspense>
  );
}
