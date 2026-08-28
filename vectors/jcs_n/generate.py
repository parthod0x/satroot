"""Historical test vectors for `jcs-n`, a WITHDRAWN algorithm.

`jcs-n` was defined in `draft-mih-sokolov-scitt-payload-binding-01` and
**withdrawn in -02** (published 2026-08-24), which replaces it with plain
`jcs` — RFC 8785 with no normalization pass — and prohibits new declarations
using `jcs-n`.

These vectors were produced while implementing `jcs-n` from the -01 text, and
are retained as a record of that implementation, not as an interoperability
contribution. Anyone implementing the current registry wants `jcs`, and -02
§4.1 states the exclusion rule outright.

## The scope question, and how it resolved

Implementing -01 surfaced one thing its text did not settle: whether the
exclusion set matched top-level member names only, or names at any depth.
Section 4 said "the set of fields declared by the payload class" without
defining the scope, and §13.2's only registered entry could not distinguish
the readings.

**-02 §4.1 settles it, in the direction this implementation had chosen:**

    The exclusion set is matched against the top-level member names of P
    only; a member of the same name nested inside a member's value is not
    removed.

Vector 5 below records both candidate readings, so the ambiguity that existed
in -01 is legible rather than merely asserted. The reading now specified is
marked.

## What these vectors are worth

They are one implementation's, not cross-validated against another. -02's
withdrawal rationale notes an implementer census finding "the reference
implementation was the only implementer of the normalization step" — this was
a second, which is a factual footnote to that premise and nothing more; the
byte audit reported alongside it (191 of 203 records identical under plain
`jcs`) is the substantive reason for withdrawal and is unaffected.

Run:  PYTHONPATH=src python vectors/jcs_n/generate.py
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from satroot_jcs import jcs_n, jcs_serialize, strip_absent  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


VECTORS = [
    {
        "name": "absent-null-empty-collapse",
        "why": (
            "-01 section 3.1 (Algorithm jcs-n) removes members whose value is "
            "null, an empty array "
            "or an empty object. All four inputs must therefore produce one "
            "digest. An implementation that removes only null, or only null "
            "and empty object, diverges here."
        ),
        "inputs": [{}, {"x": None}, {"x": []}, {"x": {}}],
        "exclusion_set": None,
        "settled_by_the_draft": True,
    },
    {
        "name": "emptied-object-inside-an-array",
        "why": (
            "RFC 8259 defines `member` as a name/value pair, which occurs "
            "only inside an object; array contents are elements. The draft "
            "uses the terms correspondingly - 'empty array (zero elements)' "
            "against 'empty object (zero members)' - so `{\"a\": [{\"b\": "
            "null}]}` normalises to `{\"a\": [{}]}` and NOT to `{}`. A "
            "generic recursive prune that also filters arrays gets this "
            "wrong. That is a nonconforming implementation rather than a "
            "second reading, which is exactly what a vector prevents."
        ),
        "inputs": [{"a": [{"b": None}]}],
        "exclusion_set": None,
        "settled_by_the_draft": True,
    },
    {
        "name": "falsy-values-survive",
        "why": (
            "'Explicitly set to a non-null value' is imprecise: an empty "
            "array and an empty object ARE non-null and are removed, while "
            "false, 0 and \"\" are non-null and are kept. An implementer "
            "writing `if (!value) delete obj[key]` in a falsiness-based "
            "language strips all five and produces `{}`."
        ),
        "inputs": [{"a": False, "b": 0, "c": "", "d": None, "e": [], "f": {}}],
        "exclusion_set": None,
        "settled_by_the_draft": True,
    },
    {
        "name": "exclusion-and-normalisation-order-is-not-observable",
        "why": (
            "DISCRIMINATES NOTHING, and is retained saying so. The "
            "construction is JCS(normalize(P minus exclusion_set)), but under "
            "top-level exclusion the two operations commute: removing a "
            "top-level member cannot create or destroy an empty container "
            "elsewhere. An implementation that applied them in the wrong "
            "order would still produce this digest. A round 12 reviewer "
            "pointed out that the earlier name - "
            "'exclusion-precedes-normalisation' - claimed a property the "
            "vector cannot test."
        ),
        "inputs": [{"chain": "ref", "keep": 1}],
        "exclusion_set": ["chain"],
        "settled_by_the_draft": True,
    },
    {
        "name": "exclusion-scope-resolved-in-02",
        "why": (
            "Open in -01, settled in -02. The two candidate readings were "
            "top-level member-name matching and recursive member-name "
            "matching - not 'path-scoped', which would mean explicit paths "
            "like /inner/chain and was the wrong term for this. -01 section 4 "
            "said only 'the set of fields declared by the payload class'. "
            "-02 section 4.1 settles it: 'The exclusion set is matched "
            "against the top-level member names of P only; a member of the "
            "same name nested inside a member's value is not removed.' Both "
            "readings are recorded below; `specified_by_02` marks the one now "
            "normative, which is the one this implementation had chosen."
        ),
        "inputs": [{"chain": "drop me", "inner": {"chain": "keep me"}}],
        "exclusion_set": ["chain"],
        "settled_by_the_draft": False,
    },
    {
        "name": "nested-emptying-cascades",
        "why": (
            "Normalisation is bottom-up: emptying an inner object can empty "
            "its parent, which can empty its parent. An implementation that "
            "makes a single top-down pass leaves `{\"a\": {\"b\": {}}}`."
        ),
        "inputs": [{"a": {"b": {"c": None}}}],
        "exclusion_set": None,
        "settled_by_the_draft": True,
    },
]


def _digest(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _strip_recursive(value, names):
    """The reading -02 rejected: remove matching names at any depth."""
    if isinstance(value, dict):
        return {k: _strip_recursive(v, names) for k, v in value.items() if k not in names}
    if isinstance(value, list):
        return [_strip_recursive(v, names) for v in value]
    return value


def build():
    out = []
    for vector in VECTORS:
        cases = []
        for payload in vector["inputs"]:
            excluded = vector["exclusion_set"]
            reduced = payload
            if excluded is not None:
                names = set(excluded)
                reduced = {k: v for k, v in payload.items() if k not in names}
            cases.append(
                {
                    "input": payload,
                    "after_exclusion_and_normalisation": strip_absent(reduced),
                    "jcs": jcs_serialize(strip_absent(reduced)),
                    "digest": jcs_n(payload, excluded),
                }
            )
        entry = {
            "name": vector["name"],
            "why": vector["why"],
            "settled_by_01_text": vector["settled_by_the_draft"],
            # [] not null: an empty exclusion set is a set, not an absence.
            "exclusion_set": vector["exclusion_set"] or [],
            "cases": cases,
        }
        # Only meaningful where several inputs are meant to converge.
        if len(cases) > 1:
            entry["all_inputs_share_one_digest"] = (
                len({case["digest"] for case in cases}) == 1
            )
        if vector["name"] == "exclusion-scope-resolved-in-02":
            recursive = _strip_recursive(vector["inputs"][0], set(vector["exclusion_set"]))
            entry["readings"] = {
                "top_level_member_names": {
                    "jcs": cases[0]["jcs"],
                    "digest": cases[0]["digest"],
                    "specified_by_02": True,
                },
                "recursive_member_names": {
                    "jcs": jcs_serialize(strip_absent(recursive)),
                    "digest": _digest(jcs_serialize(strip_absent(recursive))),
                    "specified_by_02": False,
                },
            }
        out.append(entry)
    return out


def main() -> int:
    vectors = build()
    path = HERE / "vectors.json"
    path.write_text(
        json.dumps(
            {
                "spec": "draft-mih-sokolov-scitt-payload-binding-01",
                "status": (
                    "HISTORICAL. jcs-n is withdrawn in -02 (2026-08-24), "
                    "which registers plain jcs in its place and prohibits new "
                    "declarations using jcs-n. These vectors record an "
                    "implementation of the -01 text and are not an "
                    "interoperability contribution."
                ),
                "algorithm": "jcs-n (withdrawn)",
                "construction": (
                    "lowercase_hex(SHA-256(JCS(normalize(P minus exclusion_set))))"
                ),
                "note": (
                    "Produced independently of the draft authors, from the "
                    "-01 text; not cross-validated against another "
                    "implementation. Digests are lowercase hex SHA-256 over "
                    "the UTF-8 JCS serialisation. The exclusion-scope vector "
                    "records both candidate readings of -01 and marks the one "
                    "-02 section 4.1 makes normative."
                ),
                "vectors": vectors,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for vector in vectors:
        marker = " " if vector["settled_by_01_text"] else "*"
        print(
            "%s %-34s %s"
            % (marker, vector["name"], vector["cases"][0]["digest"][:32])
        )
    print("\n* = not settled by the -01 text; -02 section 4.1 settles it")
    print("written:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
