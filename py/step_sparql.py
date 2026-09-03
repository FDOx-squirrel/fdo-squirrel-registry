"""S7 — queries.yaml -> docs/sparql.html (rdflib under Pyodide) and .rq files.

Every query is executed against the real bundle at build time, and a query that
returns no rows fails the build: SPARQL does not fail on a mistyped IRI, it
returns nothing, so an empty result is the ordinary symptom of a broken graph.
"""

from __future__ import annotations

import registry_utils as u

QUERIES = u.ROOT / "queries.yaml"


def main(strict: bool = False) -> None:
    if not QUERIES.exists():
        u.skipped("queries.yaml does not exist yet (written in S7)")
        return
    if not u.BUNDLE.exists():
        u.skipped(f"{u.BUNDLE.relative_to(u.ROOT)} does not exist yet (built in S4)")
        return

    raise NotImplementedError("the query page is implemented in S7")


if __name__ == "__main__":
    main()
