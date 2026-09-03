"""S2 — harvest FDOx metadata from Zenodo into data/raw/fdo/.

The only step that reaches the network. It is therefore never part of the
default run: `python main.py --only harvest`.
"""

from __future__ import annotations

import registry_utils as u


def main(strict: bool = False) -> None:
    if not u.SOURCES.exists():
        u.skipped(f"{u.SOURCES.relative_to(u.ROOT)} does not exist")
        return

    sources = u.read_json(u.SOURCES).get("sources", [])
    if not sources:
        u.skipped("registry/sources.json lists no sources yet (filled in S2)")
        return

    raise NotImplementedError("harvesting is implemented in S2")


if __name__ == "__main__":
    main()
