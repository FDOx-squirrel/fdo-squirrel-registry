"""Read one member out of an FDOx package ZIP — local, or remote via HTTP Range.

An FDOx package is a ZIP on Zenodo that carries the 3D data *and* its
fdo-metadata.ttl. The registry needs only the latter, a few kilobytes inside a
file of several hundred megabytes. Two ways to get at it:

- `member_from_local_zip(path, name)` for a package already on disk
  (config.local.json → package_dir, or --zip on the command line);
- `member_from_remote_zip(url, name, ...)` which reads the central directory
  and the one entry through HTTP Range requests. `zipfile` does all the parsing
  (including ZIP64 and the CRC check); `RangeFile` merely makes a URL look like
  a seekable file. Typically three to four requests per package.

Both return the member's bytes plus a small provenance dict. Both verify the
member against the CRC-32 the ZIP itself carries; the MD5 Zenodo publishes for
the whole ZIP can only be checked by whoever reads the whole ZIP, and the
caller says in harvest.json which of the two it was.
"""

from __future__ import annotations

import io
import posixpath
import zipfile
from pathlib import Path
from typing import Callable

# fetch_range(url, start, end_inclusive) -> (status_code, bytes, content_range_header)
# A negative start with end None asks for the last -start bytes ("bytes=-65536").
RangeFetcher = Callable[[str, int, "int | None"], tuple[int, bytes, str | None]]


class RangeUnsupported(RuntimeError):
    """The server answered a Range request with 200 — it would send the whole file."""


class RangeFile(io.RawIOBase):
    """A read-only, seekable view of a URL, backed by HTTP Range requests.

    Reads are served from a cache of fetched blocks; every miss fetches at
    least `block` bytes so that zipfile's many small reads of the central
    directory do not each become a request.
    """

    def __init__(self, url: str, fetch_range: RangeFetcher, *, block: int = 1 << 16):
        self.url = url
        self.fetch_range = fetch_range
        self.block = block
        self.pos = 0
        self.requests = 0
        self.cache: dict[int, bytes] = {}   # start offset -> bytes
        self.size = self._probe_size()

    # -- size via a suffix range request for the tail; also detects a server
    #    without Range. The tail holds the end-of-central-directory record and,
    #    for a package of a dozen files, the whole central directory — so the
    #    same request that learns the size also answers zipfile's first reads.
    def _probe_size(self) -> int:
        status, data, content_range = self._fetch(-self.block, None)
        if status != 206 or not content_range or "/" not in content_range:
            raise RangeUnsupported(f"{self.url}: Range not supported (status {status})")
        span, total = content_range.rsplit("/", 1)
        if total == "*":
            raise RangeUnsupported(f"{self.url}: server does not report the total size")
        start = int(span.split()[-1].split("-")[0])
        self.cache[start] = data
        return int(total)

    def _fetch(self, start: int, end: int) -> tuple[int, bytes, str | None]:
        self.requests += 1
        return self.fetch_range(self.url, start, end)

    def _get(self, start: int, end: int) -> bytes:
        """Bytes [start, end) — from cache or via one request covering them."""
        for offset, chunk in self.cache.items():
            if offset <= start and end <= offset + len(chunk):
                return chunk[start - offset:end - offset]
        want_end = min(max(end, start + self.block), self.size)
        status, data, _ = self._fetch(start, want_end - 1)
        if status != 206:
            raise RangeUnsupported(f"{self.url}: Range not supported (status {status})")
        self.cache[start] = data
        return data[:end - start]

    # -- file protocol used by zipfile
    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        else:
            raise ValueError(whence)
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        end = min(self.pos + n, self.size)
        if end <= self.pos:
            return b""
        data = self._get(self.pos, end)
        self.pos = end
        return data

    def readinto(self, buffer) -> int:
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


def find_member(names: list[str], basename: str) -> tuple[str | None, list[str]]:
    """The one member whose file name is `basename`, plus look-alikes.

    A package may keep its files at the root or under one top-level folder,
    so the match is on the base name. Two candidates are as bad as none: the
    registry does not guess (PRIMER S2).
    """
    exact = sorted(n for n in names if posixpath.basename(n) == basename and not n.endswith("/"))
    lookalikes = sorted(
        n for n in names
        if n not in exact and (n.lower().endswith(".ttl") or basename.lower() in posixpath.basename(n).lower())
    )
    if len(exact) == 1:
        return exact[0], lookalikes
    return None, sorted(exact + lookalikes)


def _extract(archive: zipfile.ZipFile, basename: str) -> tuple[bytes | None, dict]:
    member, lookalikes = find_member(archive.namelist(), basename)
    info = {"members": len(archive.namelist()), "lookalikes": lookalikes}
    if member is None:
        return None, info
    entry = archive.getinfo(member)
    data = archive.read(member)          # zipfile verifies the CRC-32 here
    info.update({"member": member, "member_crc32": f"{entry.CRC:08x}",
                 "member_size": entry.file_size, "crc32_verified": True})
    return data, info


def member_from_local_zip(path: Path, basename: str) -> tuple[bytes | None, dict]:
    with zipfile.ZipFile(path) as archive:
        data, info = _extract(archive, basename)
    info["fetch_mode"] = "local"
    return data, info


def member_from_remote_zip(url: str, basename: str, fetch_range: RangeFetcher) -> tuple[bytes | None, dict]:
    """Raises RangeUnsupported when the server will not serve byte ranges."""
    remote = RangeFile(url, fetch_range)
    with zipfile.ZipFile(remote) as archive:
        data, info = _extract(archive, basename)
    info.update({"fetch_mode": "range", "range_requests": remote.requests, "zip_size": remote.size})
    return data, info


def member_from_zip_bytes(blob: bytes, basename: str) -> tuple[bytes | None, dict]:
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        data, info = _extract(archive, basename)
    info["fetch_mode"] = "full"
    return data, info
