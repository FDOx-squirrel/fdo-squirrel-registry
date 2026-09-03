"""S6 — query the bundle into dist/registry-index.json for the facet page.

The facet page reads this file rather than the graph, so nobody waits for a
WASM runtime just to filter by "3D".
"""

from __future__ import annotations

import registry_utils as u


def main(strict: bool = False) -> None:
    if not u.BUNDLE.exists():
        u.skipped(f"{u.BUNDLE.relative_to(u.ROOT)} does not exist yet (built in S4)")
        return

    raise NotImplementedError("the index is implemented in S6")


if __name__ == "__main__":
    main()
