"""Feature extraction from Synapse for XGBoost training.

SQL fetches raw match documents in a single blob scan.
Python expands to per-player rows with ~80 columns:
  - Player stats from postGameData (10 rows per match)
  - Rank tier + LP from allPlayerRanks
  - Performance scores (hardCarry, teamplay, damageShare, etc.)
  - Timeline phase aggregates (kills, deaths, wards per early/mid/late)
  - Dragon features from timeline (total, elder, per-type counts)
  - Teamfight counts per phase (15s windows with 2+ kills)
  - Diff frame phase averages (CS/gold/KA/XP, primary player only)
  - Team objectives (baron, dragon, tower, inhibitor, riftHerald)
  - Items (item0-item6), summoner spells (spell0, spell1), runes (keystone, subStyle)
  - Team compositions (for champion interaction encoding)

Game phase boundaries (timeline timestamps in ms):
  Early:  timestamp < matchDurationSec * 250       (first 25%)
  Mid:    >= matchDurationSec * 250  AND  < * 500   (25%-50%)
  Late:   >= matchDurationSec * 500                 (last 50%)

Diff frame timestamps are minute indices, so thresholds use matchDurationMin * 0.25/0.5.

Teamfight definition: 15s window with >= 2 champion kills.

Usage:
    SYNAPSE_PASSWORD=... python db/scripts/features.py [--region na1]
"""

import os
import json
import argparse
import logging
from math import floor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

SERVER = os.environ.get(
    "SYNAPSE_ENDPOINT", "crawlsynapse-ws-ondemand.sql.azuresynapse.net"
)
DATABASE = "crawldb"
USERNAME = os.environ.get("SYNAPSE_USER", "sqladmin")
PASSWORD = os.environ.get("SYNAPSE_PASSWORD", "")

DRAGON_TYPES = [
    "infernal_dragon",
    "mountain_dragon",
    "ocean_dragon",
    "hextech_dragon",
    "chemtech_dragon",
    "cloud_dragon",
]


def build_query(region: str, limit: int | None = None) -> str:
    """Single blob-scan query returning raw match documents."""
    top = f"TOP {limit}" if limit else ""
    return f"""
    SELECT {top} *
    FROM OPENROWSET(
        BULK 'teemo/0.0.0/{region}/*.jsonl.gz',
        DATA_SOURCE = 'CrawlStorage',
        FORMAT = 'CSV',
        FIELDTERMINATOR = '0x0b',
        FIELDQUOTE = '0x0b',
        ROWTERMINATOR = '0x0a'
    ) WITH (doc NVARCHAR(MAX)) AS r
    WHERE JSON_VALUE(doc, '$.data.match.winningTeam') IS NOT NULL
    """


def _phase(ts_ms: float, duration_sec: float) -> int:
    """Classify a millisecond timestamp into game phase (1=early, 2=mid, 3=late)."""
    if ts_ms < duration_sec * 250:
        return 1
    elif ts_ms < duration_sec * 500:
        return 2
    return 3


def _diff_phase(ts_min: int, duration_sec: float) -> int:
    """Classify a minute-index timestamp into game phase."""
    dm = duration_sec / 60.0
    if ts_min < dm * 0.25:
        return 1
    elif ts_min < dm * 0.5:
        return 2
    return 3


def _phase_avg(frames: list[dict], duration_sec: float) -> dict[int, float]:
    """Compute average (youValue - oppValue) per phase from diff frames."""
    buckets: dict[int, list[float]] = {1: [], 2: [], 3: []}
    for f in frames:
        phase = _diff_phase(f.get("timestamp", 0), duration_sec)
        diff = (f.get("youValue", 0) or 0) - (f.get("oppValue", 0) or 0)
        buckets[phase].append(diff)
    return {p: (sum(v) / len(v) if v else 0.0) for p, v in buckets.items()}


def _extract_dragons(timeline: list[dict]) -> dict:
    """Count dragon kills by type from timeline events."""
    result = {"total_dragons": 0, "elder_count": 0}
    for dt in DRAGON_TYPES:
        result[dt.replace("_dragon", "")] = 0

    for e in timeline:
        if e.get("monsterType") != "dragon":
            continue
        result["total_dragons"] += 1
        sub = e.get("monsterSubtype", "")
        if sub == "elder_dragon":
            result["elder_count"] += 1
        elif sub in DRAGON_TYPES:
            result[sub.replace("_dragon", "")] += 1

    return result


def _extract_teamfights(timeline: list[dict], duration_sec: float) -> dict:
    """Count teamfights (15s windows with 2+ kills) per phase."""
    buckets: dict[int, int] = {}
    for e in timeline:
        if e.get("eventType") != "champion_kill":
            continue
        ts = e.get("timestamp", 0)
        bucket = floor(ts / 15000)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    counts = {1: 0, 2: 0, 3: 0}
    for bucket, kill_count in buckets.items():
        if kill_count >= 2:
            phase = _phase(bucket * 15000, duration_sec)
            counts[phase] += 1

    return {
        "early_teamfights": counts[1],
        "mid_teamfights": counts[2],
        "late_teamfights": counts[3],
    }


def _extract_player_timeline(
    timeline: list[dict], player_name: str, player_tag: str, duration_sec: float
) -> dict:
    """Count kills, deaths, wards per phase for a specific player."""
    counts = {}
    for prefix in ("kills", "deaths", "wards"):
        for phase_name in ("early", "mid", "late"):
            counts[f"{phase_name}_{prefix}"] = 0

    for e in timeline:
        ts = e.get("timestamp", 0)
        phase = _phase(ts, duration_sec)
        phase_name = {1: "early", 2: "mid", 3: "late"}[phase]
        etype = e.get("eventType")

        if etype == "champion_kill":
            if e.get("riotUserName") == player_name and e.get("riotTagLine") == player_tag:
                counts[f"{phase_name}_kills"] += 1
            if e.get("victimRiotUserName") == player_name and e.get("victimRiotTagLine") == player_tag:
                counts[f"{phase_name}_deaths"] += 1
        elif etype == "ward_placed":
            if e.get("riotUserName") == player_name and e.get("riotTagLine") == player_tag:
                counts[f"{phase_name}_wards"] += 1

    return counts


def extract_features(docs: list[str]) -> list[dict]:
    """Parse raw match JSON strings and expand to per-player feature rows."""
    records = []

    for raw_doc in docs:
        doc = json.loads(raw_doc)
        match = doc["data"]["match"]
        summary = match["matchSummary"]
        hist = match["historicalData"]

        winning_team = match["winningTeam"]
        duration_sec = summary.get("matchDuration", 1)
        if duration_sec < 300:
            continue  # skip remakes

        match_time = summary.get("matchCreationTime", 0)
        match_id = hist.get("matchId")
        primary_name = match.get("playerInfo", {}).get("riotUserName")
        primary_tag = match.get("playerInfo", {}).get("riotTagLine")

        # Build rank lookup
        rank_lookup = {}
        for r in match.get("allPlayerRanks", []) or []:
            key = f"{r['riotUserName']}#{r['riotTagLine']}"
            solo = None
            for s in r.get("rankScores", []) or []:
                if s.get("queueType") == "ranked_solo_5x5":
                    solo = s
                    break
            if solo is None and r.get("rankScores"):
                solo = r["rankScores"][0]
            if solo:
                rank_lookup[key] = {"tier": solo.get("tier"), "lp": solo.get("lp", 0)}

        # Build performance score lookup
        perf_lookup = {}
        for ps in match.get("performanceScore", []) or []:
            key = f"{ps['riotUserName']}#{ps['riotTagLine']}"
            perf_lookup[key] = ps

        # Team objectives
        t1 = hist.get("teamOneOverview", {}) or {}
        t2 = hist.get("teamTwoOverview", {}) or {}

        # Timeline (match-level features computed once)
        timeline = hist.get("timelineData", []) or []
        dragons = _extract_dragons(timeline)
        teamfights = _extract_teamfights(timeline, duration_sec)

        # Diff frames (primary player only)
        cs_diff = _phase_avg(hist.get("csDifferenceFrames", []) or [], duration_sec)
        gold_diff = _phase_avg(hist.get("goldDifferenceFrames", []) or [], duration_sec)
        ka_diff = _phase_avg(hist.get("kaDifferenceFrames", []) or [], duration_sec)
        xp_diff = _phase_avg(hist.get("xpDifferenceFrames", []) or [], duration_sec)

        # Team compositions
        team_a = summary.get("teamA", []) or []
        team_b = summary.get("teamB", []) or []

        # Per-player expansion
        for p in hist.get("postGameData", []) or []:
            pkey = f"{p['riotUserName']}#{p['riotTagLine']}"
            rank_info = rank_lookup.get(pkey, {"tier": None, "lp": 0})
            perf = perf_lookup.get(pkey, {})
            is_primary = (p["riotUserName"] == primary_name and p["riotTagLine"] == primary_tag)

            # Team objectives for this player's team
            team_obj = t1 if p["teamId"] == 100 else t2

            # Player timeline
            player_tl = _extract_player_timeline(
                timeline, p["riotUserName"], p["riotTagLine"], duration_sec
            )

            # Items
            items = p.get("items", []) or []
            item_dict = {f"item{i}": (items[i] if i < len(items) else 0) for i in range(7)}

            # Spells
            spells = p.get("summonerSpells", []) or []
            spell_dict = {
                "spell0": spells[0] if len(spells) > 0 else 0,
                "spell1": spells[1] if len(spells) > 1 else 0,
            }

            record = {
                # Match identifiers
                "matchId": match_id,
                "matchDurationSec": duration_sec,
                "winningTeam": winning_team,
                "matchCreationTime": match_time,
                "primaryUserName": primary_name,
                "primaryTagLine": primary_tag,
                # Player stats
                "riotUserName": p["riotUserName"],
                "riotTagLine": p["riotTagLine"],
                "championId": p.get("championId"),
                "teamId": p["teamId"],
                "role": p.get("role"),
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "cs": p.get("cs", 0),
                "jungleCs": p.get("jungleCs", 0),
                "damage": p.get("damage", 0),
                "damageTaken": p.get("damageTaken", 0),
                "gold": p.get("gold", 0),
                "level": p.get("level", 1),
                "wardsPlaced": p.get("wardsPlaced", 0),
                "carryPercentage": p.get("carryPercentage", 0),
                **item_dict,
                **spell_dict,
                "keystone": p.get("keystone"),
                "subStyle": p.get("subStyle"),
                # Rank
                "rank_tier": rank_info.get("tier"),
                "rank_lp": rank_info.get("lp", 0),
                # Performance scores
                "hardCarry": perf.get("hardCarry"),
                "teamplay": perf.get("teamplay"),
                "damageShareTotal": perf.get("damageShareTotal"),
                "goldShareTotal": perf.get("goldShareTotal"),
                "killParticipationTotal": perf.get("killParticipationTotal"),
                "visionScoreTotal": perf.get("visionScoreTotal"),
                "finalLvlDiffTotal": perf.get("finalLvlDiffTotal"),
                # Team objectives
                "baron_kills": team_obj.get("baronKills", 0),
                "dragon_kills": team_obj.get("dragonKills", 0),
                "tower_kills": team_obj.get("towerKills", 0),
                "inhibitor_kills": team_obj.get("inhibitorKills", 0),
                "rift_herald_kills": team_obj.get("riftHeraldKills", 0),
                # Per-player timeline phase aggregates
                **player_tl,
                # Dragon features (match-level)
                **dragons,
                # Teamfights (match-level)
                **teamfights,
                # Diff frame phase averages (primary player only)
                "cs_diff_early": cs_diff[1] if is_primary else 0,
                "cs_diff_mid": cs_diff[2] if is_primary else 0,
                "cs_diff_late": cs_diff[3] if is_primary else 0,
                "gold_diff_early": gold_diff[1] if is_primary else 0,
                "gold_diff_mid": gold_diff[2] if is_primary else 0,
                "gold_diff_late": gold_diff[3] if is_primary else 0,
                "ka_diff_early": ka_diff[1] if is_primary else 0,
                "ka_diff_mid": ka_diff[2] if is_primary else 0,
                "ka_diff_late": ka_diff[3] if is_primary else 0,
                "xp_diff_early": xp_diff[1] if is_primary else 0,
                "xp_diff_mid": xp_diff[2] if is_primary else 0,
                "xp_diff_late": xp_diff[3] if is_primary else 0,
                # Team compositions (JSON for Python-side champion interaction encoding)
                "teamA_json": json.dumps(team_a),
                "teamB_json": json.dumps(team_b),
            }
            records.append(record)

    return records


def query_features(region: str, limit: int | None = None):
    """Fetch raw match docs from Synapse and extract per-player features."""
    import time
    import pandas as pd
    import pymssql

    query = build_query(region, limit=limit)

    # Retry connection (Synapse serverless pools can be slow to wake)
    docs = None
    for attempt in range(3):
        try:
            log.info("Querying raw docs for %s (attempt %d)...", region, attempt + 1)
            with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                docs = [row[0] for row in cursor]
            break
        except Exception as e:
            if attempt < 2:
                log.warning("Connection failed, retrying in 5s: %s", e)
                time.sleep(5)
            else:
                raise

    log.info("Got %d matches from %s, extracting features...", len(docs), region)
    records = extract_features(docs)
    df = pd.DataFrame(records)
    log.info("Extracted %d player-rows with %d columns", len(df), len(df.columns))
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
