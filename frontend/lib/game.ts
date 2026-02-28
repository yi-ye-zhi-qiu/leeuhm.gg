const CDRAGON =
  "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default";

export function championIconUrl(id: number): string {
  return `${CDRAGON}/v1/champion-icons/${id}.png`;
}

export function itemIconUrl(id: number): string {
  if (id === 0) return "";
  return `https://ddragon.leagueoflegends.com/cdn/16.3.1/img/item/${id}.png`;
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

export function timeAgo(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "just now";
}

export function kdaRatio(k: number, d: number, a: number): string {
  if (d === 0) return "Perfect";
  return ((k + a) / d).toFixed(2);
}

export function queueLabel(qt: string): string {
  const map: Record<string, string> = {
    ranked_solo_5x5: "Ranked Solo",
    ranked_flex_sr: "Ranked Flex",
    normal_draft_5x5: "Normal",
  };
  return map[qt] ?? qt;
}

export function formatGold(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

const SPELL_MAP: Record<number, string> = {
  1: "SummonerBoost",
  3: "SummonerExhaust",
  4: "SummonerFlash",
  6: "SummonerHaste",
  7: "SummonerHeal",
  11: "SummonerSmite",
  12: "SummonerTeleport",
  13: "SummonerMana",
  14: "SummonerDot",
  21: "SummonerBarrier",
  32: "SummonerSnowball",
};

export function summonerSpellIconUrl(id: number): string {
  const name = SPELL_MAP[id] ?? "SummonerFlash";
  return `https://ddragon.leagueoflegends.com/cdn/16.3.1/img/spell/${name}.png`;
}

const RUNE_PATH: Record<number, string> = {
  // Precision
  8005: "perk-images/Styles/Precision/PressTheAttack/PressTheAttack.png",
  8008: "perk-images/Styles/Precision/LethalTempo/LethalTempoTemp.png",
  8021: "perk-images/Styles/Precision/FleetFootwork/FleetFootwork.png",
  8010: "perk-images/Styles/Precision/Conqueror/Conqueror.png",
  // Domination
  8112: "perk-images/Styles/Domination/Electrocute/Electrocute.png",
  8124: "perk-images/Styles/Domination/Predator/Predator.png",
  8128: "perk-images/Styles/Domination/DarkHarvest/DarkHarvest.png",
  9923: "perk-images/Styles/Domination/HailOfBlades/HailOfBlades.png",
  // Sorcery
  8214: "perk-images/Styles/Sorcery/SummonAery/SummonAery.png",
  8229: "perk-images/Styles/Sorcery/ArcaneComet/ArcaneComet.png",
  8230: "perk-images/Styles/Sorcery/PhaseRush/PhaseRush.png",
  // Resolve
  8437: "perk-images/Styles/Resolve/GraspOfTheUndying/GraspOfTheUndying.png",
  8439: "perk-images/Styles/Resolve/VeteranAftershock/VeteranAftershock.png",
  8465: "perk-images/Styles/Resolve/Guardian/Guardian.png",
  // Inspiration
  8351: "perk-images/Styles/Inspiration/GlacialAugment/GlacialAugment.png",
  8360: "perk-images/Styles/Inspiration/UnsealedSpellbook/UnsealedSpellbook.png",
  8369: "perk-images/Styles/Inspiration/FirstStrike/FirstStrike.png",
};

const STYLE_PATH: Record<number, string> = {
  8000: "perk-images/Styles/7201_Precision.png",
  8100: "perk-images/Styles/7200_Domination.png",
  8200: "perk-images/Styles/7202_Sorcery.png",
  8300: "perk-images/Styles/7203_Whimsy.png",
  8400: "perk-images/Styles/7204_Resolve.png",
};

const DDRAGON_RUNE = "https://ddragon.leagueoflegends.com/cdn/img";

export function keystoneIconUrl(id: number): string {
  const path = RUNE_PATH[id];
  if (!path) return `${DDRAGON_RUNE}/perk-images/Styles/7201_Precision.png`;
  return `${DDRAGON_RUNE}/${path}`;
}

export function runeStyleIconUrl(id: number): string {
  const path = STYLE_PATH[id];
  if (!path) return `${DDRAGON_RUNE}/perk-images/Styles/7201_Precision.png`;
  return `${DDRAGON_RUNE}/${path}`;
}
