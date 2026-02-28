import { readFileSync, existsSync } from "fs";
import { join } from "path";
import type { ShapResult, ShapValue, MatchData } from "@/types/match";

interface ShapModel {
  model_type: string;
  intercept: number;
  coefficients: number[];
  feature_names: string[];
  feature_means: number[];
}

const modelCache = new Map<string, ShapModel | null>();

function getModel(region: string): ShapModel | null {
  if (modelCache.has(region)) return modelCache.get(region)!;

  const modelDir = join(process.cwd(), "..", "model");
  const filePath = join(modelDir, `${region}.json`);

  if (!existsSync(filePath)) {
    modelCache.set(region, null);
    return null;
  }

  const model: ShapModel = JSON.parse(readFileSync(filePath, "utf8"));
  modelCache.set(region, model);
  return model;
}

const TIER_MAP: Record<string, number> = {
  IRON: 1,
  BRONZE: 2,
  SILVER: 3,
  GOLD: 4,
  PLATINUM: 5,
  EMERALD: 6,
  DIAMOND: 7,
  MASTER: 8,
  GRANDMASTER: 8,
  CHALLENGER: 8,
};

/**
 * Extract the feature vector from a match for the primary player.
 * Must match the order in train_xgb.py's build_feature_matrix().
 */
function extractFeatures(
  data: MatchData,
  model: ShapModel
): number[] {
  const ms = data.match.matchSummary;
  const hist = data.match.historicalData;
  const dm = ms.matchDuration / 60;

  // Find primary player in postGameData
  const pgd = hist.postGameData.find(
    (p) =>
      p.riotUserName === ms.riotUserName && p.riotTagLine === ms.riotTagLine
  );

  // Rank lookup
  const rankEntry = data.match.allPlayerRanks?.find(
    (r) =>
      r.riotUserName === ms.riotUserName && r.riotTagLine === ms.riotTagLine
  );
  const soloRank = rankEntry?.rankScores?.find(
    (s) => s.queueType === "ranked_solo_5x5"
  ) ?? rankEntry?.rankScores?.[0];

  // Build feature name → value map
  const fv: Record<string, number> = {};

  // Per-minute rates
  fv["damageTaken_pm"] = (pgd?.damageTaken ?? 0) / dm;
  fv["wardsPlaced_pm"] = (pgd?.wardsPlaced ?? 0) / dm;

  // Raw stats
  fv["visionScoreTotal"] = ms.visionScore ?? 0;

  // Rank
  fv["rank_tier_num"] = soloRank ? (TIER_MAP[soloRank.tier?.toUpperCase()] ?? 4) : 4;

  // Streaks (not available at inference time, use 0)
  fv["win_streak"] = 0;
  fv["loss_streak"] = 0;

  // Champion interactions (label-encoded — use mean at inference since
  // the exact encoding from training isn't available, so SHAP ≈ 0)
  for (let i = 0; i < model.feature_names.length; i++) {
    const name = model.feature_names[i];
    if (name === "Lane Matchup" || name.startsWith("Synergy ")) {
      fv[name] = model.feature_means[i];
    }
  }

  // Build vector in model feature order
  // Map feature display names to column names
  const nameToCol: Record<string, string> = {
    "Dmg Taken/min": "damageTaken_pm",
    "Wards/min": "wardsPlaced_pm",
    "Vision Score": "visionScoreTotal",
    "Rank": "rank_tier_num",
    "Lane Matchup": "Lane Matchup",
  };
  nameToCol["Win Streak"] = "win_streak";
  nameToCol["Loss Streak"] = "loss_streak";
  for (let i = 0; i < 4; i++) {
    nameToCol[`Synergy ${i}`] = `Synergy ${i}`;
  }

  return model.feature_names.map((name, i) => {
    const col = nameToCol[name];
    if (col && col in fv) return fv[col];
    // Fallback: use mean (SHAP = 0)
    return model.feature_means[i];
  });
}

function sigmoid(x: number): number {
  return 1 / (1 + Math.exp(-x));
}

export function computeShapValues(
  data: MatchData,
  regionId: string
): ShapResult | null {
  const model = getModel(regionId);
  if (!model) return null;

  const features = extractFeatures(data, model);
  const { coefficients, feature_means, feature_names, intercept } = model;

  // Linear SHAP: shap_i = coef_i * (x_i - mean_i)
  const shapValues: ShapValue[] = [];
  let logitSum = intercept;

  for (let i = 0; i < coefficients.length; i++) {
    const sv = coefficients[i] * (features[i] - feature_means[i]);
    logitSum += sv;
    shapValues.push({
      feature: feature_names[i],
      value: features[i],
      shapValue: sv,
    });
  }

  // Sort by |shapValue| descending, take top 20
  shapValues.sort((a, b) => Math.abs(b.shapValue) - Math.abs(a.shapValue));

  return {
    baseValue: sigmoid(intercept),
    predictedProbability: sigmoid(logitSum),
    shapValues: shapValues.slice(0, 20),
  };
}
