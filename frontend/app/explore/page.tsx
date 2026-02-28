import { Suspense } from "react";
import { fetchSynapseData } from "@/server/azure-query";
import { getTierCounts, getTotalForTier } from "@/lib/tier-counts";
import { MatchList } from "@/components/match/MatchList";
import { MatchRowSkeleton } from "@/components/match/MatchRowSkeleton";
import { ExploreFilters } from "@/components/explore/ExploreFilters";
import { ExplorePagination } from "@/components/explore/ExplorePagination";

export const dynamic = "force-dynamic";

const TIER_ORDER = [
  "CHALLENGER",
  "GRANDMASTER",
  "MASTER",
  "DIAMOND",
  "EMERALD",
];

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}

function TierCounts() {
  const counts = getTierCounts();
  const tiers = TIER_ORDER.filter((t) => counts[t]);

  if (tiers.length === 0) return null;

  return (
    <div className="mb-8 flex flex-wrap gap-3">
      {tiers.map((tier) => {
        const entries = counts[tier];
        const total = entries.reduce((s, e) => s + e.count, 0);
        return (
          <div
            key={tier}
            className="rounded-lg border bg-card px-4 py-2 text-sm"
          >
            <span className="font-semibold text-foreground">
              {total.toLocaleString()}
            </span>{" "}
            <span className="text-muted-foreground">
              {tier.charAt(0) + tier.slice(1).toLowerCase()}
            </span>
          </div>
        );
      })}
    </div>
  );
}

async function MatchResults({
  rank,
  champion,
  page,
}: {
  rank: string;
  champion: number | undefined;
  page: number;
}) {
  const pageSize = 10;
  const { matches, hasMore } = await fetchSynapseData({
    rank,
    champion,
    page,
    pageSize,
  });

  if (matches.length === 0) {
    return <p className="text-muted-foreground py-8">No matches found.</p>;
  }

  const totalPages = Math.ceil(getTotalForTier(rank) / pageSize);

  return (
    <>
      <MatchList matches={matches} />
      <ExplorePagination
        currentPage={page}
        hasMore={hasMore}
        totalPages={totalPages}
      />
    </>
  );
}

export default async function ExplorePage({ searchParams }: Props) {
  const params = await searchParams;
  const rank = (params.rank as string) || "CHALLENGER";
  const champion = params.champion ? Number(params.champion) : undefined;
  const page = Math.max(1, Number(params.page) || 1);

  return (
    <main className="mx-auto max-w-5xl px-8 py-6 pt-16">
      <h1 className="mb-6 text-2xl font-bold font-heading">Explore Matches</h1>
      <TierCounts />
      <ExploreFilters currentRank={rank} currentChampion={champion} />
      <Suspense fallback={<MatchRowSkeleton />}>
        <MatchResults rank={rank} champion={champion} page={page} />
      </Suspense>
    </main>
  );
}
