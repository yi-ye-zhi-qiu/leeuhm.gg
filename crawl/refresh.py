# """Script to refresh all tier/region data and some specific users"""
#
# from scrapy.crawler import CrawlerProcess
# from twisted.internet import defer
# from twisted.internet import asyncioreactor
# from scrapy.utils.log import configure_logging
# from scrapy.utils.reactor import install_reactor
# from scrapy.utils.project import get_project_settings
#
# # Generic configuration
# GAME_SPIDER = "crawl-game-ids"
# USER_SPIDER = "crawl-user-game-ids"
# configure_logging()
# settings = get_project_settings()
# process = CrawlerProcess(settings)
#
# # Installation of asyncio reactor as per `CrawlerRunner`
# # https://docs.scrapy.org/en/latest/topics/asyncio.html#installing-the-asyncio-reactor
# reactor = asyncioreactor.AsyncioSelectorReactor()
# install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")
#
#
# # Sequential run of spiders, one runs after the prior completes
# @defer.inlineCallbacks
# def crawl():
#     yield process.crawl(
#         GAME_SPIDER, "na", "challenger", N_LEADERBOAD_PAGES=10, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "grandmaster", N_LEADERBOAD_PAGES=20, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "master", N_LEADERBOAD_PAGES=30, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "diamond", N_LEADERBOAD_PAGES=100, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "emerald", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "platinum", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "gold", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "silver", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "na", "iron", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "challenger", N_LEADERBOAD_PAGES=10, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "grandmaster", N_LEADERBOAD_PAGES=20, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "master", N_LEADERBOAD_PAGES=30, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "diamond", N_LEADERBOAD_PAGES=100, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "emerald", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "platinum", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "gold", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "silver", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "euw", "iron", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "challenger", N_LEADERBOAD_PAGES=10, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "grandmaster", N_LEADERBOAD_PAGES=20, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "master", N_LEADERBOAD_PAGES=30, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "diamond", N_LEADERBOAD_PAGES=100, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "emerald", N_LEADERBOAD_PAGES=150, N_USER_ITER=3
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "platinum", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "gold", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "silver", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         GAME_SPIDER, "kr", "iron", N_LEADERBOAD_PAGES=150, N_USER_ITER=1
#     )
#     yield process.crawl(
#         USER_SPIDER, "euw", USER_NAME="Thebausffs", USER_TAG="EUW", N_USER_ITER=10
#     )
#     yield process.crawl(
#         USER_SPIDER, "na", USER_NAME="ye qiu11", USER_TAG="NA1", N_USER_ITER=10
#     )
#     process.stop()
#
#
# crawl()
# # reactor.run()  # the script will block here until the last crawl call is finished
# process.start()
