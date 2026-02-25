"""Module containing feeds helpers"""

from urllib.parse import urlparse
from scrapy.crawler import Crawler
from azure.storage.blob import BlobServiceClient

from scrapy.extensions.feedexport import BlockingFeedStorage

from typing import Any, IO
from typing_extensions import Self


class AzureFeedStorage(BlockingFeedStorage):
    def __init__(
        self,
        uri: str,
        account_url: str,
        account_key: str,
        container: str,
        *,
        feed_options: dict[str, Any] | None
    ):
        u = urlparse(uri)
        self.blob = u.netloc + u.path  # Remove "azure://" from uri
        self.container_name = container
        self.container_client = BlobServiceClient(
            account_url=account_url, credential=account_key
        )

    @classmethod
    def from_crawler(
        cls, crawler: Crawler, uri: str, *, feed_options: dict[str, Any] | None
    ) -> Self:
        return cls(
            uri=uri,
            account_url=crawler.settings["AZURE_ACCOUNT_URL"],
            account_key=crawler.settings["AZURE_ACCOUNT_KEY"],
            container=crawler.settings["AZURE_CONTAINER"],
            feed_options=feed_options,
        )

    def _store_in_thread(self, file: IO[bytes]) -> None:
        file.seek(0)
        self.blob_client = self.container_client.get_blob_client(
            container=self.container_name, blob=self.blob
        )
        _ = self.blob_client.upload_blob(file, blob_type="BlockBlob")
        file.close()
