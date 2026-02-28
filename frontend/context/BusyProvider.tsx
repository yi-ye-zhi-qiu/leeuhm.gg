"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

interface BusyProps {
  busy: boolean;
  setBusy: (busy: boolean) => void;
}

const BusyContext = createContext<BusyProps | undefined>(undefined);

const BusyProvider: React.FC<{
  children: React.ReactNode;
  showIndicator?: boolean;
}> = ({ children, showIndicator = true }) => {
  const [busy, setBusy] = useState<boolean>(false);
  const pathname = usePathname();

  // Reset busy state on route change
  useEffect(() => {
    setBusy(false);
  }, [pathname]);

  return (
    <BusyContext.Provider value={{ busy, setBusy }}>
      {busy && showIndicator && (
        <div className="fixed top-0 left-0 right-0 h-1 overflow-hidden z-[9999]">
          <div
            className="absolute h-full w-full"
            style={{ animation: "primaryIndeterminateTranslate 2s infinite linear" }}
          >
            <span
              className="bg-gradient-to-r from-accent-foreground/30 to-accent-foreground/60 inline-block h-full absolute w-full"
              style={{ animation: "primaryIndeterminateScale 2s infinite linear" }}
            />
          </div>
          <div
            className="absolute h-full w-full"
            style={{ animation: "auxiliaryIndeterminateTranslate 2s infinite linear" }}
          >
            <span
              className="bg-accent-foreground/50 inline-block w-full h-full absolute"
              style={{ animation: "primaryIndeterminateScale 2s infinite linear" }}
            />
          </div>
        </div>
      )}
      {children}
    </BusyContext.Provider>
  );
};

function useBusy() {
  return useContext(BusyContext);
}

export { BusyProvider, useBusy };
