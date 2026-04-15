"use client";

import { useSearchParams } from "next/navigation";
import * as React from "react";

const REF_KEY = "vendoroo_diagnostic_ref";

/**
 * Persists ?ref= for analytics (e.g. QR campaigns). Page content unchanged.
 */
export function LandingRefTracker() {
  const searchParams = useSearchParams();

  React.useEffect(() => {
    const ref = searchParams.get("ref");
    if (ref && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(REF_KEY, ref);
    }
  }, [searchParams]);

  return null;
}
