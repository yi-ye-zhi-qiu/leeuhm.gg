"""Template for running ad-hoc queries against Synapse serverless SQL.

Usage:
    SYNAPSE_PASSWORD=... python db/test.py
"""

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
SELECT TOP 10 *
FROM OPENROWSET(
    BULK 'teemo/0.0.0/na1/*.jsonl.gz',
    DATA_SOURCE = 'CrawlStorage',
    FORMAT = 'CSV',
    FIELDTERMINATOR = '0x0b',
    FIELDQUOTE = '0x0b',
    ROWTERMINATOR = '0x0a'
) WITH (doc NVARCHAR(MAX)) AS r
WHERE JSON_VALUE(doc, '$.data.match.winningTeam') IS NOT NULL
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
    print(df.info())
