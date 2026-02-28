"use client";

import { useState } from "react";
import type { ShapResult } from "@/types/match";

const VB_W = 200;
const VB_H = 14;
const TIP = 4;

type Polygon = { points: string; feature: string; value: number; centerPct: number };

export function WFactor({
  shap,
  win,
}: {
  shap: ShapResult;
  win: boolean;
}) {
  const [hovered, setHovered] = useState<string | null>(null);

  const pct = Math.round(shap.predictedProbability * 100);
  const clampedPct = Math.max(10, Math.min(90, pct));

  const top = shap.shapValues.slice(0, 6);

  // Top contributing feature (largest absolute SHAP value)
  const topFeature = top.length > 0
    ? top.reduce((best, s) => Math.abs(s.shapValue) > Math.abs(best.shapValue) ? s : best)
    : null;

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
    const minX = Math.min(...coords);
    const maxX = Math.max(...coords);

    bluePolygons.push({
      points,
      feature: helped[i].feature,
      value: helped[i].shapValue,
      centerPct: ((minX + maxX) / 2 / VB_W) * 100,
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
    const minX = Math.min(...coords);
    const maxX = Math.max(...coords);

    redPolygons.push({
      points,
      feature: hurt[i].feature,
      value: hurt[i].shapValue,
      centerPct: ((minX + maxX) / 2 / VB_W) * 100,
    });
    rx = x1 + (isFirst ? 0 : TIP);
  }

  // Find the hovered polygon to show its label
  const hoveredPoly = hovered
    ? [...bluePolygons, ...redPolygons].find((p) => p.feature === hovered)
    : null;

  return (
    <div className="flex flex-1 flex-col gap-0.5 min-w-0">
      {/* Hovered feature label — positioned above bar */}
      <div className="relative h-3">
        {hoveredPoly && (
          <span
            className="absolute text-[9px] font-medium whitespace-nowrap text-foreground"
            style={{
              left: `${hoveredPoly.centerPct}%`,
              transform: "translateX(-50%)",
            }}
          >
            {hoveredPoly.feature}{" "}
            <span className="text-muted-foreground font-mono">
              {hoveredPoly.value > 0 ? "+" : ""}
              {hoveredPoly.value.toFixed(2)}
            </span>
          </span>
        )}
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
            className={
              hovered === a.feature
                ? "fill-win/80 stroke-white"
                : "fill-win/50 stroke-white"
            }
            strokeWidth={0.4}
            onMouseEnter={() => setHovered(a.feature)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}
        {redPolygons.map((a) => (
          <polygon
            key={a.feature}
            points={a.points}
            className={
              hovered === a.feature
                ? "fill-loss/80 stroke-white"
                : "fill-loss/50 stroke-white"
            }
            strokeWidth={0.4}
            onMouseEnter={() => setHovered(a.feature)}
            onMouseLeave={() => setHovered(null)}
          />
        ))}
      </svg>

      {/* Top feature — positioned at meeting point, below bar */}
      {topFeature && (
        <div className="relative h-3.5">
          <span
            className="absolute rounded-sm border bg-muted/50 px-1 py-px text-[8px] font-medium text-muted-foreground whitespace-nowrap"
            style={{
              left: `${clampedPct}%`,
              transform: "translateX(-50%)",
            }}
          >
            {topFeature.feature}
          </span>
        </div>
      )}
    </div>
  );
}
