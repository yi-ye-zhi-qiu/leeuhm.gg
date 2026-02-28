"""Custom Scrapy extensions."""

from typing import Any
from scrapy import Spider
from scrapy.extensions.feedexport import FeedExporter


class ImmediateFeedExporter(FeedExporter):
    """FeedExporter subclass that uploads each batch immediately when full,
    rather than deferring all uploads to spider close."""

    async def item_scraped(self, item: Any, spider: Spider) -> None:
        slots = []
        to_close = []
        for slot in self.slots:
            if not slot.filter.accepts(item):
                slots.append(slot)
                continue

            slot.start_exporting()
            assert slot.exporter
            slot.exporter.export_item(item)
            slot.itemcount += 1

            if (
                self.feeds[slot.uri_template]["batch_item_count"]
                and slot.itemcount
                >= self.feeds[slot.uri_template]["batch_item_count"]
            ):
                uri_params = self._get_uri_params(
                    spider, self.feeds[slot.uri_template]["uri_params"], slot
                )
                slots.append(
                    self._start_new_batch(
                        batch_id=slot.batch_id + 1,
                        uri=slot.uri_template % uri_params,
                        feed_options=self.feeds[slot.uri_template],
                        spider=spider,
                        uri_template=slot.uri_template,
                    )
                )
                to_close.append(slot)
            else:
                slots.append(slot)

        # Swap in new slots BEFORE awaiting uploads, so incoming items
        # write to the new batch file instead of the closed one.
        self.slots = slots
        for slot in to_close:
            await self._close_slot(slot, spider)
