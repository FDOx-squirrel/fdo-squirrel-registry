"""Declared, minimal repairs applied to a harvested TTL before it is parsed.

A published Zenodo record is immutable. Four of the eight pinned packages were
written by a generator that has since been fixed, so no upstream correction can
ever reach them: either the registry reads them as they are, or those four FDOs
stay out of the catalogue for good (PRIMER A4, 2026-09-03).

The rules below are therefore *encoding* repairs, in the same sense as the
`normalise` rows of the crosswalk: they change how a statement is written down,
never what it says. Two properties make that claim checkable rather than a
promise:

  * **Every rule is evidenced by a later package.** Both defects were fixed in
    `fdo-squirrel` between January and February 2026, so the repaired form is
    not our invention - it is literally what the same generator writes today,
    and a February package in `data/raw/fdo/` shows it.
  * **Every rule reports itself.** A repaired file is flagged in the build log,
    on the crosswalk page and in the bundle (`fdoreg:readRepair`), and the
    `fdoreg:sha256` recorded for the record stays the hash of the *original*
    file as Zenodo holds it. Nothing in the output claims to have read a file
    that Zenodo does not have.

A rule that cannot fire without guessing is not written here. Repairing the
three duplicated `dct:description` values of 18732893 would need us to decide
which of "make 3d model available", "good" and "low" was meant to be what; that
is a defect of the data, not of its encoding, and it goes into the quality
report in S5 instead.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Rule 1 - a prefix used but never declared
# ---------------------------------------------------------------------------

# rdflib's complaint, e.g. 'Bad syntax (Prefix "crmdig:" not bound)'
_UNBOUND = re.compile(r'Prefix "([A-Za-z][\w.-]*):" not bound')


def missing_prefixes(text: str, error: Exception, known: dict[str, str]) -> tuple[str, str] | None:
    """Prepend an @prefix line for a prefix the file uses but never declares.

    The three January packages write `crmdig:D1, crm:E73` in the class list of
    the dataset without declaring either prefix. The February packages declare
    both, with exactly the bindings in `registry_utils.PREFIXES` - so the fix
    adds a line the generator itself now emits.

    A prefix that is *not* in that table is not repaired. Choosing a namespace
    for it would be inventing the one thing the file failed to say.
    """
    match = _UNBOUND.search(str(error))
    if not match:
        return None
    prefix = match.group(1)
    if prefix not in known:
        return None
    line = f"@prefix {prefix}: <{known[prefix]}> .\n"
    return line + text, f"missing-prefix:{prefix}"


# ---------------------------------------------------------------------------
# Rule 2 - unescaped quotes inside a one-line string literal
# ---------------------------------------------------------------------------

# predicate, then a literal that runs to the end of the line and is closed by
# ; or . - the shape the generator writes one statement per line in.
_ONE_LINE_LITERAL = re.compile(r'^(\s*[\w.-]+:[^\s"]+\s+)"(.*)"(\s*[;.]\s*)$')


def unescaped_quotes(text: str, error: Exception, known: dict[str, str]) -> tuple[str, str] | None:
    """Escape `"` inside a literal that spans the rest of its line.

    18732893 carries the JSON of `dct:provenance` unescaped, so the literal
    ends at the first inner quote and the parser sees a bare word where it
    wants a predicate. The February packages carry the same JSON with `\\"`.

    Only single-line literals closed by `;` or `.` are touched, so a typed or
    language-tagged literal (which ends in `^^` or `@`) is left alone.
    """
    changed = False
    out = []
    for line in text.splitlines(keepends=True):
        match = _ONE_LINE_LITERAL.match(line.rstrip("\n"))
        if match:
            head, body, tail = match.groups()
            # An already-escaped quote is left as it is; only a bare one is a
            # defect, and re-escaping would turn \" into \\".
            fixed = re.sub(r'(?<!\\)"', r'\\"', body)
            if fixed != body:
                line = f'{head}"{fixed}"{tail}\n'
                changed = True
        out.append(line)
    if not changed:
        return None
    return "".join(out), "unescaped-quote"


RULES = (missing_prefixes, unescaped_quotes)

# A file needing more than this many rounds is not suffering from the two known
# defects; it is broken in a way nobody has looked at, and guessing further is
# how a repair layer starts inventing content.
MAX_ROUNDS = 12


def repair(text: str, parse, known: dict[str, str]) -> tuple[str, list[str]]:
    """Apply rules until the text parses or no rule matches.

    `parse` is called with the text and must raise on invalid Turtle. Returns
    the (possibly unchanged) text and the list of repairs applied, in order.
    """
    applied: list[str] = []
    for _ in range(MAX_ROUNDS):
        try:
            parse(text)
            return text, applied
        except Exception as error:
            for rule in RULES:
                result = rule(text, error, known)
                if result is not None:
                    text, label = result
                    applied.append(label)
                    break
            else:
                return text, applied            # no rule matched: give up
    return text, applied
