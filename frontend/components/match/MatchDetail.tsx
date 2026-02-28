import type { MatchData, PostGameData, TeamOverview } from "@/types/match";
import { ShapForcePlotExpanded } from "./ShapForcePlotExpanded";
import {
  championIconUrl,
  itemIconUrl,
  summonerSpellIconUrl,
  keystoneIconUrl,
  runeStyleIconUrl,
  formatGold,
} from "@/lib/game";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export function MatchDetail({ data }: { data: MatchData }) {
  const { postGameData, teamOneOverview, teamTwoOverview } =
    data.match.historicalData;
  const team1 = postGameData.filter((p) => p.teamId === 100);
  const team2 = postGameData.filter((p) => p.teamId === 200);
  const winTeam = data.match.winningTeam;

  const maxDamage = Math.max(...postGameData.map((p) => p.damage));

  function getRank(userName: string, tagLine: string) {
    const r = data.match.allPlayerRanks.find(
      (r) => r.riotUserName === userName && r.riotTagLine === tagLine
    );
    if (!r?.rankScores.length) return null;
    return (
      r.rankScores.find((s) => s.queueType === "ranked_solo_5x5") ??
      r.rankScores[0]
    );
  }

  return (
    <div className="mt-1 rounded-lg border bg-card p-3">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-24" />
            <TableHead>Player</TableHead>
            <TableHead className="text-center">KDA</TableHead>
            <TableHead className="w-44">Damage</TableHead>
            <TableHead className="text-right">Gold</TableHead>
            <TableHead className="text-right">CS</TableHead>
            <TableHead className="text-right">Wards</TableHead>
            <TableHead>Items</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell
              colSpan={8}
              className="bg-win/10 py-1 text-xs font-semibold text-win"
            >
              Blue Team {winTeam === 100 ? "(Victory)" : "(Defeat)"}
            </TableCell>
          </TableRow>
          {team1.map((p) => (
            <PlayerRow
              key={`${p.riotUserName}#${p.riotTagLine}`}
              player={p}
              rank={getRank(p.riotUserName, p.riotTagLine)}
              maxDamage={maxDamage}
            />
          ))}

          <TeamSeparator
            blue={teamOneOverview}
            red={teamTwoOverview}
            blueWin={winTeam === 100}
          />

          <TableRow>
            <TableCell
              colSpan={8}
              className="bg-loss/10 py-1 text-xs font-semibold text-loss"
            >
              Red Team {winTeam === 200 ? "(Victory)" : "(Defeat)"}
            </TableCell>
          </TableRow>
          {team2.map((p) => (
            <PlayerRow
              key={`${p.riotUserName}#${p.riotTagLine}`}
              player={p}
              rank={getRank(p.riotUserName, p.riotTagLine)}
              maxDamage={maxDamage}
            />
          ))}
        </TableBody>
      </Table>
      {data.shapValues && (
        <ShapForcePlotExpanded
          shap={data.shapValues}
          win={data.match.matchSummary.win}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Team Separator                                                     */
/* ------------------------------------------------------------------ */

function ObjectiveIcon({
  label,
  blueVal,
  redVal,
}: {
  label: string;
  blueVal: number;
  redVal: number;
}) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <div className="flex items-center gap-1.5 text-xs font-semibold">
        <span className="text-win">{blueVal}</span>
        <span className="text-muted-foreground">/</span>
        <span className="text-loss">{redVal}</span>
      </div>
    </div>
  );
}

function DualBar({
  label,
  blueVal,
  redVal,
}: {
  label: string;
  blueVal: number;
  redVal: number;
}) {
  const total = blueVal + redVal;
  const bluePct = total > 0 ? (blueVal / total) * 100 : 50;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs font-semibold">
        <span className="text-win">{formatGold(blueVal)}</span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <span className="text-loss">{formatGold(redVal)}</span>
      </div>
      <div className="flex h-2 w-full overflow-hidden rounded-full">
        <div
          className="h-full bg-win transition-all"
          style={{ width: `${bluePct}%` }}
        />
        <div className="h-full flex-1 bg-loss" />
      </div>
    </div>
  );
}

function TeamSeparator({
  blue,
  red,
  blueWin,
}: {
  blue: TeamOverview;
  red: TeamOverview;
  blueWin: boolean;
}) {
  return (
    <TableRow>
      <TableCell colSpan={8} className="py-4">
        <div className="mx-auto flex max-w-lg flex-col gap-2">
          {/* Objective icons */}
          <div className="flex items-center justify-center gap-6">
            <ObjectiveIcon
              label="Baron"
              blueVal={blue.baronKills}
              redVal={red.baronKills}
            />
            <ObjectiveIcon
              label="Dragon"
              blueVal={blue.dragonKills}
              redVal={red.dragonKills}
            />
            <ObjectiveIcon
              label="Tower"
              blueVal={blue.towerKills}
              redVal={red.towerKills}
            />
            <ObjectiveIcon
              label="Herald"
              blueVal={blue.riftHeraldKills}
              redVal={red.riftHeraldKills}
            />
            <ObjectiveIcon
              label="Inhibitor"
              blueVal={blue.inhibitorKills}
              redVal={red.inhibitorKills}
            />
          </div>

          {/* Kills & Gold bars */}
          <div className="flex flex-col gap-2">
            <DualBar
              label="Kills"
              blueVal={blue.kills}
              redVal={red.kills}
            />
            <DualBar
              label="Gold"
              blueVal={blue.gold}
              redVal={red.gold}
            />
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
}

/* ------------------------------------------------------------------ */
/*  Damage Bar                                                         */
/* ------------------------------------------------------------------ */

function DamageBar({
  value,
  max,
  color,
}: {
  value: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex flex-col gap-0.5">
      <div className="h-2 w-full rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-muted-foreground">
        {formatGold(value)}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Player Row                                                         */
/* ------------------------------------------------------------------ */

function PlayerRow({
  player: p,
  rank,
  maxDamage,
}: {
  player: PostGameData;
  rank: { tier: string; rank: string; lp: number } | null;
  maxDamage: number;
}) {
  return (
    <TableRow>
      <TableCell className="py-1.5">
        <div className="flex items-center gap-1">
          <div className="relative shrink-0">
            <img
              src={championIconUrl(p.championId)}
              alt=""
              className="h-9 w-9 rounded"
            />
            <span className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-neutral-800 text-[8px] font-bold text-white">
              {p.level}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <img
              src={summonerSpellIconUrl(p.summonerSpells[0])}
              alt=""
              className="h-4 w-4 rounded"
            />
            <img
              src={summonerSpellIconUrl(p.summonerSpells[1])}
              alt=""
              className="h-4 w-4 rounded"
            />
          </div>
          <div className="flex flex-col gap-0.5">
            <img
              src={keystoneIconUrl(p.keystone)}
              alt=""
              className="h-4 w-4 rounded-full"
            />
            <img
              src={runeStyleIconUrl(p.subStyle)}
              alt=""
              className="h-4 w-4 rounded-full"
            />
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="flex flex-col">
          <span className="text-xs font-medium">
            {p.riotUserName}
            <span className="text-muted-foreground">#{p.riotTagLine}</span>
          </span>
          <span className="text-[10px] text-muted-foreground">
            {rank ? `${rank.tier} ${rank.rank} ${rank.lp}LP` : "Unranked"}
          </span>
        </div>
      </TableCell>
      <TableCell className="text-center text-xs">
        {p.kills}/{p.deaths}/{p.assists}
      </TableCell>
      <TableCell>
        <DamageBar value={p.damage} max={maxDamage} color="bg-loss" />
      </TableCell>
      <TableCell className="text-right text-xs">
        {formatGold(p.gold)}
      </TableCell>
      <TableCell className="text-right text-xs">{p.cs + p.jungleCs}</TableCell>
      <TableCell className="text-right text-xs">{p.wardsPlaced}</TableCell>
      <TableCell>
        <div className="flex gap-0.5">
          {p.items.slice(0, 6).map((id, i) =>
            id > 0 ? (
              <img
                key={i}
                src={itemIconUrl(id)}
                alt=""
                className="h-5 w-5 rounded"
              />
            ) : (
              <div key={i} className="h-5 w-5 rounded bg-muted" />
            )
          )}
          {p.items[6] > 0 && (
            <img
              src={itemIconUrl(p.items[6])}
              alt=""
              className="ml-0.5 h-5 w-5 rounded-full"
            />
          )}
        </div>
      </TableCell>
    </TableRow>
  );
}
