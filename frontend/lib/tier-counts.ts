// Pre-computed tier counts — avoids expensive blob scan on every page load.
// To refresh, re-run the COUNT query against Synapse and update this map.
export const TIER_COUNTS: Record<string, { rank: string; count: number }[]> = {
  CHALLENGER: [{ rank: "I", count: 841 }],
  GRANDMASTER: [{ rank: "I", count: 390 }],
  MASTER: [{ rank: "I", count: 6580 }],
  DIAMOND: [
    { rank: "I", count: 3236 },
    { rank: "II", count: 5778 },
    { rank: "III", count: 5054 },
    { rank: "IV", count: 1018 },
  ],
  EMERALD: [
    { rank: "I", count: 4100 },
    { rank: "II", count: 10325 },
    { rank: "III", count: 26007 },
    { rank: "IV", count: 43 },
  ],
};

export function getTierCounts() {
  return TIER_COUNTS;
}

export function getTotalForTier(tier: string): number {
  const entries = TIER_COUNTS[tier.toUpperCase()];
  if (!entries) return 0;
  return entries.reduce((sum, e) => sum + e.count, 0);
}
