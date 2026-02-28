import { Suspense } from "react";
import { fetchSynapseData } from "@/server/azure-query";
import { MatchList } from "@/components/match/MatchList";
import { MatchRowSkeleton } from "@/components/match/MatchRowSkeleton";
import { ExploreFilters } from "@/components/explore/ExploreFilters";
import { ExplorePagination } from "@/components/explore/ExplorePagination";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
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
  const { matches, hasMore } = await fetchSynapseData({
    rank,
    champion,
    page,
    pageSize: 10,
  });

  if (matches.length === 0) {
    return <p className="text-muted-foreground py-8">No matches found.</p>;
  }

  return (
    <>
      <MatchList matches={matches} />
      <ExplorePagination currentPage={page} hasMore={hasMore} />
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
      <ExploreFilters currentRank={rank} currentChampion={champion} />
      <Suspense fallback={<MatchRowSkeleton />}>
        <MatchResults rank={rank} champion={champion} page={page} />
      </Suspense>
    </main>
  );
}
