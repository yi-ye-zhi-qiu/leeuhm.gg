import type { ShapResult } from "@/types/match";

function getTag(win: boolean, pct: number): string {
  if (win) {
    if (pct >= 70) return "Dominant";
    if (pct >= 55) return "Expected";
    return "Surprising";
  } else {
    if (pct <= 30) return "Outclassed";
    if (pct <= 45) return "Expected";
    return "Surprising";
  }
}

const VB_W = 200;
const VB_H = 14;
const TIP = 4;

export function WFactor({
  shap,
  win,
}: {
  shap: ShapResult;
  win: boolean;
}) {
  const pct = Math.round(shap.predictedProbability * 100);
  const tag = getTag(win, pct);

  const top = shap.shapValues.slice(0, 6);

  const helped = top
    .filter((s) => s.shapValue > 0)
    .sort((a, b) => a.shapValue - b.shapValue);
  const hurt = top
    .filter((s) => s.shapValue < 0)
    .sort((a, b) => a.shapValue - b.shapValue);

  const helpedTotal = helped.reduce((s, v) => s + v.shapValue, 0) || 0.01;
  const hurtTotal =
    hurt.reduce((s, v) => s + Math.abs(v.shapValue), 0) || 0.01;

  const meetX = shap.predictedProbability * VB_W;
  const mid = VB_H / 2;

  // Blue arrows — each overlaps the previous by TIP so notch receives tip
  const blueOverlaps = Math.max(0, helped.length - 1) * TIP;
  const blueEffective = meetX + blueOverlaps;

  const bluePolygons: {
    points: string;
    feature: string;
    value: number;
  }[] = [];
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

    bluePolygons.push({
      points,
      feature: helped[i].feature,
      value: helped[i].shapValue,
    });
    bx = x2 - (isLast ? 0 : TIP);
  }

  // Red arrows — mirrored, iterate from rightmost to leftmost
  const redOverlaps = Math.max(0, hurt.length - 1) * TIP;
  const redEffective = VB_W - meetX + redOverlaps;

  const redPolygons: {
    points: string;
    feature: string;
    value: number;
  }[] = [];
  let rx = VB_W;
  for (let i = hurt.length - 1; i >= 0; i--) {
    const w = (Math.abs(hurt[i].shapValue) / hurtTotal) * redEffective;
    const x2 = rx;
    const x1 = x2 - w;
    const isFirst = i === 0; // leftmost red arrow (inner edge, meets blue)
    const isRightmost = i === hurt.length - 1;

    // First red arrow (inner edge) is flat — no pointed tip where it meets blue
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

    redPolygons.push({
      points,
      feature: hurt[i].feature,
      value: hurt[i].shapValue,
    });
    rx = x1 + (isFirst ? 0 : TIP);
  }

  return (
    <div className="flex flex-1 flex-col gap-0.5 min-w-0">
      {/* Percentage — positioned at meeting point, above bar */}
      <div className="relative h-3">
        <span
          className="absolute text-[10px] font-mono font-bold tabular-nums text-muted-foreground whitespace-nowrap"
          style={{
            left: `${pct}%`,
            transform: "translateX(-50%)",
          }}
        >
          {win ? "W" : "L"} {pct}%
        </span>
      </div>

      {/* SVG force bar */}
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        className="h-3.5 w-full"
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
              {a.feature}: +{a.value.toFixed(2)}
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
              {a.feature}: {a.value.toFixed(2)}
            </title>
          </polygon>
        ))}
      </svg>

      {/* Feature labels — only for segments ≥ MIN_LABEL_WIDTH */}
      <CompactLabels
        bluePolygons={bluePolygons}
        redPolygons={redPolygons}
      />

      {/* Tag — positioned at meeting point, below bar */}
      <div className="relative h-3.5">
        <span
          className="absolute rounded-sm border bg-muted/50 px-1 py-px text-[8px] font-medium text-muted-foreground whitespace-nowrap"
          style={{
            left: `${pct}%`,
            transform: "translateX(-50%)",
          }}
        >
          {tag}
        </span>
      </div>
    </div>
  );
}

// 12.5% of the 200-unit viewBox = 25 units
const MIN_LABEL_WIDTH = 25;

type Polygon = { points: string; feature: string; value: number };

function parseSegmentBounds(points: string) {
  const coords = points.split(" ").map((p) => {
    const [x] = p.split(",").map(Number);
    return x;
  });
  const minX = Math.min(...coords);
  const maxX = Math.max(...coords);
  return { minX, maxX, width: maxX - minX };
}

function CompactLabels({
  bluePolygons,
  redPolygons,
}: {
  bluePolygons: Polygon[];
  redPolygons: Polygon[];
}) {
  const labels: { center: number; feature: string }[] = [];

  for (const poly of [...bluePolygons, ...redPolygons]) {
    const { minX, maxX, width } = parseSegmentBounds(poly.points);
    if (width >= MIN_LABEL_WIDTH) {
      labels.push({
        center: ((minX + maxX) / 2 / VB_W) * 100,
        feature: poly.feature,
      });
    }
  }

  if (labels.length === 0) return null;

  return (
    <div className="relative h-3">
      {labels.map((l) => (
        <span
          key={l.feature}
          className="absolute text-[7px] text-muted-foreground whitespace-nowrap"
          style={{
            left: `${l.center}%`,
            transform: "translateX(-50%)",
          }}
        >
          {l.feature}
        </span>
      ))}
    </div>
  );
}
