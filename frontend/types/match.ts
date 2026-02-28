export interface TeamOverview {
  baronKills: number;
  dragonKills: number;
  towerKills: number;
  riftHeraldKills: number;
  inhibitorKills: number;
  kills: number;
  gold: number;
  bans: number[];
}

export interface MatchData {
  match: {
    matchSummary: MatchSummary;
    historicalData: {
      matchId: string;
      postGameData: PostGameData[];
      teamOneOverview: TeamOverview;
      teamTwoOverview: TeamOverview;
    };
    allPlayerRanks: PlayerRank[];
    playerInfo: PlayerInfo;
    winningTeam: number;
  };
  shapValues?: ShapResult;
}

export interface MatchSummary {
  win: boolean;
  championId: number;
  kills: number;
  deaths: number;
  assists: number;
  cs: number;
  jungleCs: number;
  gold: number;
  level: number;
  items: number[];
  runes: number[];
  summonerSpells: number[];
  matchDuration: number;
  matchCreationTime: number;
  matchId: number;
  regionId: string;
  queueType: string;
  visionScore: number;
  damage: number;
  role: number;
  killParticipation: number;
  primaryStyle: number;
  subStyle: number;
  version: string;
  maximumKillStreak: number;
  riotUserName: string;
  riotTagLine: string;
  teamA: TeamMember[];
  teamB: TeamMember[];
  lpInfo: {
    lp: number;
    placement: number;
  };
}

export interface TeamMember {
  championId: number;
  riotUserName: string;
  riotTagLine: string;
  role: number;
  teamId: number;
}

export interface PostGameData {
  championId: number;
  riotUserName: string;
  riotTagLine: string;
  kills: number;
  deaths: number;
  assists: number;
  cs: number;
  jungleCs: number;
  damage: number;
  damageTaken: number;
  gold: number;
  level: number;
  items: number[];
  summonerSpells: number[];
  keystone: number;
  subStyle: number;
  role: number;
  teamId: number;
  wardsPlaced: number;
  carryPercentage: number;
}

export interface PlayerRank {
  riotUserName: string;
  riotTagLine: string;
  rankScores: {
    tier: string;
    rank: string;
    lp: number;
    wins: number;
    losses: number;
    queueType: string;
  }[];
}

export interface PlayerInfo {
  riotUserName: string;
  riotTagLine: string;
  regionId: string;
  summonerLevel: number;
  iconId: number;
}

export interface ShapValue {
  feature: string;
  value: number;
  shapValue: number;
}

export interface ShapResult {
  baseValue: number;
  predictedProbability: number;
  shapValues: ShapValue[];
}
