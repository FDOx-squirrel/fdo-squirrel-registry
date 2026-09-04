"""S8 - package the registry itself as a fdo:RegistryFDO via fdo-squirrel.

Bundle plus index plus shapes, staged into one ZIP alongside MD.cff and
CITATION.cff, and run through fdo-squirrel exactly as any harvested package
would be - the registry becomes an FDO by the same rules its content
follows, and the round trip is the best integration test S8 gets (PRIMER
S8).

fdo-squirrel is a dependency (requirements.txt), invoked as the console
script installed next to this interpreter, not via PATH or a module import
(see `_fdo_squirrel_executable()` for why both of those fail here).
`--outdir` points it at dist/release/ rather than letting it default to the
current directory, so a run from anywhere still lands the result in the
same place (fdo-squirrel PATCH-README, "Why the main.py change").

What this step will not do is publish to Zenodo - that needs a human with
credentials, the same reasoning that keeps `harvest` out of the default run
(PRIMER A4, "Netzschritt im Standardlauf"). It writes the finished bundle to
dist/release/ and says so; the DOI that publishing it returns is what later
goes into registry/sources.json, by hand, like every other entry.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import registry_utils as u

STAGE = u.DIST / "_release_stage"
STAGE_ZIP = u.DIST / "_release_stage.zip"

REQUIRED = [u.BUNDLE, u.INDEX, u.SHAPES, u.MD_CFF, u.CITATION_CFF]


def _fdo_squirrel_executable() -> Path | None:
    """The fdo-squirrel console script installed in *this* interpreter's
    environment, found the way pip actually put it there.

    Not `shutil.which("fdo-squirrel")`: that walks $PATH, which does not
    include a venv's scripts directory unless the venv was activated - true
    even when fdo-squirrel is correctly installed in the exact environment
    running this script (e.g. `venv/bin/python main.py` without `source
    venv/bin/activate`). Not `sys.executable -m main` either: fdo-squirrel's
    entry module is named `main`, and Python puts the current directory
    first on a subprocess's sys.path for `-m` - since this repository's own
    orchestrator is also `main.py`, that resolves to *this* file, not
    fdo-squirrel's, the moment this step runs from the repository root,
    which is exactly the case here.

    Not `Path(sys.executable).parent / "fdo-squirrel"` either, on its own:
    that is right for a POSIX venv (`venv/bin/python` and
    `venv/bin/fdo-squirrel` are siblings) and for a Windows venv
    (`venv\\Scripts\\python.exe` and `venv\\Scripts\\fdo-squirrel.exe` are
    siblings too) - but wrong for a plain, non-venv Windows install, where
    `python.exe` sits at the installation root while pip puts console
    scripts in a `Scripts\\` subdirectory next to it, not beside it.
    `sysconfig.get_path("scripts")` is what pip itself consults to decide
    where a console script goes, so it is correct in all three layouts;
    kept as the first candidate, with the sibling-of-python.exe path second
    as a fallback for anything unusual enough to disagree with it.
    """
    name = "fdo-squirrel.exe" if sys.platform == "win32" else "fdo-squirrel"
    candidates = [
        Path(sysconfig.get_path("scripts")) / name,
        Path(sys.executable).parent / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _stage() -> None:
    """Assemble bundle + index + shapes + MD.cff + CITATION.cff into one ZIP.

    A copy, not a symlink or an in-place zip of the repo: fdo-squirrel reads
    a self-contained package, and dist/ and metadata/ hold plenty this
    release has no business describing (quality_report.md, the n4o bundle,
    shapes_selftest.ttl, ...).
    """
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "dist").mkdir(parents=True)
    (STAGE / "metadata").mkdir()
    shutil.copy2(u.BUNDLE, STAGE / "dist" / u.BUNDLE.name)
    shutil.copy2(u.INDEX, STAGE / "dist" / u.INDEX.name)
    shutil.copy2(u.SHAPES, STAGE / "metadata" / u.SHAPES.name)
    shutil.copy2(u.MD_CFF, STAGE / u.MD_CFF.name)
    shutil.copy2(u.CITATION_CFF, STAGE / u.CITATION_CFF.name)

    if STAGE_ZIP.exists():
        STAGE_ZIP.unlink()
    shutil.make_archive(str(STAGE_ZIP.with_suffix("")), "zip", STAGE)


def main(strict: bool = False) -> None:
    missing = [u.rel(p) for p in REQUIRED if not p.exists()]
    if missing:
        u.skipped(f"missing {', '.join(missing)}")
        return

    exe = _fdo_squirrel_executable()
    if exe is None:
        message = "fdo-squirrel not installed in this interpreter's environment - pip install -r requirements.txt"
        if strict:
            raise SystemExit(f"release: {message}")
        u.skipped(message)
        return

    _stage()
    u.ensure_dirs(u.RELEASE_DIR)
    result = subprocess.run(
        [str(exe), "--package", str(STAGE_ZIP), "--outdir", str(u.RELEASE_DIR)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    shutil.rmtree(STAGE)
    STAGE_ZIP.unlink()

    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        message = f"fdo-squirrel exited {result.returncode}"
        if strict:
            raise SystemExit(f"release: {message}")
        u.skipped(message)
        return

    ttl = u.RELEASE_DIR / "fdo-metadata.ttl"
    bundle = next(u.RELEASE_DIR.glob("*-fdo-bundle.zip"), None)
    print(f"  {u.rel(ttl)}"
          + (f", {ttl.stat().st_size} bytes" if ttl.exists() else " (missing)"))
    if bundle:
        print(f"  {u.rel(bundle)} - ready to publish by hand")
    print("  not published: Zenodo upload needs a human with credentials (PRIMER A4).")
    print("  once published, add the DOI to registry/sources.json (S2).")


if __name__ == "__main__":
    main()
