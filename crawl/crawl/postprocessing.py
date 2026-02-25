"""Module containing postprocessing"""

from gzip import GzipFile
from typing import Any, BinaryIO, Dict


class GzipPlugin:
    """
    Compresses received data using `gzip <https://en.wikipedia.org/wiki/Gzip>`_.

    Accepted ``feed_options`` parameters:

    - `gzip_compresslevel`
    - `gzip_mtime`
    - `gzip_filename`

    See :py:class:`gzip.GzipFile` for more info about parameters.

    This is modified from source.

    The current S3 feeds interaction with Gzip package is broken.

    More specifically:
      - Closes temporary file.
      - `_store_in_thread` method receives closed file
      - file seek fails

    Our modification is to only close Gzip instance, not the file itself.

    References:
      - https://github.com/scrapy/scrapy/issues/5500
      - https://github.com/scrapy/scrapy/issues/5928
    """

    def __init__(self, file: BinaryIO, feed_options: Dict[str, Any]) -> None:
        self.file = file
        self.feed_options = feed_options
        compress_level = self.feed_options.get("gzip_compresslevel", 9)
        mtime = self.feed_options.get("gzip_mtime")
        filename = self.feed_options.get("gzip_filename")
        self.gzipfile = GzipFile(
            fileobj=self.file,
            mode="wb",
            compresslevel=compress_level,
            mtime=mtime,
            filename=filename,
        )

    def write(self, data: bytes) -> int:
        return self.gzipfile.write(data)

    def close(self) -> None:
        self.gzipfile.close()
        # Change to source: commenting out closing file
        # self.file.close()
