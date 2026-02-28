import type { ShapResult } from "@/types/match";

const VB_W = 400;
const VB_H = 20;
const TIP = 5;

type Polygon = {
  points: string;
  feature: string;
  value: number;
  minX: number;
  maxX: number;
};

function buildPolygons(shap: ShapResult): {
  bluePolygons: Polygon[];
  redPolygons: Polygon[];
} {
  const all = shap.shapValues;

  const helped = all
    .filter((s) => s.shapValue > 0)
    .sort((a, b) => a.shapValue - b.shapValue);
  const hurt = all
    .filter((s) => s.shapValue < 0)
    .sort((a, b) => a.shapValue - b.shapValue);

  const helpedTotal = helped.reduce((s, v) => s + v.shapValue, 0) || 0.01;
  const hurtTotal =
    hurt.reduce((s, v) => s + Math.abs(v.shapValue), 0) || 0.01;

  const meetX = shap.predictedProbability * VB_W;
  const mid = VB_H / 2;

  // Blue arrows
  const blueOverlaps = Math.max(0, helped.length - 1) * TIP;
  const blueEffective = meetX + blueOverlaps;

  const bluePolygons: Polygon[] = [];
  let bx = 0;
  for (let i = 0; i < helped.length; i++) {
    const w = (helped[i].shapValue / helpedTotal) * blueEffective;
    const x1 = bx;
    const x2 = x1 + w;
    const isFirst = i === 0;
    const isLast = i === helped.length - 1;

    let points: string;
    if (isFirst && isLast) {
      points = `${x1},0 ${x2},0 ${x2},${VB_H} ${x1},${VB_H}`;
    } else if (isFirst) {
      points = `${x1},0 ${x2 - TIP},0 ${x2},${mid} ${x2 - TIP},${VB_H} ${x1},${VB_H}`;
    } else if (isLast) {
      points = `${x1},0 ${x2},0 ${x2},${VB_H} ${x1},${VB_H} ${x1 + TIP},${mid}`;
    } else {
      points = `${x1},0 ${x2 - TIP},0 ${x2},${mid} ${x2 - TIP},${VB_H} ${x1},${VB_H} ${x1 + TIP},${mid}`;
    }

    const coords = points.split(" ").map((p) => Number(p.split(",")[0]));
    bluePolygons.push({
      points,
      feature: helped[i].feature,
      value: helped[i].shapValue,
      minX: Math.min(...coords),
      maxX: Math.max(...coords),
    });
    bx = x2 - (isLast ? 0 : TIP);
  }

  // Red arrows
  const redOverlaps = Math.max(0, hurt.length - 1) * TIP;
  const redEffective = VB_W - meetX + redOverlaps;

  const redPolygons: Polygon[] = [];
  let rx = VB_W;
  for (let i = hurt.length - 1; i >= 0; i--) {
    const w = (Math.abs(hurt[i].shapValue) / hurtTotal) * redEffective;
    const x2 = rx;
    const x1 = x2 - w;
    const isFirst = i === 0;
    const isRightmost = i === hurt.length - 1;

    let points: string;
    if (isFirst && isRightmost) {
      points = `${x1},0 ${x2},0 ${x2},${VB_H} ${x1},${VB_H}`;
    } else if (isFirst) {
      points = `${x1},0 ${x2},0 ${x2 - TIP},${mid} ${x2},${VB_H} ${x1},${VB_H}`;
    } else if (isRightmost) {
      points = `${x1 + TIP},0 ${x2},0 ${x2},${VB_H} ${x1 + TIP},${VB_H} ${x1},${mid}`;
    } else {
      points = `${x1 + TIP},0 ${x2},0 ${x2 - TIP},${mid} ${x2},${VB_H} ${x1 + TIP},${VB_H} ${x1},${mid}`;
    }

    const coords = points.split(" ").map((p) => Number(p.split(",")[0]));
    redPolygons.push({
      points,
      feature: hurt[i].feature,
      value: hurt[i].shapValue,
      minX: Math.min(...coords),
      maxX: Math.max(...coords),
    });
    rx = x1 + (isFirst ? 0 : TIP);
  }

  return { bluePolygons, redPolygons };
}

interface LabelEntry {
  centerPct: number;
  displayPct: number;
  feature: string;
  value: number;
  row: "above" | "below";
  needsLeader: boolean;
  isBlue: boolean;
}

// Minimum gap in percentage points between adjacent labels on the same row
const MIN_GAP = 6;

function layoutLabels(polygons: Polygon[], isBlue: boolean): LabelEntry[] {
  const entries = polygons.map((p) => ({
    centerPct: ((p.minX + p.maxX) / 2 / VB_W) * 100,
    feature: p.feature,
    value: p.value,
    width: p.maxX - p.minX,
    isBlue,
  }));

  // Sort by center position left-to-right
  entries.sort((a, b) => a.centerPct - b.centerPct);

  const labels: LabelEntry[] = [];
  let lastBelow = -Infinity;
  let lastAbove = -Infinity;

  for (const e of entries) {
    let row: "above" | "below";
    let displayPct = e.centerPct;
    let needsLeader = false;

    if (e.centerPct - lastBelow >= MIN_GAP) {
      row = "below";
      lastBelow = e.centerPct;
    } else if (e.centerPct - lastAbove >= MIN_GAP) {
      row = "above";
      lastAbove = e.centerPct;
    } else {
      // Both rows overlap — nudge position
      row = "above";
      displayPct = lastAbove + MIN_GAP;
      lastAbove = displayPct;
      needsLeader = true;
    }

    labels.push({
      centerPct: e.centerPct,
      displayPct,
      feature: e.feature,
      value: e.value,
      row,
      needsLeader,
      isBlue: e.isBlue,
    });
  }

  return labels;
}

export function ShapForcePlotExpanded({
  shap,
  win,
}: {
  shap: ShapResult;
  win: boolean;
}) {
  const pct = Math.round(shap.predictedProbability * 100);
  const { bluePolygons, redPolygons } = buildPolygons(shap);

  const labels = [
    ...layoutLabels(bluePolygons, true),
    ...layoutLabels(redPolygons, false),
  ];

  const aboveLabels = labels.filter((l) => l.row === "above");
  const belowLabels = labels.filter((l) => l.row === "below");

  return (
    <div className="mt-4 rounded-lg border bg-card p-4">
      <div className="mb-2 text-xs font-medium text-muted-foreground">
        Win Probability Breakdown — All Features
      </div>
      <div className="flex flex-col gap-0">
        {/* Percentage above */}
        <div className="relative h-4">
          <span
            className="absolute text-xs font-mono font-bold tabular-nums text-muted-foreground whitespace-nowrap"
            style={{
              left: `${pct}%`,
              transform: "translateX(-50%)",
            }}
          >
            {win ? "W" : "L"} {pct}%
          </span>
        </div>

        {/* Above-bar labels */}
        <div className="relative h-5">
          {aboveLabels.map((l) => (
            <span
              key={l.feature}
              className={`absolute text-[8px] whitespace-nowrap ${l.needsLeader ? "rotate-[-45deg] origin-bottom-left" : ""} ${l.isBlue ? "text-win" : "text-loss"}`}
              style={{
                left: `${l.displayPct}%`,
                transform: l.needsLeader
                  ? undefined
                  : "translateX(-50%)",
                bottom: 0,
              }}
            >
              {l.feature}
            </span>
          ))}
        </div>

        {/* Leader lines (above) rendered in SVG overlay */}
        {aboveLabels.some((l) => l.needsLeader) && (
          <svg className="w-full h-2" viewBox={`0 0 100 8`} preserveAspectRatio="none">
            {aboveLabels
              .filter((l) => l.needsLeader)
              .map((l) => (
                <line
                  key={l.feature}
                  x1={l.centerPct}
                  y1={8}
                  x2={l.displayPct}
                  y2={0}
                  className="stroke-muted-foreground/40"
                  strokeWidth={0.3}
                />
              ))}
          </svg>
        )}

        {/* SVG force bar */}
        <svg
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          className="h-5 w-full"
          preserveAspectRatio="none"
        >
          {bluePolygons.map((a) => (
            <polygon
              key={a.feature}
              points={a.points}
              className="fill-win/50 stroke-white"
              strokeWidth={0.4}
            >
              <title>
                {a.feature}: +{a.value.toFixed(3)}
              </title>
            </polygon>
          ))}
          {redPolygons.map((a) => (
            <polygon
              key={a.feature}
              points={a.points}
              className="fill-loss/50 stroke-white"
              strokeWidth={0.4}
            >
              <title>
                {a.feature}: {a.value.toFixed(3)}
              </title>
            </polygon>
          ))}
        </svg>

        {/* Leader lines (below) */}
        {belowLabels.some((l) => l.needsLeader) && (
          <svg className="w-full h-2" viewBox="0 0 100 8" preserveAspectRatio="none">
            {belowLabels
              .filter((l) => l.needsLeader)
              .map((l) => (
                <line
                  key={l.feature}
                  x1={l.centerPct}
                  y1={0}
                  x2={l.displayPct}
                  y2={8}
                  className="stroke-muted-foreground/40"
                  strokeWidth={0.3}
                />
              ))}
          </svg>
        )}

        {/* Below-bar labels */}
        <div className="relative h-5">
          {belowLabels.map((l) => (
            <span
              key={l.feature}
              className={`absolute text-[8px] whitespace-nowrap ${l.needsLeader ? "rotate-[45deg] origin-top-left" : ""} ${l.isBlue ? "text-win" : "text-loss"}`}
              style={{
                left: `${l.displayPct}%`,
                transform: l.needsLeader
                  ? undefined
                  : "translateX(-50%)",
                top: 0,
              }}
            >
              {l.feature}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
