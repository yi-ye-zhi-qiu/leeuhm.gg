import type { ShapResult } from "@/types/match";

export function ShapForcePlotExpanded({
  shap,
}: {
  shap: ShapResult;
}) {
  const sorted = [...shap.shapValues].sort(
    (a, b) => b.shapValue - a.shapValue
  );

  const maxAbs = Math.max(...sorted.map((s) => Math.abs(s.shapValue)), 0.01);

  return (
    <div className="mt-4 rounded-lg border bg-card p-4">
      <div className="mb-3">
        <span className="text-xs font-medium text-muted-foreground">
          Win Probability Breakdown
        </span>
      </div>

      <div className="space-y-1.5">
        {sorted.map((s) => {
          const isPositive = s.shapValue > 0;
          const widthPct = (Math.abs(s.shapValue) / maxAbs) * 100;

          return (
            <div key={s.feature} className="flex items-center gap-2 text-xs">
              <span className="w-28 shrink-0 truncate text-right text-muted-foreground">
                {s.feature}
              </span>
              <div className="relative flex h-4 flex-1 items-center">
                {/* Center line */}
                <div className="absolute left-1/2 h-full w-px bg-border" />
                {/* Bar */}
                <div
                  className={`absolute h-3 rounded-sm ${
                    isPositive ? "bg-win/60" : "bg-loss/60"
                  }`}
                  style={{
                    width: `${widthPct / 2}%`,
                    ...(isPositive
                      ? { left: "50%" }
                      : { right: "50%" }),
                  }}
                />
              </div>
              <span
                className={`w-12 shrink-0 text-right font-mono tabular-nums ${
                  isPositive ? "text-win" : "text-loss"
                }`}
              >
                {isPositive ? "+" : ""}
                {s.shapValue.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
