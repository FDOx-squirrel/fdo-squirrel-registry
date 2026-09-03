"""S4 — build dist/fdo-registry.ttl as a DCAT catalogue.

Order matters: vereindeutigen before merging. Skolemise blank nodes and rewrite
the package-relative urn: IRIs *per record*, then hang the result into the
catalogue — otherwise the collision has already happened (PRIMER A1, Befund 2).
"""

from __future__ import annotations

import registry_utils as u


def main(strict: bool = False) -> None:
    records = u.harvested_records()
    if not records:
        u.skipped("no harvested FDO metadata under data/raw/fdo/ (run: python main.py --only harvest)")
        return

    raise NotImplementedError("bundling is implemented in S4")


if __name__ == "__main__":
    main()
