import os
import json
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
SELECT TOP 10000 *
FROM OPENROWSET(
    BULK 'teemo/0.0.0/na1/*.jsonl.gz',
    DATA_SOURCE = 'CrawlStorage',
    FORMAT = 'CSV',
    FIELDTERMINATOR = '0x0b',
    FIELDQUOTE = '0x0b',
    ROWTERMINATOR = '0x0a'
) WITH (doc NVARCHAR(MAX)) AS r
"""

LOG_PREFIX = "[Synapse]"


def log(msg, *args):
    logging.info(f"{LOG_PREFIX} {msg}", *args)


def load(query: str = QUERY) -> pd.DataFrame:
    log("Instantiating connection")
    with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
        rows = pd.read_sql(query, conn)
    return pd.json_normalize(rows["doc"].apply(json.loads))


if __name__ == "__main__":
    df = load()
    print(df.info())
    print(df.head())
    breakpoint()
