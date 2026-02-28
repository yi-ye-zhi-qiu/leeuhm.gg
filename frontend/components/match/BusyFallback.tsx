"use client";

import { useEffect } from "react";
import { useBusy } from "@/context/BusyProvider";

export function BusyFallback() {
  const { setBusy } = useBusy();

  useEffect(() => {
    setBusy(true);
    return () => setBusy(false);
  }, [setBusy]);

  return null;
}
