"""S5 — validate the bundle against metadata/shapes.ttl and write the quality report.

Three kinds of shape: completeness, the CRM anchor check over every class that
occurs in the bundle, and the MUST-NOT constructs of the NFDI4Objects
application profile.
"""

from __future__ import annotations

import registry_utils as u

SHAPES = u.METADATA / "shapes.ttl"


def main(strict: bool = False) -> None:
    if not u.BUNDLE.exists():
        u.skipped(f"{u.BUNDLE.relative_to(u.ROOT)} does not exist yet (built in S4)")
        return
    if not SHAPES.exists():
        u.skipped(f"{SHAPES.relative_to(u.ROOT)} does not exist yet (written in S5)")
        return

    raise NotImplementedError("validation is implemented in S5")


if __name__ == "__main__":
    main()
