import os
import logging
import pymssql

logging.basicConfig(level=logging.INFO)

SERVER = os.environ.get(
    "SYNAPSE_ENDPOINT", "crawlsynapse-ws-ondemand.sql.azuresynapse.net"
)
DATABASE = "crawldb"
USERNAME = os.environ.get("SYNAPSE_USER", "sqladmin")
PASSWORD = os.environ["SYNAPSE_PASSWORD"]

SETUP_DB_SQL = """
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'crawldb')
    CREATE DATABASE crawldb;
"""

SETUP_SQL = """
IF NOT EXISTS (SELECT * FROM sys.symmetric_keys WHERE name = '##MS_DatabaseMasterKey##')
    CREATE MASTER KEY ENCRYPTION BY PASSWORD = '{password}';

IF NOT EXISTS (SELECT * FROM sys.database_scoped_credentials WHERE name = 'SynapseIdentity')
    CREATE DATABASE SCOPED CREDENTIAL SynapseIdentity WITH IDENTITY = 'Managed Identity';

IF NOT EXISTS (SELECT * FROM sys.external_data_sources WHERE name = 'CrawlStorage')
    CREATE EXTERNAL DATA SOURCE CrawlStorage
    WITH (
        LOCATION = 'https://crawlstorageacc.blob.core.windows.net/crawlstorage',
        CREDENTIAL = SynapseIdentity
    );
"""

LOG_PREFIX = "[Synapse Setup]"


def log(msg):
    logging.info(f"{LOG_PREFIX} {msg}")


def setup():
    log("Creating database if not exists")
    with pymssql.connect(SERVER, USERNAME, PASSWORD, "master") as conn:
        conn.autocommit(True)
        cursor = conn.cursor()
        cursor.execute(SETUP_DB_SQL)
    log("Database ready")

    log("Creating master key, credential, and data source if not exists")
    with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
        cursor = conn.cursor()
        for stmt in SETUP_SQL.format(password=PASSWORD).strip().split("\n\n"):
            cursor.execute(stmt)
        conn.commit()
    log("Setup complete")


if __name__ == "__main__":
    setup()
