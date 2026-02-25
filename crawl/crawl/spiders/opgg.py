# OP.gg has since moved to Next.js server actions, which are annoying to scrape.
#
# import os
# import json
# from scrapy.http import Request
# from jsonschema import validate
# from scrapy.spiders import CrawlSpider, Rule
# from scrapy.linkextractors import LinkExtractor
# from crawl.utils.datatypes import URLComponents
# from scrapy.utils.reactor import install_reactor
# from scrapy.utils.reactor import is_asyncio_reactor_installed
# from urllib.parse import parse_qsl, urlparse, urlunparse, urlencode
#
#
# from typing import Iterable, Literal, Optional, Union
#
#
# class CrawlGameIds(CrawlSpider):
#     """
#     A spider class to crawl OPGG leaderboards and the top 20 games
#     from each player. This will enable downstream crawl of game
#     data.
#
#     You can model the volume of games returned as n_pages * 100 * 20 * 10.
#     This is because there are 100 players per page, 20 games per player,
#     and 10 players per game. This assumes uniqueness across games and players.
#     This is not the case! So, you'll likely end up with some fraction
#     of that estimated volume.
#
#     Please invoke the spider with the `REGION` and `TIER` spider arguments.
#
#     `scrapy crawl leaderboards -a REGION=euw -a TIER=challenger`
#
#     :param TIER: optional, the tier to crawl leaderboards
#        from.  Possible values: challenger, grandmaster,
#        master, diamond, emerald, platinum, gold, silver,
#        bronze, iron. If no value is provided, defaults
#        to None and is just the top X players.
#
#     :param REGION: the region to crawl leaderboards from,
#        possible values: euw, na, kr
#
#     :param N_LEADERBOAD_PAGES: int value of how many leaderboard
#        pages to scrape, has no max
#
#     :param N_USER_ITER: int value of how many API requests to make
#        per user; each iteration returns 20 more games, has no max
#        though the API will time out eventually as OP.gg does not
#        store user data for all time
#     """
#
#     name = "crawl-game-ids"
#     _version = "0.0.0"
#
#     def __init__(
#         self,
#         REGION: Literal["na", "euw", "kr"],
#         TIER: Optional[
#             Literal[
#                 "challenger",
#                 "grandmaster",
#                 "master",
#                 "diamond",
#                 "emerald",
#                 "platinum",
#                 "gold",
#                 "silver",
#                 "bronze",
#                 "iron",
#             ]
#         ] = None,
#         N_LEADERBOAD_PAGES: Optional[int] = 5,
#         N_USER_ITER: Optional[int] = 1,
#         *args,
#         **kwargs,
#     ) -> None:
#         # Check for correct asyncio reactor (allows JA3/Fingerprint impersonation)
#         if not is_asyncio_reactor_installed():
#             raise ValueError(
#                 f"{CrawlGameIds.__qualname__} requires the asyncio Twisted "
#                 f"reactor. Make sure you have it configured in the "
#                 f"TWISTED_REACTOR setting. See the asyncio documentation "
#                 f"of Scrapy for more information."
#             )
#         super(CrawlGameIds, self).__init__(*args, **kwargs)
#         self.start_urls = [
#             f"https://www.op.gg/leaderboards/tier?region={REGION}&tier={TIER}"
#         ]
#         # Used in api function call
#         self.region = REGION
#         # Folder to partition by azure://data/euw/challenger/...
#         # in the case of a null value: ....../euw/None/...
#         self.feeds_partition = os.path.join(REGION, str(TIER))
#         # Number of leaderboard pages
#         self.n_leaderboard_pages = int(N_LEADERBOAD_PAGES)
#         # Number of pages per user
#         self.n_user_iter = int(N_USER_ITER)
#
#     rules = (
#         Rule(
#             LinkExtractor(
#                 allow=r"/summoners/",
#                 deny=(r"champions", r"mastery", r"ingame", r"utm_source"),
#             ),
#             callback="parse_summoners",
#             # This stops "summoners" from propagating more /summoners/ pages!
#             follow=False,
#         ),
#         Rule(
#             # TODO: Find out why this allows: https://www.op.gg/leaderboards/a
#             LinkExtractor(allow=(r"/leaderboards/tier\?region")),
#             process_links="limit_to_n_pages",
#             callback="parse_leaderboards",
#         ),
#     )
#
#     def limit_to_n_pages(self, links) -> list:
#         return list(
#             filter(
#                 lambda x: int(dict(parse_qsl(urlparse(x.url).query))["page"])
#                 <= self.n_leaderboard_pages,
#                 links,
#             )
#         )
#
#     def parse_leaderboards(self, response) -> Iterable:
#         """
#         A method to call on response producted by start_urls attribute.
#
#         This handles pagination up to limit specified as spider argument.
#         """
#
#         yield from map(
#             response.follow,
#             response.xpath("//a[contains(@href, 'page=')]/@href").extract(),
#         )
#
#     def _games_api_request(self, summoner_id, timestamp) -> Request:
#         return Request(
#             urlunparse(
#                 URLComponents(
#                     scheme="https",
#                     netloc="lol-web-api.op.gg",
#                     path=f"/api/v1.0/internal/bypass/games/{self.region}/summoners/{summoner_id}",
#                     params="",
#                     query=urlencode(
#                         {"ended_at": timestamp, "limit": 20, "hl": "en_US"}
#                     ),
#                     fragment="",
#                 )
#             ),
#             callback=self.parse_api_response,
#             cb_kwargs={"summoner_id": summoner_id},
#         )
#
#     def parse_summoners(self, response) -> Union[Iterable, dict]:
#         """A method to yield data of a player."""
#
#         breakpoint()
#         data = json.loads(
#             response.xpath(
#                 "//script[@type='application/json']/text()[contains(.,'props')]"
#             ).get()
#         )
#         # Edgecase: data contains `props` but is not ideal schema.
#         # Will throw KeyError in the below.
#         yield data
#         # Fetch more user games, equivalent to 'Show more' button
#         summoner_id = data["props"]["pageProps"]["data"]["summoner_id"]
#         oldest_game = min(
#             data["props"]["pageProps"]["games"]["data"], key=lambda x: x["created_at"]
#         )
#         if self.n_user_iter > 1:
#             req = self._games_api_request(summoner_id, oldest_game["created_at"])
#             req.meta["n"] = 1
#             yield req
#         self.logger.info(
#             "(Rank %d of %d in %s): User %s, Found %d games, oldest: %s",
#             data["props"]["pageProps"]["data"]["ladder_rank"]["rank"],
#             data["props"]["pageProps"]["data"]["ladder_rank"]["total"],
#             data["query"]["region"],
#             data["query"]["summoner"],
#             len(data["props"]["pageProps"]["games"]["data"]),
#             oldest_game["created_at"],
#         )
#
#     def parse_api_response(self, response, summoner_id):
#         # Check if there are any more games to parse
#         # This can reach a limit if the user has no historical values
#         if not (n_games := len(response.json()["data"])):
#             return
#
#         oldest_game = min(response.json()["data"], key=lambda x: x["created_at"])
#         if (n := response.meta["n"]) <= self.n_user_iter:
#             req = self._games_api_request(summoner_id, oldest_game["created_at"])
#             req.meta["n"] = n + 1
#             yield req
#         # Just maintain the same schema as `parse_summoners`
#         data = {"props": {"pageProps": {"games": response.json()}}}
#         yield data
#         self.logger.info(
#             "(Rank ? of ? in ?): User %s, Found %d games, oldest: %s",
#             summoner_id,
#             len(data["props"]["pageProps"]["games"]["data"]),
#             oldest_game["created_at"],
#         )
#
#
# class CrawlUserGameIds(CrawlGameIds):
#     """
#     Extends class to allow developer to query by user information only.
#     """
#
#     name = "crawl-user-game-ids"
#     _version = "0.0.0"
#
#     def __init__(
#         self, REGION: str, USER_NAME: str, USER_TAG: str, *args, **kwargs
#     ) -> None:
#         super(CrawlUserGameIds, self).__init__(REGION, *args, **kwargs)
#         self.start_urls = [
#             f"https://www.op.gg/summoners/{REGION}/{USER_NAME}-{USER_TAG}"
#         ]
#         # Folder to partition by azure://data/euw/challenger/...
#         # in the case of a null value: ....../euw/None/...
#         self.feeds_partition = os.path.join(REGION, USER_NAME, USER_TAG)
#         return
