import os
import random


class Proxy:
    """A middleware to use a proxy url."""

    def process_request(self, request, spider):
        if not request.meta.get("proxy", None):
            proxy_network = os.getenv("PROXY_NETWORK", None)
            if proxy_network:
                proxy_network = proxy_network.format(session_id=random.getrandbits(256))
            request.meta["proxy"] = proxy_network


class Impersonate:
    """A middleware to impersonate a browser"""

    def process_request(self, request, spider):
        if not request.meta.get("impersonate", None):
            request.meta["impersonate"] = "chrome124"
