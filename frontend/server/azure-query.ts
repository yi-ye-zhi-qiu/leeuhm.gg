"use server";

import sql from "mssql";
import type { MatchData } from "@/types/match";
import { computeShapValues } from "@/lib/shap";

const config: sql.config = {
  user: process.env.SYNAPSE_USER,
  password: process.env.SYNAPSE_PASSWORD,
  server: process.env.SYNAPSE_ENDPOINT!,
  database: "crawldb",
  options: {
    encrypt: true,
    enableArithAbort: true,
  },
  pool: {
    max: 10,
    min: 0,
    idleTimeoutMillis: 30000,
  },
};

let pool: sql.ConnectionPool | null = null;

async function getPool() {
  if (!pool) {
    pool = await sql.connect(config);
  }
  return pool;
}

export interface FetchOptions {
  rank?: string;
  champion?: number;
  page?: number;
  pageSize?: number;
}

// Fetch pageSize+1 rows using TOP to avoid expensive ORDER BY + OFFSET/FETCH
// and COUNT(*) OVER() scans. The +1 tells us if a next page exists.
function buildQuery(opts: FetchOptions) {
  const { rank, champion, page = 1, pageSize = 10 } = opts;
  // We fetch enough rows to skip past previous pages + 1 extra to detect hasMore
  const fetchCount = page * pageSize + 1;

  const conditions: string[] = [
    "JSON_VALUE(doc, '$.data.match.winningTeam') IS NOT NULL",
  ];
  const needsRankJoin = !!rank;

  if (champion) {
    conditions.push(
      `JSON_VALUE(doc, '$.data.match.matchSummary.championId') = '${champion}'`
    );
  }

  let rankJoin = "";
  if (needsRankJoin) {
    rankJoin = `
CROSS APPLY OPENJSON(doc, '$.data.match.allPlayerRanks') WITH (
    riotUserName NVARCHAR(100) '$.riotUserName',
    riotTagLine NVARCHAR(100) '$.riotTagLine',
    rankScores NVARCHAR(MAX) '$.rankScores' AS JSON
) AS player
CROSS APPLY OPENJSON(player.rankScores) WITH (
    tier NVARCHAR(50) '$.tier',
    queueType NVARCHAR(50) '$.queueType'
) AS rs`;
    conditions.push(
      "player.riotUserName = JSON_VALUE(doc, '$.data.match.playerInfo.riotUserName')",
      "player.riotTagLine = JSON_VALUE(doc, '$.data.match.playerInfo.riotTagLine')",
      "rs.queueType = 'ranked_solo_5x5'",
      `rs.tier = '${rank}'`
    );
  }

  return `
SELECT TOP ${fetchCount} doc
FROM OPENROWSET(
    BULK 'teemo/0.0.0/na1/*.jsonl.gz',
    DATA_SOURCE = 'CrawlStorage',
    FORMAT = 'CSV',
    FIELDTERMINATOR = '0x0b',
    FIELDQUOTE = '0x0b',
    ROWTERMINATOR = '0x0a'
) WITH (doc NVARCHAR(MAX)) AS r
${rankJoin}
WHERE ${conditions.join("\n  AND ")}
`;
}

// Strip metricsData, timelineData, and frame arrays before
// sending to the client — they make up ~95% of each document
// but no component uses them.
function slim(raw: any): MatchData {
  const m = raw.data.match;
  return {
    match: {
      matchSummary: m.matchSummary,
      historicalData: {
        matchId: m.historicalData.matchId,
        postGameData: m.historicalData.postGameData,
        teamOneOverview: m.historicalData.teamOneOverview,
        teamTwoOverview: m.historicalData.teamTwoOverview,
      },
      allPlayerRanks: m.allPlayerRanks,
      playerInfo: m.playerInfo,
      winningTeam: m.winningTeam,
    },
  };
}

// -- Commented out: expensive blob-scan queries --
// export async function fetchTierCounts() { ... }
// export async function fetchTotalCount() { ... }

export async function fetchSynapseData(
  opts: FetchOptions = {}
): Promise<{ matches: MatchData[]; hasMore: boolean }> {
  const { page = 1, pageSize = 10 } = opts;
  const db = await getPool();
  const query = buildQuery(opts);
  const result = await db.query(query);

  if (result.recordset.length === 0) {
    return { matches: [], hasMore: false };
  }

  const allRows = result.recordset.map((row: { doc: string }) => {
    const raw = JSON.parse(row.doc);
    const regionId = raw.data?.match?.matchSummary?.regionId;
    const slimmed = slim(raw);
    if (regionId) {
      slimmed.shapValues = computeShapValues(raw, regionId) ?? undefined;
    }
    return slimmed;
  });

  // Sort client-side by matchCreationTime descending
  allRows.sort(
    (a, b) =>
      b.match.matchSummary.matchCreationTime -
      a.match.matchSummary.matchCreationTime
  );

  // Slice to current page
  const start = (page - 1) * pageSize;
  const pageRows = allRows.slice(start, start + pageSize);
  const hasMore = allRows.length > page * pageSize;

  return { matches: pageRows, hasMore };
}
