import os
import logging
import pandas as pd
import pymssql

SERVER = os.environ.get(
    "SYNAPSE_ENDPOINT", "crawlsynapse-ws-ondemand.sql.azuresynapse.net"
)
DATABASE = "crawldb"
USERNAME = os.environ.get("SYNAPSE_USER", "sqladmin")
PASSWORD = os.environ["SYNAPSE_PASSWORD"]

# Find the lowest-ranked player whose matches were crawled.
# Matches playerInfo (the looked-up player) against allPlayerRanks
# to get their solo queue rank, then sorts lowest ELO first.
QUERY = """
SELECT TOP 1
    JSON_VALUE(doc, '$.data.match.playerInfo.riotUserName') AS riotUserName,
    JSON_VALUE(doc, '$.data.match.playerInfo.riotTagLine') AS riotTagLine,
    rs.tier,
    rs.[rank],
    rs.lp
FROM OPENROWSET(
    BULK 'teemo/0.0.0/na1/*.jsonl.gz',
    DATA_SOURCE = 'CrawlStorage',
    FORMAT = 'CSV',
    FIELDTERMINATOR = '0x0b',
    FIELDQUOTE = '0x0b',
    ROWTERMINATOR = '0x0a'
) WITH (doc NVARCHAR(MAX)) AS r
CROSS APPLY OPENJSON(doc, '$.data.match.allPlayerRanks') WITH (
    riotUserName NVARCHAR(100) '$.riotUserName',
    riotTagLine NVARCHAR(100) '$.riotTagLine',
    rankScores NVARCHAR(MAX) '$.rankScores' AS JSON
) AS player
CROSS APPLY OPENJSON(player.rankScores) WITH (
    tier NVARCHAR(50) '$.tier',
    [rank] NVARCHAR(10) '$.rank',
    lp INT '$.lp',
    queueType NVARCHAR(50) '$.queueType'
) AS rs
WHERE JSON_VALUE(doc, '$.data.match.winningTeam') IS NOT NULL
  AND player.riotUserName = JSON_VALUE(doc, '$.data.match.playerInfo.riotUserName')
  AND player.riotTagLine = JSON_VALUE(doc, '$.data.match.playerInfo.riotTagLine')
  AND rs.queueType = 'ranked_solo_5x5'
ORDER BY
    CASE rs.tier
        WHEN 'IRON' THEN 1
        WHEN 'BRONZE' THEN 2
        WHEN 'SILVER' THEN 3
        WHEN 'GOLD' THEN 4
        WHEN 'PLATINUM' THEN 5
        WHEN 'EMERALD' THEN 6
        WHEN 'DIAMOND' THEN 7
        WHEN 'MASTER' THEN 8
        WHEN 'GRANDMASTER' THEN 9
        WHEN 'CHALLENGER' THEN 10
    END ASC,
    CASE rs.[rank]
        WHEN 'IV' THEN 1
        WHEN 'III' THEN 2
        WHEN 'II' THEN 3
        WHEN 'I' THEN 4
    END ASC,
    rs.lp ASC
"""

LOG_PREFIX = "[Synapse]"


def log(msg, *args):
    logging.info(f"{LOG_PREFIX} {msg}", *args)


def load(query: str = QUERY) -> pd.DataFrame:
    log("Instantiating connection")
    with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
        rows = pd.read_sql(query, conn)
    log("Got %d rows", len(rows))
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = load()
    print(df.to_string(index=False))
