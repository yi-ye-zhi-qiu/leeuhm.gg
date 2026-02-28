import os
import random

PROXY_NETWORK = os.getenv("PROXY_NETWORK", "")


class Proxy:
    """A middleware to use a proxy url."""

    def process_request(self, request, spider):
        if not request.meta.get("proxy", None) and PROXY_NETWORK:
            request.meta["proxy"] = PROXY_NETWORK.format(
                session=random.getrandbits(256)
            )


class Impersonate:
    """A middleware to impersonate a browser."""

    def process_request(self, request, spider):
        # request.meta.setdefault("impersonate", "chrome")
        return None
