"""S3 — generate metadata/crm_bridge.ttl from crosswalks/fdo--crm.csv.

Only the `axiom` rows become RDF here; the `instance` rows are applied per
object by the bundle step, because we do not axiomatise foreign namespaces
(PRIMER A3).
"""

from __future__ import annotations

import registry_utils as u

CROSSWALK = u.CROSSWALKS / "fdo--crm.csv"


def main(strict: bool = False) -> None:
    if not CROSSWALK.exists():
        u.skipped(f"{CROSSWALK.relative_to(u.ROOT)} does not exist yet (written in S3)")
        return

    raise NotImplementedError("the crosswalk is implemented in S3")


if __name__ == "__main__":
    main()
