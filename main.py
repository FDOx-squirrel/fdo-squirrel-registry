"""FDOx registry pipeline orchestrator.

Single entry point for this repository:

    python main.py                  run every step, in order
    python main.py --list           print the steps and exit
    python main.py --only bundle    run one step
    python main.py --from bundle    run this step and everything after it
    python main.py --skip harvest   run everything except this step
    python main.py --dry-run        print the plan, run nothing
    python main.py --strict         warnings become errors (this is what CI runs)

Steps that reach the network are NOT part of the default run. They carry
`network=True` below and are only executed when named explicitly, e.g.

    python main.py --only harvest

The steps mirror Teil B of PRIMER.md; each is implemented in the step it is
named after and reports "skipped (no input)" until then.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import io
import os
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "py"))

REPORT = ROOT / "dist" / "pipeline_report.txt"

# name        module (in py/)   description                                   network
STEPS: list[tuple[str, str, str, bool]] = [
    ("harvest", "step_harvest", "S2  fetch FDOx metadata from Zenodo", True),
    ("bridge", "step_bridge", "S3  crosswalks/fdo--crm.csv -> crm_bridge.ttl", False),
    ("bundle", "step_bundle", "S4  build dist/fdo-registry.ttl", False),
    ("validate", "step_validate", "S5  SHACL gate and quality report", False),
    ("index", "step_index", "S6  build dist/registry-index.json", False),
    ("sparql", "step_sparql", "S7  build the browser query page", False),
    ("site", "step_site", "S6  render docs/ for GitHub Pages", False),
]


class Tee(io.TextIOBase):
    """Write to the terminal and to the report file at the same time.

    Steps are run in-process, so their prints are captured here rather than
    through a pipe. The report and the terminal therefore always show exactly
    the same lines, which is the point: a log that differs from what the user
    saw is a log nobody trusts.
    """

    def __init__(self, *streams):
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the pipeline.")
    parser.add_argument("--list", action="store_true", help="print steps and exit")
    parser.add_argument("--only", metavar="STEP", help="run this step alone")
    parser.add_argument("--from", dest="start", metavar="STEP", help="start here")
    parser.add_argument("--skip", metavar="STEP", action="append", default=[],
                        help="skip this step (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as errors")
    return parser.parse_args()


def select(args: argparse.Namespace) -> list[tuple[str, str, str, bool]]:
    names = [step[0] for step in STEPS]

    for candidate in [args.only, args.start, *args.skip]:
        if candidate and candidate not in names:
            sys.exit(f"unknown step: {candidate}\nknown steps: {', '.join(names)}")

    if args.only:
        return [step for step in STEPS if step[0] == args.only]

    chosen = STEPS
    if args.start:
        chosen = chosen[names.index(args.start):]
    # Network steps stay out of a run that did not name them.
    chosen = [step for step in chosen if not step[3]]
    return [step for step in chosen if step[0] not in args.skip]


def run_step(name: str, module_name: str, strict: bool) -> float:
    """Import the step lazily and run its main(). Returns the duration."""
    started = time.perf_counter()
    module = importlib.import_module(module_name)
    if not hasattr(module, "main"):
        raise AttributeError(f"{module_name} has no main()")

    # Steps that predate the strict flag stay callable. Check the signature
    # rather than catching TypeError: a TypeError raised *inside* the step
    # would otherwise be swallowed and the step run a second time.
    if "strict" in inspect.signature(module.main).parameters:
        module.main(strict=strict)
    else:
        module.main()
    return time.perf_counter() - started


def main() -> int:
    args = parse_args()

    if args.list:
        width = max(len(step[0]) for step in STEPS)
        for name, _, description, network in STEPS:
            mark = "  [network, not in default run]" if network else ""
            print(f"  {name:<{width}}  {description}{mark}")
        return 0

    plan = select(args)
    if not plan:
        print("nothing to do")
        return 0

    if args.dry_run:
        for name, module_name, description, _ in plan:
            print(f"  would run {name} ({module_name}): {description}")
        return 0

    # Without this, ✓, ‰ and δ fail at the pipe on Windows and the traceback
    # talks about codecs instead of the actual problem.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    timings: list[tuple[str, float]] = []
    failed: str | None = None

    with REPORT.open("w", encoding="utf-8") as log:
        tee = Tee(sys.stdout, log)
        with redirect_stdout(tee), redirect_stderr(tee):
            for name, module_name, description, _ in plan:
                print(f"\n=== {name} — {description} ===")
                try:
                    timings.append((name, run_step(name, module_name, args.strict)))
                except Exception:
                    traceback.print_exc()
                    failed = name
                    break

            total = sum(duration for _, duration in timings)
            if timings:
                print("\n=== timings ===")
                width = max(len(name) for name, _ in timings)
                for name, duration in timings:
                    share = duration / total * 100 if total else 0
                    print(f"  {name:<{width}}  {duration:6.1f} s  {share:4.1f} %")
                print(f"  {'total':<{width}}  {total:6.1f} s")

            if failed:
                print(f"\nFAILED in step: {failed}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
