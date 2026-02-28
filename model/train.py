"""
Train per-region logistic regression models for SHAP force plots.

Features (per player per match):
  - Per-minute rates: kills, deaths, assists, CS, gold, damage, damageTaken, wards
  - Raw: visionScore, level, carryPercentage
  - Rank: tier (numeric 1-8), LP
  - Momentum: win/loss streak indicators (last 1, 2, 3, 5, 10+ games)

Usage:
    SYNAPSE_PASSWORD=... python model/train.py
"""

import os
import json
import logging
from collections import defaultdict

import numpy as np
import pandas as pd
import pymssql
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

SERVER = os.environ.get(
    "SYNAPSE_ENDPOINT", "crawlsynapse-ws-ondemand.sql.azuresynapse.net"
)
DATABASE = "crawldb"
USERNAME = os.environ.get("SYNAPSE_USER", "sqladmin")
PASSWORD = os.environ["SYNAPSE_PASSWORD"]

REGIONS = ["na1", "euw1", "kr"]

TIER_MAP = {
    "IRON": 1,
    "BRONZE": 2,
    "SILVER": 3,
    "GOLD": 4,
    "PLATINUM": 5,
    "EMERALD": 6,
    "DIAMOND": 7,
    "MASTER": 8,
    "GRANDMASTER": 8,
    "CHALLENGER": 8,
}

FEATURE_COLS = [
    "kills_pm",
    "deaths_pm",
    "assists_pm",
    "cs_pm",
    "gold_pm",
    "damage_pm",
    "damageTaken_pm",
    "wardsPlaced_pm",
    "visionScore",
    "level",
    "carryPercentage",
    "rank_tier",
    "lp",
    "win_streak_1",
    "win_streak_2",
    "win_streak_3",
    "win_streak_5",
    "win_streak_10",
    "loss_streak_1",
    "loss_streak_2",
    "loss_streak_3",
    "loss_streak_5",
    "loss_streak_10",
]

FEATURE_NAMES = [
    "Kills/min",
    "Deaths/min",
    "Assists/min",
    "CS/min",
    "Gold/min",
    "Damage/min",
    "Dmg Taken/min",
    "Wards/min",
    "Vision Score",
    "Level",
    "Carry %",
    "Rank",
    "LP",
    "W Streak 1",
    "W Streak 2",
    "W Streak 3",
    "W Streak 5",
    "W Streak 10+",
    "L Streak 1",
    "L Streak 2",
    "L Streak 3",
    "L Streak 5",
    "L Streak 10+",
]


def query_region(region: str) -> pd.DataFrame:
    query = f"""
    SELECT *
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
    log.info(f"Querying {region}...")
    with pymssql.connect(SERVER, USERNAME, PASSWORD, DATABASE) as conn:
        rows = pd.read_sql(query, conn)
    log.info(f"Got {len(rows)} matches from {region}")
    return rows


def compute_streaks(results: list[bool]) -> dict:
    """Given a list of win/loss booleans (oldest first), return streak indicators."""
    n = len(results)
    streaks = {}
    for threshold in [1, 2, 3, 5, 10]:
        if n >= threshold:
            recent = results[-threshold:]
            streaks[f"win_streak_{threshold}"] = 1 if all(recent) else 0
            streaks[f"loss_streak_{threshold}"] = 1 if not any(recent) else 0
        else:
            streaks[f"win_streak_{threshold}"] = 0
            streaks[f"loss_streak_{threshold}"] = 0
    return streaks


def extract_features(rows: pd.DataFrame) -> pd.DataFrame:
    # First pass: collect per-player match history for streak computation
    player_history: dict[str, list[tuple[int, bool]]] = defaultdict(list)
    parsed_matches = []

    for _, row in rows.iterrows():
        doc = json.loads(row["doc"])
        match = doc["data"]["match"]
        winning_team = match["winningTeam"]
        match_time = match["matchSummary"].get("matchCreationTime", 0)
        duration_sec = match["matchSummary"].get("matchDuration", 1)
        duration_min = duration_sec / 60.0

        if duration_min < 5:  # skip remakes
            continue

        post_game = match["historicalData"]["postGameData"]
        ranks_list = match.get("allPlayerRanks", [])

        # Build rank lookup
        rank_lookup = {}
        for r in ranks_list:
            key = f"{r['riotUserName']}#{r['riotTagLine']}"
            solo = None
            for s in r.get("rankScores", []):
                if s.get("queueType") == "ranked_solo_5x5":
                    solo = s
                    break
            if solo is None and r.get("rankScores"):
                solo = r["rankScores"][0]
            if solo:
                rank_lookup[key] = {
                    "tier": TIER_MAP.get(solo["tier"].upper(), 4),
                    "lp": solo.get("lp", 0),
                }

        parsed_matches.append(
            {
                "match_time": match_time,
                "duration_min": duration_min,
                "winning_team": winning_team,
                "post_game": post_game,
                "rank_lookup": rank_lookup,
            }
        )

        # Record each player's result for streak tracking
        for p in post_game:
            pkey = f"{p['riotUserName']}#{p['riotTagLine']}"
            won = p["teamId"] == winning_team
            player_history[pkey].append((match_time, won))

    # Sort each player's history by time
    for pkey in player_history:
        player_history[pkey].sort(key=lambda x: x[0])

    # Second pass: extract features with streak context
    records = []
    for m in parsed_matches:
        for p in m["post_game"]:
            pkey = f"{p['riotUserName']}#{p['riotTagLine']}"
            rank_info = m["rank_lookup"].get(pkey, {"tier": 4, "lp": 0})
            dm = m["duration_min"]

            # Compute streak features from this player's history
            history = player_history[pkey]
            preceding_results = [
                won for t, won in history if t < m["match_time"]
            ]
            streaks = compute_streaks(preceding_results)

            record = {
                "kills_pm": p["kills"] / dm,
                "deaths_pm": p["deaths"] / dm,
                "assists_pm": p["assists"] / dm,
                "cs_pm": (p["cs"] + p.get("jungleCs", 0)) / dm,
                "gold_pm": p["gold"] / dm,
                "damage_pm": p["damage"] / dm,
                "damageTaken_pm": p.get("damageTaken", 0) / dm,
                "wardsPlaced_pm": p.get("wardsPlaced", 0) / dm,
                "visionScore": p.get("visionScore", 0),
                "level": p["level"],
                "carryPercentage": p.get("carryPercentage", 0),
                "rank_tier": rank_info["tier"],
                "lp": rank_info["lp"],
                **streaks,
                "win": 1 if p["teamId"] == m["winning_team"] else 0,
            }
            records.append(record)

    return pd.DataFrame(records)


def train_region(region: str):
    rows = query_region(region)
    df = extract_features(rows)
    log.info(f"{region}: {len(df)} player-rows extracted")

    X = df[FEATURE_COLS].fillna(0).values
    y = df["win"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LogisticRegression(
        penalty="l2", solver="liblinear", max_iter=1000, C=0.1
    )
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    log.info(f"{region}: accuracy = {accuracy:.4f}")

    output = {
        "feature_names": FEATURE_NAMES,
        "coefficients": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "feature_means": X_train.mean(axis=0).tolist(),
        "n_samples": int(len(X_train)),
        "accuracy": round(accuracy, 4),
    }

    output_path = os.path.join(os.path.dirname(__file__), f"{region}.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    log.info(f"{region}: model saved to {output_path}")

    # Sanity checks
    coef_dict = dict(zip(FEATURE_NAMES, model.coef_[0]))
    log.info(f"  Kills/min coef: {coef_dict['Kills/min']:+.4f} (expect positive)")
    log.info(f"  Deaths/min coef: {coef_dict['Deaths/min']:+.4f} (expect negative)")
    log.info(f"  LP coef: {coef_dict['LP']:+.4f}")
    for s in ["W Streak 3", "L Streak 3"]:
        log.info(f"  {s} coef: {coef_dict[s]:+.4f}")


if __name__ == "__main__":
    for region in REGIONS:
        try:
            train_region(region)
        except Exception as e:
            log.error(f"Failed to train {region}: {e}", exc_info=True)
