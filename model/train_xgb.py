"""XGBoost training pipeline for match outcome prediction.

Replaces the logistic regression model with XGBoost binary:logistic.
Reads SQL-extracted features from db/scripts/features.py and adds
Python-side feature engineering:
  - Per-minute rates (kills/deaths/assists/cs/gold/damage/damageTaken/wards)
  - Rank tier encoding (TIER_MAP)
  - Win/loss streaks (cross-match temporal, same logic as old train.py)
  - One-hot encoded items (~200 binary), summoner spells (~12), runes (~40)
  - Champion lane matchup pairs (label-encoded categorical)
  - Champion teammate synergy pairs (label-encoded categorical)

Exports:
  - model/{region}.json  – model metadata (type, base_value, accuracy, feature_names)
  - model/{region}.xgb   – XGBoost model binary
  - model/{region}_shap.json – precomputed top-6 SHAP values per player-match

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
import xgboost as xgb
from sklearn.model_selection import train_test_split

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
    ("kills", "kills_pm", "Kills/min"),
    ("deaths", "deaths_pm", "Deaths/min"),
    ("assists", "assists_pm", "Assists/min"),
    ("cs", "cs_pm", "CS/min"),
    ("gold", "gold_pm", "Gold/min"),
    ("damage", "damage_pm", "Damage/min"),
    ("damageTaken", "damageTaken_pm", "Dmg Taken/min"),
    ("wardsPlaced", "wardsPlaced_pm", "Wards/min"),
]

# Raw SQL columns used directly as features
RAW_FEATURES = [
    ("visionScoreTotal", "Vision Score"),
    ("level", "Level"),
    ("carryPercentage", "Carry %"),
]

RANK_FEATURES = [
    ("rank_tier_num", "Rank"),
    ("rank_lp", "LP"),
]

STREAK_THRESHOLDS = [1, 2, 3, 5, 10]

OBJECTIVE_FEATURES = [
    ("baron_kills", "Baron Kills"),
    ("dragon_kills", "Dragon Kills"),
    ("tower_kills", "Tower Kills"),
    ("inhibitor_kills", "Inhibitor Kills"),
    ("rift_herald_kills", "Rift Herald Kills"),
]

PERFORMANCE_FEATURES = [
    ("hardCarry", "Hard Carry"),
    ("teamplay", "Teamplay"),
    ("damageShareTotal", "Damage Share"),
    ("goldShareTotal", "Gold Share"),
    ("killParticipationTotal", "Kill Participation"),
    ("visionScoreTotal", "Vision Score (perf)"),
    ("finalLvlDiffTotal", "Level Diff"),
]

PHASE_FEATURES = [
    ("early_kills", "Early Kills"),
    ("mid_kills", "Mid Kills"),
    ("late_kills", "Late Kills"),
    ("early_deaths", "Early Deaths"),
    ("mid_deaths", "Mid Deaths"),
    ("late_deaths", "Late Deaths"),
    ("early_wards", "Early Wards"),
    ("mid_wards", "Mid Wards"),
    ("late_wards", "Late Wards"),
]

TEAMFIGHT_FEATURES = [
    ("early_teamfights", "Early Teamfights"),
    ("mid_teamfights", "Mid Teamfights"),
    ("late_teamfights", "Late Teamfights"),
]

DRAGON_FEATURES = [
    ("total_dragons", "Total Dragons"),
    ("elder_count", "Elder Dragons"),
    ("infernal", "Infernal"),
    ("mountain", "Mountain"),
    ("ocean", "Ocean"),
    ("hextech", "Hextech"),
    ("chemtech", "Chemtech"),
    ("cloud", "Cloud"),
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
    streaks = {}
    for threshold in STREAK_THRESHOLDS:
        if n >= threshold:
            recent = results[-threshold:]
            streaks[f"win_streak_{threshold}"] = 1 if all(recent) else 0
            streaks[f"loss_streak_{threshold}"] = 1 if not any(recent) else 0
        else:
            streaks[f"win_streak_{threshold}"] = 0
            streaks[f"loss_streak_{threshold}"] = 0
    return streaks


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


def add_one_hot_items(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """One-hot encode items (item0..item6). Returns df, column names, display names."""
    item_cols = [f"item{i}" for i in range(7)]
    all_items = set()
    for col in item_cols:
        all_items.update(df[col].dropna().unique())
    all_items.discard(0)  # item 0 = empty slot
    all_items = sorted(all_items)

    cols = []
    names = []
    for item_id in all_items:
        col_name = f"item_{item_id}"
        df[col_name] = 0
        for ic in item_cols:
            df[col_name] = df[col_name] | (df[ic] == item_id).astype(int)
        cols.append(col_name)
        names.append(f"Item {item_id}")

    return df, cols, names


def add_one_hot_spells(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """One-hot encode summoner spells (spell0, spell1)."""
    all_spells = set()
    for col in ["spell0", "spell1"]:
        all_spells.update(df[col].dropna().unique())
    all_spells.discard(0)
    all_spells = sorted(all_spells)

    cols = []
    names = []
    for spell_id in all_spells:
        col_name = f"spell_{spell_id}"
        df[col_name] = ((df["spell0"] == spell_id) | (df["spell1"] == spell_id)).astype(int)
        cols.append(col_name)
        names.append(f"Spell {spell_id}")

    return df, cols, names


def add_one_hot_runes(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """One-hot encode keystone and subStyle runes."""
    all_keystones = sorted(df["keystone"].dropna().unique())
    all_substyles = sorted(df["subStyle"].dropna().unique())

    cols = []
    names = []
    for ks in all_keystones:
        col_name = f"ks_{int(ks)}"
        df[col_name] = (df["keystone"] == ks).astype(int)
        cols.append(col_name)
        names.append(f"Keystone {int(ks)}")

    for ss in all_substyles:
        col_name = f"ss_{int(ss)}"
        df[col_name] = (df["subStyle"] == ss).astype(int)
        cols.append(col_name)
        names.append(f"SubStyle {int(ss)}")

    return df, cols, names


def add_champion_interactions(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Add champion lane matchup and teammate synergy features (label-encoded categorical)."""
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
    df, item_cols, item_names = add_one_hot_items(df)
    df, spell_cols, spell_names = add_one_hot_spells(df)
    df, rune_cols, rune_names = add_one_hot_runes(df)
    df, champ_cols, champ_names = add_champion_interactions(df)

    # Assemble feature columns and display names in order
    feature_cols = []
    feature_names = []

    # Per-minute rates
    for _, col, name in PM_RATES:
        feature_cols.append(col)
        feature_names.append(name)

    # Raw stats
    for col, name in RAW_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Rank
    for col, name in RANK_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Streaks
    for t in STREAK_THRESHOLDS:
        feature_cols.append(f"win_streak_{t}")
        feature_names.append(f"W Streak {t}" if t < 10 else "W Streak 10+")
    for t in STREAK_THRESHOLDS:
        feature_cols.append(f"loss_streak_{t}")
        feature_names.append(f"L Streak {t}" if t < 10 else "L Streak 10+")

    # Team objectives
    for col, name in OBJECTIVE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Performance scores
    for col, name in PERFORMANCE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Phase kills/deaths/wards
    for col, name in PHASE_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Teamfights
    for col, name in TEAMFIGHT_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Dragons
    for col, name in DRAGON_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # Diff frames
    for col, name in DIFF_FEATURES:
        feature_cols.append(col)
        feature_names.append(name)

    # One-hot items
    feature_cols.extend(item_cols)
    feature_names.extend(item_names)

    # One-hot spells
    feature_cols.extend(spell_cols)
    feature_names.extend(spell_names)

    # One-hot runes
    feature_cols.extend(rune_cols)
    feature_names.extend(rune_names)

    # Champion interactions (categorical)
    feature_cols.extend(champ_cols)
    feature_names.extend(champ_names)

    return df, feature_cols, feature_names


def train_region(region: str):
    """Train XGBoost model for a single region."""
    df = query_features(region)
    log.info("%s: %d raw player-rows", region, len(df))

    # Build target variable
    df["win"] = (df["teamId"] == df["winningTeam"]).astype(int)

    # Build feature matrix
    df, feature_cols, feature_names = build_feature_matrix(df)
    log.info("%s: %d features", region, len(feature_cols))

    # Prepare X and y
    X = df[feature_cols].fillna(0).copy()
    y = df["win"].values

    # Mark categorical features for XGBoost
    cat_cols = [c for c in feature_cols if c in ("lane_matchup", "synergy_0", "synergy_1", "synergy_2", "synergy_3")]
    for c in cat_cols:
        X[c] = X[c].astype("category")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train indices for SHAP export later
    train_idx = X_train.index
    test_idx = X_test.index

    model = xgb.XGBClassifier(
        objective="binary:logistic",
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        tree_method="hist",
        random_state=42,
        verbosity=1,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=20)

    accuracy = model.score(X_test, y_test)
    log.info("%s: accuracy = %.4f", region, accuracy)

    # Save XGBoost model binary
    model_dir = os.path.dirname(__file__)
    model.save_model(os.path.join(model_dir, f"{region}.xgb"))

    # Compute SHAP values using TreeExplainer
    log.info("%s: computing SHAP values...", region)
    import shap
    explainer = shap.TreeExplainer(model)

    # Compute SHAP for ALL samples (train + test)
    X_all = pd.concat([X_train, X_test])
    shap_values = explainer.shap_values(X_all)
    base_value = float(explainer.expected_value)

    # Build SHAP lookup: matchId -> playerKey -> top-6 SHAP features
    shap_lookup: dict[str, dict[str, dict]] = {}
    all_idx = list(train_idx) + list(test_idx)

    for i, idx in enumerate(all_idx):
        row = df.loc[idx]
        match_id = str(row["matchId"])
        player_key = f"{row['riotUserName']}#{row['riotTagLine']}"

        sv = shap_values[i]
        # Pair with feature names and sort by |shap|
        pairs = list(zip(feature_names, X_all.iloc[i].values, sv))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        top6 = [
            {"feature": name, "value": float(val), "shapValue": float(shap_val)}
            for name, val, shap_val in pairs[:6]
        ]

        if match_id not in shap_lookup:
            shap_lookup[match_id] = {}
        shap_lookup[match_id][player_key] = {
            "baseValue": float(1 / (1 + np.exp(-base_value))),
            "predictedProbability": float(
                1 / (1 + np.exp(-(base_value + float(np.sum(sv)))))
            ),
            "shapValues": top6,
        }

    # Save SHAP lookup
    shap_path = os.path.join(model_dir, f"{region}_shap.json")
    with open(shap_path, "w") as f:
        json.dump(shap_lookup, f)
    log.info("%s: SHAP values saved to %s (%d matches)", region, shap_path, len(shap_lookup))

    # Save model metadata JSON
    meta = {
        "model_type": "xgboost",
        "base_value": base_value,
        "accuracy": round(accuracy, 4),
        "feature_names": feature_names,
        "n_samples": int(len(X_train)),
        "n_features": len(feature_cols),
    }
    meta_path = os.path.join(model_dir, f"{region}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    log.info("%s: model metadata saved to %s", region, meta_path)

    # Sanity checks
    log.info("  Accuracy: %.4f (vs ~0.80 LR baseline)", accuracy)
    log.info("  Features: %d total", len(feature_cols))
    log.info("  Samples: %d train, %d test", len(X_train), len(X_test))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost model")
    parser.add_argument(
        "--region",
        nargs="+",
        default=REGIONS,
        choices=REGIONS,
        help="Region(s) to train",
    )
    args = parser.parse_args()

    for region in args.region:
        try:
            train_region(region)
        except Exception as e:
            log.error("Failed to train %s: %s", region, e, exc_info=True)
