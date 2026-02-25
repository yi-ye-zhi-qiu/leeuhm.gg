import os

LOG_LEVEL = "INFO"
RETRY_ENABLED = False
COOKIES_ENABLED = False
SPIDER_MODULES = ["crawl.spiders"]
CONCURRENT_REQUESTS = 64
DOWNLOADER_MIDDLEWARES = {
    "crawl.middlewares.Proxy": 100,
    "crawl.middlewares.Impersonate": 200,
}
ITEM_PIPELINES = {
    "crawl.pipelines.RecordCrawledAt": 100,
}
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
DOWNLOADER_CLIENT_TLS_METHOD = "TLSv1.2"
DOWNLOAD_HANDLERS = {
    "http": "scrapy_impersonate.ImpersonateDownloadHandler",
    "https": "scrapy_impersonate.ImpersonateDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEEDS = {
    os.path.join(
        "azure://",  # upload to Azure
        "%(name)s",  # the Spider name, e.g. crawl-user-game-ids
        "%(_version)s",  # x.y.z
        "%(feeds_partition)s",  # /{region}/{tier}/, e.g. /euw/diamond/
        # /{region}/{user_name}/{user_tag} e.g. /na/ye qiu11/na1/
        "%(batch_time)s-%(batch_id)d.jsonl.gz",
    ): {
        "format": "jsonlines",
        "encoding": "utf-8",
        "store_empty": False,
        "postprocessing": ["crawl.postprocessing.GzipPlugin"],
        "gzip_compresslevel": 9,
        "batch_item_count": 150,  # every X summoner pages
    }
}
FEED_STORAGES = {"azure": "crawl.utils.feeds.AzureFeedStorage"}
AZURE_CONTAINER = os.environ["AZURE_CONTAINER"]
AZURE_ACCOUNT_URL = os.environ["AZURE_ACCOUNT_URL"]
AZURE_ACCOUNT_KEY = os.environ["AZURE_ACCOUNT_KEY"]
DEFAULT_REQUEST_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Authorization": "",
    "Content-Type": "application/json",
    "Dnt": "1",
    "Origin": "https://u.gg",
    "Priority": "u=1, i",
    "Referer": "https://u.gg/lol/leaderboards/ranking?region=na1",
    "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    "Sec-Ch-Ua-Mobile": "?1",
    "Sec-Ch-Ua-Platform": '"Android"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
    "X-App-Type": "web",
    "X-App-Version": "43fbbe7cce4c6e5ca7278597788eefbe02e91992",
}
# op.gg headers
# DEFAULT_REQUEST_HEADERS = {
#     "Accept": "text/x-component",
#     "Accept-Language": "en-US,en;q=0.9",
#     "Content-Type": "text/plain;charset=UTF-8",
#     "Dnt": "1",
#     "Next-Action": "409a2b9ca50d15e50a4dace93552e3a40113dc2753",
#     "Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22en%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22lol%22%2C%7B%22children%22%3A%5B%22summoners%22%2C%7B%22children%22%3A%5B%5B%22region%22%2C%22na%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%5B%22summoner%22%2C%22Doublelift-NA01%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
#     "Origin": "https://op.gg",
#     "Priority": "u=1, i",
#     "Referer": "https://op.gg/lol/summoners/na/Doublelift-NA01",
#     "Sec-Ch-Ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
#     "Sec-Ch-Ua-Mobile": "?1",
#     "Sec-Ch-Ua-Platform": '"Android"',
#     "Sec-Fetch-Dest": "empty",
#     "Sec-Fetch-Mode": "cors",
#     "Sec-Fetch-Site": "same-origin",
#     "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Mobile Safari/537.36",
# }
