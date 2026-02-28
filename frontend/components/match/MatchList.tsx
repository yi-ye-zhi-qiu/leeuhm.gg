"use client";

import { Suspense, useState, lazy } from "react";
import type { MatchData } from "@/types/match";
import { BusyFallback } from "./BusyFallback";
import { MatchRow } from "./MatchRow";

const MatchDetail = lazy(() =>
  import("./MatchDetail").then((m) => ({ default: m.MatchDetail })),
);

export function MatchList({ matches }: { matches: MatchData[] }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  return (
    <div className="flex flex-col gap-2">
      {matches.map((match) => {
        const id = match.match.matchSummary.matchId;
        const isExpanded = expandedId === id;
        return (
          <div key={id}>
            <div
              onClick={() => setExpandedId(isExpanded ? null : id)}
              className="cursor-pointer"
            >
              <MatchRow data={match} />
            </div>
            {isExpanded && (
              <Suspense fallback={<BusyFallback />}>
                <MatchDetail data={match} />
              </Suspense>
            )}
          </div>
        );
      })}
    </div>
  );
}
