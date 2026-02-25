import os
from typing import Iterable, Literal, Optional
from urllib.parse import urlunparse
from scrapy import Spider
from scrapy.http import JsonRequest, Response
from scrapy.utils.reactor import is_asyncio_reactor_installed
from crawl.utils.datatypes import URLComponents

QUEUE_TYPE = 420  # 5v5 Summoner's rift


class CrawlGameData(Spider):
    """
    A spider class to crawl UGG leaderboards and the top 20 games
    from each player. This will enable downstream crawl of game
    data.

    You can model the volume of games returned as n_pages * 100 * 20 * 10.
    This is because there are 100 players per page, 20 games per player,
    and 10 players per game. This assumes uniqueness across games and players.
    This is not the case! So, you'll likely end up with some fraction
    of that estimated volume.

    Please invoke the spider with the `REGION` and `TIER` spider arguments.

    `scrapy crawl teemo -a REGION=euw`

    # TODO: support tier selection ... u.gg can't do this ;[
    :param TIER: optional, the tier to crawl leaderboards
       from.  Possible values: challenger, grandmaster,
       master, diamond, emerald, platinum, gold, silver,
       bronze, iron. If no value is provided, defaults
       to None and is just the top X players.

    :param REGION: the region to crawl leaderboards from,
       possible values: euw, na, kr

    :param N_LEADERBOARD_PAGES: int value of how many leaderboard
       pages to scrape, has no max

    :param N_USER_ITER: int value of how many API requests to make
       per user; each iteration returns 20 more games, has no max
       though the API will time out eventually as OP.gg does not
       store user data for all time
    """

    name = "teemo"
    _version = "0.0.0"

    def __init__(
        self,
        REGION: Literal["na", "euw", "kr"],  # eun, oce, ...
        N_LEADERBOARD_PAGES: Optional[int] = 7500,  # This goes to Bronze 1 about
        N_USER_ITER: Optional[int] = 1,
        *args,
        **kwargs,
    ) -> None:
        # Check for correct asyncio reactor (allows JA3/Fingerprint impersonation)
        if not is_asyncio_reactor_installed():
            raise ValueError(
                f"{CrawlGameData.__qualname__} requires the asyncio Twisted "
                f"reactor. Make sure you have it configured in the "
                f"TWISTED_REACTOR setting. See the asyncio documentation "
                f"of Scrapy for more information."
            )
        super(CrawlGameData, self).__init__(*args, **kwargs)
        # Used in api function call
        self.region = REGION
        # Folder to partition by azure://data/euw/challenger/...
        # in the case of a null value: ....../euw/None/...
        self.feeds_partition = REGION
        self.n_leaderboard_pages = int(N_LEADERBOARD_PAGES)
        self.n_user_iter = int(N_USER_ITER)

    def start_requests(self) -> Iterable[JsonRequest]:
        for page_index in range(1, self.n_leaderboard_pages + 1):
            yield self._leaderboard_api(page_index=page_index)

    def _leaderboard_api(self, page_index=1) -> JsonRequest:
        return JsonRequest(
            urlunparse(
                URLComponents(
                    scheme="https",
                    netloc="u.gg",
                    path="/api",
                    params="",
                    query={},
                    fragment="",
                )
            ),
            callback=self.parse_leaderboard,
            data={
                "operationName": "getRankedLeaderboard",
                "variables": {
                    "page": page_index,
                    "queueType": QUEUE_TYPE,
                    "regionId": self.region,
                },
                "query": "query getRankedLeaderboard($page: Int, $queueType: Int, $regionId: String!) {\n  leaderboardPage(page: $page, queueType: $queueType, regionId: $regionId) {\n    totalPlayerCount\n    topPlayerMostPlayedChamp\n    players {\n      iconId\n      losses\n      lp\n      overallRanking\n      rank\n      summonerLevel\n      riotTagLine\n      riotUserName\n      tier\n      wins\n      __typename\n    }\n    __typename\n  }\n}",
            },
            cb_kwargs={"page_index": page_index},
        )

    def _match_summary_api(
        self, riot_tag_line: str, riot_user_name: str, page: int
    ) -> JsonRequest:
        return JsonRequest(
            urlunparse(
                URLComponents(
                    scheme="https",
                    netloc="u.gg",
                    path="/api",
                    params="",
                    query={},
                    fragment="",
                )
            ),
            callback=self.parse_match_summary,
            data={
                "operationName": "FetchMatchSummaries",
                "variables": {
                    "regionId": self.region,
                    "riotUserName": riot_user_name,
                    "riotTagLine": riot_tag_line,
                    "queueType": [],
                    "duoRiotUserName": "",
                    "duoRiotTagLine": "",
                    "role": [],
                    "seasonIds": [
                        26,
                        25,
                    ],
                    "championId": [],
                    "page": page,
                },
                "query": "query FetchMatchSummaries($championId: [Int], $page: Int, $queueType: [Int], $duoRiotUserName: String, $duoRiotTagLine: String, $regionId: String!, $role: [Int], $seasonIds: [Int]!, $riotUserName: String!, $riotTagLine: String!) {\n  fetchPlayerMatchSummaries(\n    championId: $championId\n    page: $page\n    queueType: $queueType\n    duoRiotUserName: $duoRiotUserName\n    duoRiotTagLine: $duoRiotTagLine\n    regionId: $regionId\n    role: $role\n    seasonIds: $seasonIds\n    riotUserName: $riotUserName\n    riotTagLine: $riotTagLine\n  ) {\n    finishedMatchSummaries\n    totalNumMatches\n    matchSummaries {\n      assists\n      augments\n      championId\n      cs\n      damage\n      deaths\n      gold\n      items\n      jungleCs\n      killParticipation\n      kills\n      level\n      matchCreationTime\n      matchDuration\n      matchId\n      maximumKillStreak\n      primaryStyle\n      queueType\n      regionId\n      role\n      runes\n      subStyle\n      summonerName\n      riotUserName\n      riotTagLine\n      summonerSpells\n      psHardCarry\n      psTeamPlay\n      lpInfo {\n        lp\n        placement\n        promoProgress\n        promoTarget\n        promotedTo {\n          tier\n          rank\n          __typename\n        }\n        __typename\n      }\n      teamA {\n        championId\n        summonerName\n        riotUserName\n        riotTagLine\n        teamId\n        role\n        hardCarry\n        teamplay\n        placement\n        playerSubteamId\n        __typename\n      }\n      teamB {\n        championId\n        summonerName\n        riotUserName\n        riotTagLine\n        teamId\n        role\n        hardCarry\n        teamplay\n        placement\n        playerSubteamId\n        __typename\n      }\n      version\n      visionScore\n      win\n      roleQuestCompletion\n      roleBoundItem\n      __typename\n    }\n    __typename\n  }\n}",
            },
            cb_kwargs={"riot_user_name": riot_user_name},
        )

    def _match_detail_api(
        self, riot_user_name: str, riot_tag_line: str, match_id: str, version: str
    ) -> JsonRequest:
        return JsonRequest(
            urlunparse(
                URLComponents(
                    scheme="https",
                    netloc="u.gg",
                    path="/api",
                    params="",
                    query={},
                    fragment="",
                )
            ),
            callback=self.parse_match_detail,
            data={
                "operationName": "match",
                "variables": {
                    "regionId": self.region,
                    "riotUserName": riot_user_name,
                    "riotTagLine": riot_tag_line,
                    "matchId": str(match_id),
                    "version": version,
                },
                "query": "query match($matchId: String!, $regionId: String!, $riotUserName: String!, $riotTagLine: String!, $version: String!) {\n  match(\n    matchId: $matchId\n    regionId: $regionId\n    riotUserName: $riotUserName\n    riotTagLine: $riotTagLine\n    version: $version\n  ) {\n    allPlayerRanks {\n      rankScores {\n        lastUpdatedAt\n        losses\n        lp\n        queueType\n        rank\n        role\n        seasonId\n        tier\n        wins\n        __typename\n      }\n      riotUserName\n      riotTagLine\n      __typename\n    }\n    historicalData {\n      kaDifferenceFrames {\n        oppValue\n        timestamp\n        youValue\n        __typename\n      }\n      xpDifferenceFrames {\n        oppValue\n        timestamp\n        youValue\n        __typename\n      }\n      teamOneOverview {\n        bans\n        baronKills\n        dragonKills\n        gold\n        inhibitorKills\n        kills\n        riftHeraldKills\n        towerKills\n        __typename\n      }\n      teamTwoOverview {\n        bans\n        baronKills\n        dragonKills\n        gold\n        inhibitorKills\n        kills\n        riftHeraldKills\n        towerKills\n        __typename\n      }\n      runes\n      skillPath\n      statShards\n      accountIdV3\n      csDifferenceFrames {\n        oppValue\n        timestamp\n        youValue\n        __typename\n      }\n      finishedItems {\n        itemId\n        timestamp\n        type\n        __typename\n      }\n      goldDifferenceFrames {\n        oppValue\n        timestamp\n        youValue\n        __typename\n      }\n      itemPath {\n        itemId\n        timestamp\n        type\n        __typename\n      }\n      matchId\n      metricsData {\n        cs\n        jungleCs\n        level\n        pid\n        position\n        riotTagLine\n        riotUserName\n        timestamp\n        totalDamageDoneToChampions\n        totalDamageTaken\n        totalGold\n        xp\n        __typename\n      }\n      postGameData {\n        assists\n        augments\n        carryPercentage\n        championId\n        cs\n        damage\n        damageTaken\n        deaths\n        gold\n        items\n        jungleCs\n        keystone\n        kills\n        level\n        role\n        subStyle\n        riotUserName\n        riotTagLine\n        summonerSpells\n        teamId\n        wardsPlaced\n        level\n        roleBoundItem\n        __typename\n      }\n      timelineData {\n        assistPids\n        assistRiotIds {\n          username\n          tagLine\n          __typename\n        }\n        buildingType\n        eventType\n        killerId\n        killerIds\n        laneType\n        monsterSubtype\n        monsterType\n        pid\n        position\n        riotTagLine\n        riotUserName\n        teamId\n        timestamp\n        towerType\n        victimId\n        victimRiotTagLine\n        victimRiotUserName\n        wardType\n        __typename\n      }\n      primaryStyle\n      queueType\n      regionId\n      subStyle\n      riotUserName\n      riotTagLine\n      __typename\n    }\n    matchSummary {\n      assists\n      augments\n      championId\n      cs\n      damage\n      deaths\n      gold\n      items\n      jungleCs\n      killParticipation\n      kills\n      level\n      matchCreationTime\n      matchDuration\n      matchId\n      maximumKillStreak\n      primaryStyle\n      queueType\n      regionId\n      role\n      runes\n      subStyle\n      summonerName\n      riotUserName\n      riotTagLine\n      summonerSpells\n      psHardCarry\n      psTeamPlay\n      lpInfo {\n        lp\n        placement\n        promoProgress\n        promoTarget\n        promotedTo {\n          tier\n          rank\n          __typename\n        }\n        __typename\n      }\n      teamA {\n        championId\n        summonerName\n        riotUserName\n        riotTagLine\n        teamId\n        role\n        hardCarry\n        teamplay\n        placement\n        playerSubteamId\n        __typename\n      }\n      teamB {\n        championId\n        summonerName\n        riotUserName\n        riotTagLine\n        teamId\n        role\n        hardCarry\n        teamplay\n        placement\n        playerSubteamId\n        __typename\n      }\n      version\n      visionScore\n      win\n      roleQuestCompletion\n      roleBoundItem\n      __typename\n    }\n    playerInfo {\n      accountIdV3\n      accountIdV4\n      exodiaUuid\n      iconId\n      puuidV4\n      regionId\n      summonerIdV3\n      summonerIdV4\n      summonerLevel\n      riotUserName\n      riotTagLine\n      __typename\n    }\n    performanceScore {\n      damageShare\n      damageShareAgg\n      damageShareTotal\n      finalLvlDiff\n      finalLvlDiffAgg\n      finalLvlDiffTotal\n      goldShare\n      goldShareAgg\n      goldShareTotal\n      hardCarry\n      killParticipation\n      killParticipationAgg\n      killParticipationTotal\n      kpOverGs\n      kpOverGsAgg\n      kpOverGsTotal\n      riotUserName\n      riotTagLine\n      teamplay\n      visionScore\n      visionScoreAgg\n      visionScoreTotal\n      __typename\n    }\n    winningTeam\n    __typename\n  }\n}",
            },
            cb_kwargs={"match_id": match_id},
        )

    def parse_leaderboard(
        self, response: Response, page_index: int
    ) -> Iterable[JsonRequest]:
        players = response.json()["data"]["leaderboardPage"]["players"]
        self.logger.info("Found %d players on page %d", len(players), page_index)
        for player in players:
            for i in (1, self.n_user_iter):
                yield self._match_summary_api(
                    player["riotTagLine"], player["riotUserName"], i
                )

    def parse_match_summary(self, response: Response, riot_user_name: str):
        games = response.json()["data"]["fetchPlayerMatchSummaries"]["matchSummaries"]
        self.logger.info("Found %d matches for %s", len(games), riot_user_name)
        for game in games:
            yield self._match_detail_api(
                riot_user_name=game["riotUserName"],
                riot_tag_line=game["riotTagLine"],
                match_id=game["matchId"],
                version=game["version"],
            )

    def parse_match_detail(self, response: Response, match_id: str):
        self.logger.info("Got match detail for %s", match_id)
        yield response.json()
