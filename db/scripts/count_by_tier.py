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

QUERY = """
SELECT
    rs.tier,
    rs.[rank],
    COUNT(*) AS game_count
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
    queueType NVARCHAR(50) '$.queueType'
) AS rs
WHERE JSON_VALUE(doc, '$.data.match.winningTeam') IS NOT NULL
  AND player.riotUserName = JSON_VALUE(doc, '$.data.match.playerInfo.riotUserName')
  AND player.riotTagLine = JSON_VALUE(doc, '$.data.match.playerInfo.riotTagLine')
  AND rs.queueType = 'ranked_solo_5x5'
GROUP BY rs.tier, rs.[rank]
ORDER BY
    CASE rs.tier
        WHEN 'CHALLENGER' THEN 1
        WHEN 'GRANDMASTER' THEN 2
        WHEN 'MASTER' THEN 3
        WHEN 'DIAMOND' THEN 4
        WHEN 'EMERALD' THEN 5
        WHEN 'PLATINUM' THEN 6
        WHEN 'GOLD' THEN 7
        WHEN 'SILVER' THEN 8
        WHEN 'BRONZE' THEN 9
        WHEN 'IRON' THEN 10
    END ASC,
    CASE rs.[rank]
        WHEN 'I' THEN 1
        WHEN 'II' THEN 2
        WHEN 'III' THEN 3
        WHEN 'IV' THEN 4
    END ASC
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
