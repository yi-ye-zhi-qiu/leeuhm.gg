"""Logistic regression training pipeline for match outcome prediction.

Reads SQL-extracted features from db/scripts/features.py and adds
Python-side feature engineering:
  - Per-minute rates (kills/deaths/assists/cs/gold/damage/damageTaken/wards)
  - Rank tier encoding (TIER_MAP)
  - Win/loss streaks (cross-match temporal)
  - One-hot encoded items, summoner spells, runes
  - Champion lane matchup pairs (label-encoded)
  - Champion teammate synergy pairs (label-encoded)

Exports:
  - model/{region}.json – coefficients, intercept, feature_names, feature_means
    (frontend computes SHAP inline as coef[i] * (x[i] - mean[i]))

Usage:
    SYNAPSE_PASSWORD=... python model/train_xgb.py [--region na1]
"""

import os
import sys
import json
import argparse
import logging
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add project root so we can import db.scripts.features
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.scripts.features import query_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

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

# Per-minute rate columns: (source_col, output_name, display_name)
PM_RATES = [
    ("damageTaken", "damageTaken_pm", "Dmg Taken/min"),
    ("wardsPlaced", "wardsPlaced_pm", "Wards/min"),
]

# Raw SQL columns used directly as features
RAW_FEATURES = [
    ("visionScoreTotal", "Vision Score"),
]

RANK_FEATURES = [
    ("rank_tier_num", "Rank"),
]

STREAK_THRESHOLD = 2

OBJECTIVE_FEATURES = []

PERFORMANCE_FEATURES = [
    ("teamplay", "Teamplay"),
    ("damageShareTotal", "Damage Share"),
    ("goldShareTotal", "Gold Share"),
    ("killParticipationTotal", "Kill Participation"),
    ("visionScoreTotal", "Vision Score (perf)"),
    ("finalLvlDiffTotal", "Level Diff"),
]

# Removed late_deaths (proxy for win/loss)
PHASE_FEATURES = [
    ("early_kills", "Early Kills"),
    ("mid_kills", "Mid Kills"),
    ("late_kills", "Late Kills"),
    ("early_deaths", "Early Deaths"),
    ("mid_deaths", "Mid Deaths"),
    ("early_wards", "Early Wards"),
    ("mid_wards", "Mid Wards"),
    ("late_wards", "Late Wards"),
]

TEAMFIGHT_FEATURES = [
    ("early_teamfights", "Early Teamfights"),
    ("mid_teamfights", "Mid Teamfights"),
    ("late_teamfights", "Late Teamfights"),
]

DIFF_FEATURES = [
    ("cs_diff_early", "CS Diff Early"),
    ("cs_diff_mid", "CS Diff Mid"),
    ("cs_diff_late", "CS Diff Late"),
    ("gold_diff_early", "Gold Diff Early"),
    ("gold_diff_mid", "Gold Diff Mid"),
    ("gold_diff_late", "Gold Diff Late"),
    ("ka_diff_early", "KA Diff Early"),
    ("ka_diff_mid", "KA Diff Mid"),
    ("ka_diff_late", "KA Diff Late"),
    ("xp_diff_early", "XP Diff Early"),
    ("xp_diff_mid", "XP Diff Mid"),
    ("xp_diff_late", "XP Diff Late"),
]


def compute_streaks(results: list[bool]) -> dict:
    """Given a list of win/loss booleans (oldest first), return streak indicators."""
    n = len(results)
    if n >= STREAK_THRESHOLD:
        recent = results[-STREAK_THRESHOLD:]
        return {
            "win_streak": 1 if all(recent) else 0,
            "loss_streak": 1 if not any(recent) else 0,
        }
    return {"win_streak": 0, "loss_streak": 0}


def add_per_minute_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-minute rate columns."""
    dm = df["matchDurationSec"] / 60.0
    for src, out, _ in PM_RATES:
        if src == "cs":
            df[out] = (df["cs"].fillna(0) + df["jungleCs"].fillna(0)) / dm
        else:
            df[out] = df[src].fillna(0) / dm
    return df


def add_rank_encoding(df: pd.DataFrame) -> pd.DataFrame:
    """Encode rank tier as numeric."""
    df["rank_tier_num"] = df["rank_tier"].map(
        lambda t: TIER_MAP.get(str(t).upper(), 4) if pd.notna(t) else 4
    )
    df["rank_lp"] = df["rank_lp"].fillna(0)
    return df


def add_streaks(df: pd.DataFrame) -> pd.DataFrame:
    """Add win/loss streak features via cross-match temporal computation."""
    player_history: dict[str, list[tuple[int, bool]]] = defaultdict(list)

    # First pass: collect history
    for _, row in df.iterrows():
        pkey = f"{row['riotUserName']}#{row['riotTagLine']}"
        won = row["teamId"] == row["winningTeam"]
        player_history[pkey].append((row["matchCreationTime"], won))

    # Sort each player's history
    for pkey in player_history:
        player_history[pkey].sort(key=lambda x: x[0])

    # Second pass: compute streaks for each row
    streak_records = []
    for _, row in df.iterrows():
        pkey = f"{row['riotUserName']}#{row['riotTagLine']}"
        history = player_history[pkey]
        preceding = [won for t, won in history if t < row["matchCreationTime"]]
        streak_records.append(compute_streaks(preceding))

    streak_df = pd.DataFrame(streak_records, index=df.index)
    return pd.concat([df, streak_df], axis=1)


def add_champion_interactions(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Add champion lane matchup and teammate synergy features (label-encoded)."""
    lane_matchups = []
    synergy_pairs = [[] for _ in range(4)]

    for _, row in df.iterrows():
        team_a = json.loads(row["teamA_json"]) if isinstance(row["teamA_json"], str) else row["teamA_json"]
        team_b = json.loads(row["teamB_json"]) if isinstance(row["teamB_json"], str) else row["teamB_json"]

        if not team_a or not team_b:
            lane_matchups.append(None)
            for s in synergy_pairs:
                s.append(None)
            continue

        # Determine which team this player is on
        player_team = team_a if row["teamId"] == team_a[0].get("teamId", 100) else team_b
        enemy_team = team_b if player_team is team_a else team_a

        # Build role->champion maps
        player_role_map = {m["role"]: m["championId"] for m in player_team}
        enemy_role_map = {m["role"]: m["championId"] for m in enemy_team}

        # Lane matchup: player's champion vs enemy in same role
        player_champ = row["championId"]
        enemy_champ = enemy_role_map.get(row["role"])
        if enemy_champ:
            matchup = f"{min(player_champ, enemy_champ)}_{max(player_champ, enemy_champ)}"
        else:
            matchup = None
        lane_matchups.append(matchup)

        # Teammate synergies: pair with each of the other 4 teammates (sorted by role)
        teammates = sorted(
            [m for m in player_team if m["championId"] != player_champ],
            key=lambda m: m["role"],
        )
        for i in range(4):
            if i < len(teammates):
                tc = teammates[i]["championId"]
                pair = f"{min(player_champ, tc)}_{max(player_champ, tc)}"
                synergy_pairs[i].append(pair)
            else:
                synergy_pairs[i].append(None)

    # Label-encode
    df["lane_matchup"] = pd.Categorical(lane_matchups).codes
    cols = ["lane_matchup"]
    names = ["Lane Matchup"]

    for i in range(4):
        col = f"synergy_{i}"
        df[col] = pd.Categorical(synergy_pairs[i]).codes
        cols.append(col)
        names.append(f"Synergy {i}")

    return df, cols, names


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """
    Build the full feature matrix from the SQL-extracted DataFrame.
    Returns (X_df, feature_col_names, feature_display_names).
    """
    df = add_per_minute_rates(df)
    df = add_rank_encoding(df)
    df = add_streaks(df)
    df, champ_cols, champ_names = add_champion_interactions(df)

    # Assemble feature columns and display names in order
    feature_cols = []
    feature_names = []

    for _, col, name in PM_RATES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in RAW_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in RANK_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    feature_cols.append("win_streak")
    feature_names.append("Win Streak")
    feature_cols.append("loss_streak")
    feature_names.append("Loss Streak")

    for col, name in OBJECTIVE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in PERFORMANCE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in PHASE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in TEAMFIGHT_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    for col, name in DIFF_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    feature_cols.extend(champ_cols)
    feature_names.extend(champ_names)

    return df, feature_cols, feature_names


def train_region(region: str, parquet_path: str | None = None, limit: int | None = None):
    """Train logistic regression model for a single region."""
    if parquet_path:
        log.info("Loading features from %s", parquet_path)
        df = pd.read_parquet(parquet_path)
    else:
        df = query_features(region, limit=limit)
    log.info("%s: %d raw player-rows", region, len(df))

    # Build target variable
    df["win"] = (df["teamId"] == df["winningTeam"]).astype(int)

    # Build feature matrix
    df, feature_cols, feature_names = build_feature_matrix(df)
    log.info("%s: %d features", region, len(feature_cols))

    # Prepare X and y
    X = df[feature_cols].fillna(0).values.astype(np.float64)
    y = df["win"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale features for logistic regression
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    model.fit(X_train_s, y_train)

    accuracy = float(model.score(X_test_s, y_test))
    log.info("%s: accuracy = %.4f", region, accuracy)

    # For linear SHAP: coef and mean are in original (unscaled) space
    # scaled_coef * (x - mean) / std = original_coef * (x - mean)
    # so original_coef = scaled_coef / std
    scaled_coefs = model.coef_[0]
    original_coefs = scaled_coefs / scaler.scale_

    # Export model JSON (frontend computes SHAP inline)
    model_dir = os.path.dirname(__file__)
    meta = {
        "model_type": "logistic_regression",
        "intercept": float(model.intercept_[0]),
        "coefficients": [float(c) for c in original_coefs],
        "feature_names": feature_names,
        "feature_means": [float(m) for m in scaler.mean_],
        "accuracy": round(accuracy, 4),
        "n_samples": int(len(X_train)),
        "n_features": len(feature_cols),
    }
    meta_path = os.path.join(model_dir, f"{region}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    log.info("%s: model saved to %s", region, meta_path)

    log.info("  Accuracy: %.4f", accuracy)
    log.info("  Features: %d total", len(feature_cols))
    log.info("  Samples: %d train, %d test", len(X_train), len(X_test))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train model")
    parser.add_argument(
        "--region",
        nargs="+",
        default=REGIONS,
        choices=REGIONS,
        help="Region(s) to train",
    )
    parser.add_argument(
        "--parquet",
        type=str,
        default=None,
        help="Path to pre-extracted parquet file (skips Synapse query)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of matches from Synapse (for testing)",
    )
    args = parser.parse_args()

    for region in args.region:
        try:
            train_region(region, parquet_path=args.parquet, limit=args.limit)
        except Exception as e:
            log.error("Failed to train %s: %s", region, e, exc_info=True)
