"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

const LEAD_KEY = "vendoroo_ops_diagnostic_lead";

/**
 * Redirects to lead capture if localStorage has no lead; preserves return path via ?next=
 */
export function RequireLeadGate({
  children,
  returnPath,
}: {
  children: React.ReactNode;
  returnPath: string;
}) {
  const router = useRouter();
  const [ready, setReady] = React.useState(false);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(LEAD_KEY);
      if (!raw) {
        router.replace(
          `/diagnostic?next=${encodeURIComponent(returnPath)}`
        );
        return;
      }
    } catch {
      router.replace(`/diagnostic?next=${encodeURIComponent(returnPath)}`);
      return;
    }
    setReady(true);
  }, [router, returnPath]);

  if (!ready) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center bg-vendoroo-page px-4 text-sm text-vendoroo-muted">
        Loading…
      </div>
    );
  }

  return <>{children}</>;
}
