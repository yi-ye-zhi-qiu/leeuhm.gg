import { readFileSync, existsSync } from "fs";
import { join } from "path";
import type { ShapResult, ShapValue } from "@/types/match";

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

// Phase classification matching train.py: early <25%, mid 25-50%, late >50%
function phase(timestampMs: number, durationSec: number): 1 | 2 | 3 {
  if (timestampMs < durationSec * 250) return 1;
  if (timestampMs < durationSec * 500) return 2;
  return 3;
}

interface DiffFrame {
  timestamp?: number;
  youValue?: number;
  oppValue?: number;
}

function phaseAvg(frames: DiffFrame[] | null | undefined, durationSec: number): [number, number, number] {
  if (!frames || frames.length === 0) return [0, 0, 0];
  const buckets: [number[], number[], number[]] = [[], [], []];
  for (const f of frames) {
    const ts = f.timestamp ?? 0;
    const p = phase(ts, durationSec);
    const diff = (f.youValue ?? 0) - (f.oppValue ?? 0);
    buckets[p - 1].push(diff);
  }
  return buckets.map(b => b.length > 0 ? b.reduce((a, v) => a + v, 0) / b.length : 0) as [number, number, number];
}

/**
 * Extract features from the raw API blob (before slim() strips timelineData).
 * Mirrors the Python feature extraction in db/scripts/features.py.
 */
function extractFeatures(
  raw: any,
  model: ShapModel
): number[] {
  const m = raw.data.match;
  const summary = m.matchSummary;
  const hist = m.historicalData;
  const durationSec = summary.matchDuration;
  const primaryName = summary.riotUserName;
  const primaryTag = summary.riotTagLine;

  // Find primary player in postGameData
  const pgd = (hist.postGameData ?? []).find(
    (p: any) => p.riotUserName === primaryName && p.riotTagLine === primaryTag
  );

  // Timeline data
  const timeline: any[] = hist.timelineData ?? [];

  // Extract phase kills/deaths for primary player
  const phaseCounts: Record<string, number> = {
    early_kills: 0, mid_kills: 0, late_kills: 0,
    early_deaths: 0, mid_deaths: 0, late_deaths: 0,
  };
  for (const e of timeline) {
    if (e.eventType !== "champion_kill") continue;
    const ts = e.timestamp ?? 0;
    const p = phase(ts, durationSec);
    const phaseName = p === 1 ? "early" : p === 2 ? "mid" : "late";
    if (e.riotUserName === primaryName && e.riotTagLine === primaryTag) {
      phaseCounts[`${phaseName}_kills`]++;
    }
    if (e.victimRiotUserName === primaryName && e.victimRiotTagLine === primaryTag) {
      phaseCounts[`${phaseName}_deaths`]++;
    }
  }

  // Extract teamfights per phase (15s windows with 2+ kills)
  const buckets: Record<number, number> = {};
  for (const e of timeline) {
    if (e.eventType !== "champion_kill") continue;
    const bucket = Math.floor((e.timestamp ?? 0) / 15000);
    buckets[bucket] = (buckets[bucket] ?? 0) + 1;
  }
  const teamfights: Record<string, number> = {
    early_teamfights: 0, mid_teamfights: 0, late_teamfights: 0,
  };
  for (const [bucket, count] of Object.entries(buckets)) {
    if (count >= 2) {
      const ts = Number(bucket) * 15000;
      const p = phase(ts, durationSec);
      const phaseName = p === 1 ? "early" : p === 2 ? "mid" : "late";
      teamfights[`${phaseName}_teamfights`]++;
    }
  }

  // Gold and KA diff frames (primary player only)
  const goldDiff = phaseAvg(hist.goldDifferenceFrames, durationSec);
  const kaDiff = phaseAvg(hist.kaDifferenceFrames, durationSec);

  // Build feature value map
  const fv: Record<string, number> = {
    // Streaks (not available at inference time)
    win_streak: 0,
    loss_streak: 0,
    // Phase kills/deaths
    ...phaseCounts,
    // Gold diffs
    gold_diff_early: goldDiff[0],
    gold_diff_mid: goldDiff[1],
    gold_diff_late: goldDiff[2],
    // KA diffs
    ka_diff_early: kaDiff[0],
    ka_diff_mid: kaDiff[1],
    ka_diff_late: kaDiff[2],
    // Teamfights
    ...teamfights,
  };

  // Champion interactions — use mean (SHAP ≈ 0)
  for (let i = 0; i < model.feature_names.length; i++) {
    const name = model.feature_names[i];
    if (name === "Lane Matchup" || name.startsWith("Synergy ")) {
      fv[name] = model.feature_means[i];
    }
  }

  // Map display names to fv keys
  const nameToCol: Record<string, string> = {
    "Win Streak": "win_streak",
    "Loss Streak": "loss_streak",
    "Early Kills": "early_kills",
    "Mid Kills": "mid_kills",
    "Late Kills": "late_kills",
    "Early Deaths": "early_deaths",
    "Mid Deaths": "mid_deaths",
    "Late Deaths": "late_deaths",
    "Gold Diff Early": "gold_diff_early",
    "Gold Diff Mid": "gold_diff_mid",
    "Gold Diff Late": "gold_diff_late",
    "KA Diff Early": "ka_diff_early",
    "KA Diff Mid": "ka_diff_mid",
    "KA Diff Late": "ka_diff_late",
    "Early Teamfights": "early_teamfights",
    "Mid Teamfights": "mid_teamfights",
    "Late Teamfights": "late_teamfights",
    "Lane Matchup": "Lane Matchup",
  };
  for (let i = 0; i < 4; i++) {
    nameToCol[`Synergy ${i}`] = `Synergy ${i}`;
  }

  return model.feature_names.map((name, i) => {
    const col = nameToCol[name];
    if (col && col in fv) return fv[col];
    return model.feature_means[i];
  });
}

function sigmoid(x: number): number {
  return 1 / (1 + Math.exp(-x));
}

/**
 * Compute SHAP values from the raw API blob (before slim()).
 * Must be called with the full document that includes timelineData.
 */
export function computeShapValues(
  raw: any,
  regionId: string
): ShapResult | null {
  const model = getModel(regionId);
  if (!model) return null;

  let features: number[];
  try {
    features = extractFeatures(raw, model);
  } catch {
    return null;
  }
  const { coefficients, feature_means, feature_names, intercept } = model;

  // Linear SHAP: shap_i = coef_i * (x_i - mean_i)
  const shapValues: ShapValue[] = [];
  let logitSum = intercept;

  for (let i = 0; i < coefficients.length; i++) {
    const fi = Number.isFinite(features[i]) ? features[i] : feature_means[i];
    const sv = coefficients[i] * (fi - feature_means[i]);
    logitSum += sv;
    shapValues.push({
      feature: feature_names[i],
      value: fi,
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
