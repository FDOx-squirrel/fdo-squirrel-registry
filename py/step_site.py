"""S6 — render docs/ for GitHub Pages and publish the bundle next to it."""

from __future__ import annotations

import registry_utils as u

TEMPLATES = u.ROOT / "py" / "templates"


def main(strict: bool = False) -> None:
    if not u.INDEX.exists():
        u.skipped(f"{u.INDEX.relative_to(u.ROOT)} does not exist yet (built in S6)")
        return
    if not TEMPLATES.exists():
        u.skipped("py/templates/ does not exist yet (written in S6)")
        return

    raise NotImplementedError("the site is implemented in S6")


if __name__ == "__main__":
    main()
