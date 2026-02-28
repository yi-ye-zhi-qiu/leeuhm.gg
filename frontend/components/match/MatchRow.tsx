import type { MatchData } from "@/types/match";
import {
  championIconUrl,
  itemIconUrl,
  summonerSpellIconUrl,
  keystoneIconUrl,
  runeStyleIconUrl,
  formatDuration,
  timeAgo,
  kdaRatio,
  queueLabel,
} from "@/lib/game";
import { cn } from "@/lib/utils";
import { WFactor } from "./ShapForcePlot";

export function MatchRow({ data }: { data: MatchData }) {
  const s = data.match.matchSummary;
  const win = s.win;
  const kda = kdaRatio(s.kills, s.deaths, s.assists);
  const totalCs = s.cs + s.jungleCs;
  const csPerMin = (totalCs / (s.matchDuration / 60)).toFixed(1);

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-lg border-l-4 px-3 py-2 transition-colors hover:brightness-95",
        win
          ? "border-l-win bg-win/5"
          : "border-l-loss bg-loss/5"
      )}
    >
      {/* Game info */}
      <div className="flex w-20 shrink-0 flex-col gap-0.5">
        <span className="text-[11px] font-semibold">
          {queueLabel(s.queueType)}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {timeAgo(s.matchCreationTime)}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {formatDuration(s.matchDuration)}
        </span>
        <span
          className={cn(
            "text-[10px] font-bold",
            win ? "text-win" : "text-loss"
          )}
        >
          {win ? "Victory" : "Defeat"}
        </span>
      </div>

      {/* Champion + summoner spells + runes + level */}
      <div className="flex shrink-0 items-center gap-0.5">
        <div className="relative">
          <img
            src={championIconUrl(s.championId)}
            alt=""
            className="h-10 w-10 rounded-full"
          />
          <span className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-neutral-800 text-[9px] font-bold text-white">
            {s.level}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <img
            src={summonerSpellIconUrl(s.summonerSpells[0])}
            alt=""
            className="h-4 w-4 rounded"
          />
          <img
            src={summonerSpellIconUrl(s.summonerSpells[1])}
            alt=""
            className="h-4 w-4 rounded"
          />
        </div>
        <div className="flex flex-col gap-0.5">
          <img
            src={keystoneIconUrl(s.runes[0])}
            alt=""
            className="h-4 w-4 rounded-full"
          />
          <img
            src={runeStyleIconUrl(s.subStyle)}
            alt=""
            className="h-4 w-4 rounded-full"
          />
        </div>
      </div>

      {/* KDA */}
      <div className="flex w-24 shrink-0 flex-col items-center">
        <span className="text-xs font-bold">
          {s.kills} / <span className="text-loss">{s.deaths}</span> /{" "}
          {s.assists}
        </span>
        <span className="text-[10px] text-muted-foreground">{kda} KDA</span>
        <span className="text-[10px] text-muted-foreground">
          P/Kill {s.killParticipation}%
        </span>
      </div>

      {/* CS & Vision */}
      <div className="flex w-16 shrink-0 flex-col items-center">
        <span className="text-[11px]">
          {totalCs} ({csPerMin})
        </span>
        <span className="text-[10px] text-muted-foreground">
          {s.visionScore} vision
        </span>
      </div>

      {/* Items */}
      <div className="flex items-center gap-0.5">
        <div className="grid grid-cols-3 gap-0.5">
          {s.items.slice(0, 6).map((id, i) =>
            id > 0 ? (
              <img
                key={i}
                src={itemIconUrl(id)}
                alt=""
                className="h-6 w-6 rounded"
              />
            ) : (
              <div key={i} className="h-6 w-6 rounded bg-muted" />
            )
          )}
        </div>
        {s.items[6] > 0 ? (
          <img
            src={itemIconUrl(s.items[6])}
            alt=""
            className="ml-0.5 h-6 w-6 rounded-full"
          />
        ) : (
          <div className="ml-0.5 h-6 w-6 rounded-full bg-muted" />
        )}
      </div>

      {/* W-factor */}
      {data.shapValues && (
        <WFactor shap={data.shapValues} win={win} />
      )}

      {/* Teams with names */}
      <div className="ml-auto flex gap-3">
        <div className="flex w-[72px] flex-col gap-px">
          {s.teamA.map((p, i) => (
            <div key={i} className="flex items-center gap-1">
              <img
                src={championIconUrl(p.championId)}
                alt=""
                className="h-3.5 w-3.5 shrink-0 rounded"
              />
              <span
                className={cn(
                  "truncate text-[9px]",
                  p.riotUserName === s.riotUserName
                    ? "font-bold text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {p.riotUserName}
              </span>
            </div>
          ))}
        </div>
        <div className="flex w-[72px] flex-col gap-px">
          {s.teamB.map((p, i) => (
            <div key={i} className="flex items-center gap-1">
              <img
                src={championIconUrl(p.championId)}
                alt=""
                className="h-3.5 w-3.5 shrink-0 rounded"
              />
              <span
                className={cn(
                  "truncate text-[9px]",
                  p.riotUserName === s.riotUserName
                    ? "font-bold text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {p.riotUserName}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
