"""SQL-first feature extraction from Synapse for XGBoost training.

Extracts ~80 raw/derived columns per player per match via CROSS APPLY + OUTER APPLY:
  - Player stats from postGameData (10 rows per match)
  - Rank tier + LP from allPlayerRanks
  - Performance scores (hardCarry, teamplay, damageShare, etc.)
  - Timeline phase aggregates (kills, deaths, wards per early/mid/late)
  - Dragon features from timeline (total, elder, per-type counts)
  - Teamfight counts per phase (15s windows with 2+ kills)
  - Diff frame phase averages (CS/gold/KA/XP, primary player only)
  - Team objectives (baron, dragon, tower, inhibitor, riftHerald)
  - Items (item0-item6), summoner spells (spell0, spell1), runes (keystone, subStyle)
  - Team compositions as JSON (for champion interaction encoding in Python)

Game phase boundaries (timeline timestamps in ms):
  Early:  timestamp < matchDurationSec * 250       (first 25%)
  Mid:    timestamp >= matchDurationSec * 250
          AND      < matchDurationSec * 500         (25%-50%)
  Late:   timestamp >= matchDurationSec * 500       (last 50%)

Diff frame timestamps are minute indices, so thresholds are:
  Early:  ts < matchDurationSec / 60.0 * 0.25
  Mid:    ts >= matchDurationSec / 60.0 * 0.25  AND  < matchDurationSec / 60.0 * 0.5
  Late:   ts >= matchDurationSec / 60.0 * 0.5

Teamfight definition: GROUP BY FLOOR(timestamp / 15000) HAVING COUNT(*) >= 2

Usage:
    SYNAPSE_PASSWORD=... python db/scripts/features.py [--region na1]
"""

import os
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

SERVER = os.environ.get(
    "SYNAPSE_ENDPOINT", "crawlsynapse-ws-ondemand.sql.azuresynapse.net"
)
DATABASE = "crawldb"
USERNAME = os.environ.get("SYNAPSE_USER", "sqladmin")
PASSWORD = os.environ.get("SYNAPSE_PASSWORD", "")


def build_query(region: str) -> str:
    """Build the comprehensive feature extraction SQL query for a region."""
    return f"""
    SELECT
        -- === Match identifiers ===
        m.matchId,
        m.matchDurationSec,
        m.winningTeam,
        m.matchCreationTime,
        m.primaryUserName,
        m.primaryTagLine,

        -- === Player stats ===
        p.riotUserName,
        p.riotTagLine,
        p.championId,
        p.teamId,
        p.role,
        p.kills,
        p.deaths,
        p.assists,
        p.cs,
        p.jungleCs,
        p.damage,
        p.damageTaken,
        p.gold,
        p.level,
        p.wardsPlaced,
        p.carryPercentage,
        p.item0, p.item1, p.item2, p.item3, p.item4, p.item5, p.item6,
        p.spell0, p.spell1,
        p.keystone, p.subStyle,

        -- === Rank ===
        rk.tier AS rank_tier,
        rk.lp AS rank_lp,

        -- === Performance scores ===
        ps.hardCarry,
        ps.teamplay,
        ps.damageShareTotal,
        ps.goldShareTotal,
        ps.killParticipationTotal,
        ps.visionScoreTotal,
        ps.finalLvlDiffTotal,

        -- === Team objectives (player's own team) ===
        CASE WHEN p.teamId = 100
            THEN CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamOneOverview.baronKills') AS INT)
            ELSE CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamTwoOverview.baronKills') AS INT)
        END AS baron_kills,
        CASE WHEN p.teamId = 100
            THEN CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamOneOverview.dragonKills') AS INT)
            ELSE CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamTwoOverview.dragonKills') AS INT)
        END AS dragon_kills,
        CASE WHEN p.teamId = 100
            THEN CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamOneOverview.towerKills') AS INT)
            ELSE CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamTwoOverview.towerKills') AS INT)
        END AS tower_kills,
        CASE WHEN p.teamId = 100
            THEN CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamOneOverview.inhibitorKills') AS INT)
            ELSE CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamTwoOverview.inhibitorKills') AS INT)
        END AS inhibitor_kills,
        CASE WHEN p.teamId = 100
            THEN CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamOneOverview.riftHeraldKills') AS INT)
            ELSE CAST(JSON_VALUE(doc, '$.data.match.historicalData.teamTwoOverview.riftHeraldKills') AS INT)
        END AS rift_herald_kills,

        -- === Timeline per-player phase aggregates ===
        tl.early_kills, tl.mid_kills, tl.late_kills,
        tl.early_deaths, tl.mid_deaths, tl.late_deaths,
        tl.early_wards, tl.mid_wards, tl.late_wards,

        -- === Dragon features (match-level) ===
        dr.total_dragons, dr.elder_count,
        dr.infernal, dr.mountain, dr.ocean,
        dr.hextech, dr.chemtech, dr.cloud,

        -- === Teamfights per phase (match-level) ===
        tf.early_teamfights, tf.mid_teamfights, tf.late_teamfights,

        -- === Diff frame phase averages (primary player only, 0 for others) ===
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN csd.cs_diff_early ELSE 0 END AS cs_diff_early,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN csd.cs_diff_mid ELSE 0 END AS cs_diff_mid,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN csd.cs_diff_late ELSE 0 END AS cs_diff_late,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN gdd.gold_diff_early ELSE 0 END AS gold_diff_early,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN gdd.gold_diff_mid ELSE 0 END AS gold_diff_mid,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN gdd.gold_diff_late ELSE 0 END AS gold_diff_late,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN kad.ka_diff_early ELSE 0 END AS ka_diff_early,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN kad.ka_diff_mid ELSE 0 END AS ka_diff_mid,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN kad.ka_diff_late ELSE 0 END AS ka_diff_late,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN xpd.xp_diff_early ELSE 0 END AS xp_diff_early,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN xpd.xp_diff_mid ELSE 0 END AS xp_diff_mid,
        CASE WHEN p.riotUserName = m.primaryUserName
              AND p.riotTagLine  = m.primaryTagLine
             THEN xpd.xp_diff_late ELSE 0 END AS xp_diff_late,

        -- === Team compositions (for champion interaction encoding in Python) ===
        JSON_QUERY(doc, '$.data.match.matchSummary.teamA') AS teamA_json,
        JSON_QUERY(doc, '$.data.match.matchSummary.teamB') AS teamB_json

    FROM OPENROWSET(
        BULK 'teemo/0.0.0/{region}/*.jsonl.gz',
        DATA_SOURCE = 'CrawlStorage',
        FORMAT = 'CSV',
        FIELDTERMINATOR = '0x0b',
        FIELDQUOTE = '0x0b',
        ROWTERMINATOR = '0x0a'
    ) WITH (doc NVARCHAR(MAX)) AS r

    ---------------------------------------------------------------------------
    -- Match-level scalars (avoids repeated JSON_VALUE calls)
    ---------------------------------------------------------------------------
    CROSS APPLY (
        SELECT
            JSON_VALUE(doc, '$.data.match.historicalData.matchId') AS matchId,
            CAST(JSON_VALUE(doc, '$.data.match.matchSummary.matchDuration') AS FLOAT) AS matchDurationSec,
            CAST(JSON_VALUE(doc, '$.data.match.winningTeam') AS INT) AS winningTeam,
            CAST(JSON_VALUE(doc, '$.data.match.matchSummary.matchCreationTime') AS BIGINT) AS matchCreationTime,
            JSON_VALUE(doc, '$.data.match.playerInfo.riotUserName') AS primaryUserName,
            JSON_VALUE(doc, '$.data.match.playerInfo.riotTagLine') AS primaryTagLine
    ) AS m

    ---------------------------------------------------------------------------
    -- 10 player rows from postGameData
    ---------------------------------------------------------------------------
    CROSS APPLY OPENJSON(doc, '$.data.match.historicalData.postGameData') WITH (
        riotUserName    NVARCHAR(100) '$.riotUserName',
        riotTagLine     NVARCHAR(100) '$.riotTagLine',
        championId      INT           '$.championId',
        teamId          INT           '$.teamId',
        role            INT           '$.role',
        kills           INT           '$.kills',
        deaths          INT           '$.deaths',
        assists         INT           '$.assists',
        cs              INT           '$.cs',
        jungleCs        INT           '$.jungleCs',
        damage          INT           '$.damage',
        damageTaken     INT           '$.damageTaken',
        gold            INT           '$.gold',
        level           INT           '$.level',
        wardsPlaced     INT           '$.wardsPlaced',
        carryPercentage FLOAT         '$.carryPercentage',
        item0           INT           '$.items[0]',
        item1           INT           '$.items[1]',
        item2           INT           '$.items[2]',
        item3           INT           '$.items[3]',
        item4           INT           '$.items[4]',
        item5           INT           '$.items[5]',
        item6           INT           '$.items[6]',
        spell0          INT           '$.summonerSpells[0]',
        spell1          INT           '$.summonerSpells[1]',
        keystone        INT           '$.keystone',
        subStyle        INT           '$.subStyle'
    ) AS p

    ---------------------------------------------------------------------------
    -- Rank (solo queue preferred) for this player
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT TOP 1 rs.tier, rs.lp
        FROM OPENJSON(doc, '$.data.match.allPlayerRanks') WITH (
            riotUserName NVARCHAR(100)  '$.riotUserName',
            riotTagLine  NVARCHAR(100)  '$.riotTagLine',
            rankScores   NVARCHAR(MAX)  '$.rankScores' AS JSON
        ) AS pr
        CROSS APPLY OPENJSON(pr.rankScores) WITH (
            tier      NVARCHAR(50)  '$.tier',
            lp        INT           '$.lp',
            queueType NVARCHAR(50)  '$.queueType'
        ) AS rs
        WHERE pr.riotUserName = p.riotUserName
          AND pr.riotTagLine  = p.riotTagLine
          AND rs.queueType    = 'ranked_solo_5x5'
    ) AS rk

    ---------------------------------------------------------------------------
    -- Performance score for this player
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT TOP 1
            ps_i.hardCarry,
            ps_i.teamplay,
            ps_i.damageShareTotal,
            ps_i.goldShareTotal,
            ps_i.killParticipationTotal,
            ps_i.visionScoreTotal,
            ps_i.finalLvlDiffTotal
        FROM OPENJSON(doc, '$.data.match.performanceScore') WITH (
            riotUserName          NVARCHAR(100) '$.riotUserName',
            riotTagLine           NVARCHAR(100) '$.riotTagLine',
            hardCarry             FLOAT         '$.hardCarry',
            teamplay              FLOAT         '$.teamplay',
            damageShareTotal      FLOAT         '$.damageShareTotal',
            goldShareTotal        FLOAT         '$.goldShareTotal',
            killParticipationTotal FLOAT        '$.killParticipationTotal',
            visionScoreTotal      FLOAT         '$.visionScoreTotal',
            finalLvlDiffTotal     FLOAT         '$.finalLvlDiffTotal'
        ) AS ps_i
        WHERE ps_i.riotUserName = p.riotUserName
          AND ps_i.riotTagLine  = p.riotTagLine
    ) AS ps

    ---------------------------------------------------------------------------
    -- Per-player kills, deaths, wards by game phase
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts < m.matchDurationSec * 250
                 THEN 1 ELSE 0 END) AS early_kills,
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 250 AND e.ts < m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS mid_kills,
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS late_kills,
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.victim_name = p.riotUserName AND e.victim_tag = p.riotTagLine
                      AND e.ts < m.matchDurationSec * 250
                 THEN 1 ELSE 0 END) AS early_deaths,
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.victim_name = p.riotUserName AND e.victim_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 250 AND e.ts < m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS mid_deaths,
            SUM(CASE WHEN e.eventType = 'champion_kill'
                      AND e.victim_name = p.riotUserName AND e.victim_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS late_deaths,
            SUM(CASE WHEN e.eventType = 'ward_placed'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts < m.matchDurationSec * 250
                 THEN 1 ELSE 0 END) AS early_wards,
            SUM(CASE WHEN e.eventType = 'ward_placed'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 250 AND e.ts < m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS mid_wards,
            SUM(CASE WHEN e.eventType = 'ward_placed'
                      AND e.killer_name = p.riotUserName AND e.killer_tag = p.riotTagLine
                      AND e.ts >= m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS late_wards
        FROM OPENJSON(doc, '$.data.match.historicalData.timelineData') WITH (
            eventType   NVARCHAR(50)  '$.eventType',
            ts          BIGINT        '$.timestamp',
            killer_name NVARCHAR(100) '$.riotUserName',
            killer_tag  NVARCHAR(100) '$.riotTagLine',
            victim_name NVARCHAR(100) '$.victimRiotUserName',
            victim_tag  NVARCHAR(100) '$.victimRiotTagLine'
        ) AS e
        WHERE e.eventType IN ('champion_kill', 'ward_placed')
    ) AS tl

    ---------------------------------------------------------------------------
    -- Dragon features (match-level)
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            COUNT(*)
                AS total_dragons,
            SUM(CASE WHEN d.monsterSubtype = 'elder_dragon'    THEN 1 ELSE 0 END) AS elder_count,
            SUM(CASE WHEN d.monsterSubtype = 'infernal_dragon' THEN 1 ELSE 0 END) AS infernal,
            SUM(CASE WHEN d.monsterSubtype = 'mountain_dragon' THEN 1 ELSE 0 END) AS mountain,
            SUM(CASE WHEN d.monsterSubtype = 'ocean_dragon'    THEN 1 ELSE 0 END) AS ocean,
            SUM(CASE WHEN d.monsterSubtype = 'hextech_dragon'  THEN 1 ELSE 0 END) AS hextech,
            SUM(CASE WHEN d.monsterSubtype = 'chemtech_dragon' THEN 1 ELSE 0 END) AS chemtech,
            SUM(CASE WHEN d.monsterSubtype = 'cloud_dragon'    THEN 1 ELSE 0 END) AS cloud
        FROM OPENJSON(doc, '$.data.match.historicalData.timelineData') WITH (
            monsterType    NVARCHAR(50) '$.monsterType',
            monsterSubtype NVARCHAR(50) '$.monsterSubtype'
        ) AS d
        WHERE d.monsterType = 'dragon'
    ) AS dr

    ---------------------------------------------------------------------------
    -- Teamfight buckets per phase (15s windows with >= 2 kills)
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            SUM(CASE WHEN b.bucket_ts < m.matchDurationSec * 250
                 THEN 1 ELSE 0 END) AS early_teamfights,
            SUM(CASE WHEN b.bucket_ts >= m.matchDurationSec * 250
                      AND b.bucket_ts <  m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS mid_teamfights,
            SUM(CASE WHEN b.bucket_ts >= m.matchDurationSec * 500
                 THEN 1 ELSE 0 END) AS late_teamfights
        FROM (
            SELECT
                FLOOR(t.ts / 15000) * 15000 AS bucket_ts,
                COUNT(*) AS kill_count
            FROM OPENJSON(doc, '$.data.match.historicalData.timelineData') WITH (
                eventType NVARCHAR(50) '$.eventType',
                ts        BIGINT       '$.timestamp'
            ) AS t
            WHERE t.eventType = 'champion_kill'
            GROUP BY FLOOR(t.ts / 15000)
            HAVING COUNT(*) >= 2
        ) AS b
    ) AS tf

    ---------------------------------------------------------------------------
    -- CS diff frame phase averages
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            AVG(CASE WHEN f.ts < m.matchDurationSec / 60.0 * 0.25
                     THEN f.youValue - f.oppValue END) AS cs_diff_early,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.25
                      AND f.ts <  m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS cs_diff_mid,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS cs_diff_late
        FROM OPENJSON(doc, '$.data.match.historicalData.csDifferenceFrames') WITH (
            ts       INT   '$.timestamp',
            youValue FLOAT '$.youValue',
            oppValue FLOAT '$.oppValue'
        ) AS f
    ) AS csd

    ---------------------------------------------------------------------------
    -- Gold diff frame phase averages
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            AVG(CASE WHEN f.ts < m.matchDurationSec / 60.0 * 0.25
                     THEN f.youValue - f.oppValue END) AS gold_diff_early,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.25
                      AND f.ts <  m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS gold_diff_mid,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS gold_diff_late
        FROM OPENJSON(doc, '$.data.match.historicalData.goldDifferenceFrames') WITH (
            ts       INT   '$.timestamp',
            youValue FLOAT '$.youValue',
            oppValue FLOAT '$.oppValue'
        ) AS f
    ) AS gdd

    ---------------------------------------------------------------------------
    -- KA diff frame phase averages
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            AVG(CASE WHEN f.ts < m.matchDurationSec / 60.0 * 0.25
                     THEN f.youValue - f.oppValue END) AS ka_diff_early,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.25
                      AND f.ts <  m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS ka_diff_mid,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS ka_diff_late
        FROM OPENJSON(doc, '$.data.match.historicalData.kaDifferenceFrames') WITH (
            ts       INT   '$.timestamp',
            youValue FLOAT '$.youValue',
            oppValue FLOAT '$.oppValue'
        ) AS f
    ) AS kad

    ---------------------------------------------------------------------------
    -- XP diff frame phase averages
    ---------------------------------------------------------------------------
    OUTER APPLY (
        SELECT
            AVG(CASE WHEN f.ts < m.matchDurationSec / 60.0 * 0.25
                     THEN f.youValue - f.oppValue END) AS xp_diff_early,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.25
                      AND f.ts <  m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS xp_diff_mid,
            AVG(CASE WHEN f.ts >= m.matchDurationSec / 60.0 * 0.5
                     THEN f.youValue - f.oppValue END) AS xp_diff_late
        FROM OPENJSON(doc, '$.data.match.historicalData.xpDifferenceFrames') WITH (
            ts       INT   '$.timestamp',
            youValue FLOAT '$.youValue',
            oppValue FLOAT '$.oppValue'
        ) AS f
    ) AS xpd

    WHERE m.winningTeam IS NOT NULL
      AND m.matchDurationSec > 300
    """


def query_features(region: str):
    """Execute the feature extraction query and return a DataFrame."""
    import pandas as pd
    import pymssql

    query = build_query(region)
    log.info("Querying features for %s...", region)
    with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
        df = pd.read_sql(query, conn)
    log.info("Got %d player-rows from %s", len(df), region)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract features from Synapse")
    parser.add_argument("--region", default="na1", choices=["na1", "euw1", "kr"])
    args = parser.parse_args()

    df = query_features(args.region)
    print(f"Shape: {df.shape}")
    print(f"Columns ({len(df.columns)}):")
    for col in df.columns:
        non_null = df[col].notna().sum()
        print(f"  {col}: {non_null}/{len(df)} non-null")
