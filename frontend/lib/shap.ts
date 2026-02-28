import { readFileSync, existsSync } from "fs";
import { join } from "path";
import type { ShapResult } from "@/types/match";

interface ShapLookup {
  [matchId: string]: {
    [playerKey: string]: ShapResult;
  };
}

// Cache loaded SHAP lookups in memory
const shapCache = new Map<string, ShapLookup | null>();

function getShapLookup(region: string): ShapLookup | null {
  if (shapCache.has(region)) return shapCache.get(region)!;

  const modelDir = join(process.cwd(), "..", "model");
  const filePath = join(modelDir, `${region}_shap.json`);

  if (!existsSync(filePath)) {
    shapCache.set(region, null);
    return null;
  }

  const lookup: ShapLookup = JSON.parse(readFileSync(filePath, "utf8"));
  shapCache.set(region, lookup);
  return lookup;
}

export function lookupShapValues(
  matchId: string,
  playerKey: string,
  regionId: string
): ShapResult | null {
  const lookup = getShapLookup(regionId);
  if (!lookup) return null;

  return lookup[matchId]?.[playerKey] ?? null;
}
