"""Generate test vectors for `jcs-n`, offered to the payload-binding draft.

`draft-mih-sokolov-scitt-payload-binding-01` defines `jcs-n` and publishes no
test vectors: Appendix A walks an example and stops before the digest. Every
divergence recorded in `docs/CANONICALISATION.md` while implementing it from
the text is one a vector would have prevented, which makes vectors a more
useful contribution than a list of corrections.

These six are chosen to separate implementations, not to demonstrate that a
correct one works. Each targets a specific decision an implementer must make
and could plausibly get wrong:

1. absent / null / empty-array / empty-object all collapse to the same digest
2. an emptied object *inside an array* is not removed with it
3. falsy-but-present values survive
4. exclusion applies before normalisation
5. exclusion scope is unspecified by the draft - this is the open question
6. nested emptying cascades bottom-up

Vector 5 is the one worth the draft authors' attention. The others pin
readings the text already settles; 5 pins a reading it does not.

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
            "Section 3.1 removes members whose value is null, an empty array "
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
        "name": "exclusion-precedes-normalisation",
        "why": (
            "The construction is JCS(normalize(P minus exclusion_set)): the "
            "exclusion set is removed first. Here excluding `chain` leaves "
            "`{\"keep\": 1}`; normalising first would remove nothing "
            "different, so the orders coincide - which is precisely why the "
            "next vector matters."
        ),
        "inputs": [{"chain": "ref", "keep": 1}],
        "exclusion_set": ["chain"],
        "settled_by_the_draft": True,
    },
    {
        "name": "exclusion-scope-is-unspecified",
        "why": (
            "THE OPEN QUESTION. The draft does not say whether the exclusion "
            "set is name-scoped (remove every member with that name, at any "
            "depth) or path-scoped (top-level names only). Section 13.2's "
            "only registered example is the bare pair {capsule_id, chain}, "
            "which cannot distinguish the two, and section 3.1 says only "
            "'minus exclusion_set'. Given this input the two readings produce "
            "different digests, so two conforming-looking implementations "
            "disagree on the same payload class. This vector records the "
            "top-level reading; the draft should state which is intended."
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
        digests = {case["digest"] for case in cases}
        out.append(
            {
                "name": vector["name"],
                "why": vector["why"],
                "settled_by_the_draft": vector["settled_by_the_draft"],
                "exclusion_set": vector["exclusion_set"],
                "all_inputs_share_one_digest": len(digests) == 1,
                "cases": cases,
            }
        )
    return out


def main() -> int:
    vectors = build()
    path = HERE / "vectors.json"
    path.write_text(
        json.dumps(
            {
                "spec": "draft-mih-sokolov-scitt-payload-binding-01",
                "algorithm": "jcs-n",
                "construction": (
                    "lowercase_hex(SHA-256(JCS(normalize(P minus exclusion_set))))"
                ),
                "note": (
                    "Produced by an independent implementation written from "
                    "the draft text. Digests are lowercase hex SHA-256 over "
                    "the UTF-8 JCS serialisation. Vector "
                    "'exclusion-scope-is-unspecified' records a reading the "
                    "draft does not settle."
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
        marker = " " if vector["settled_by_the_draft"] else "*"
        print(
            "%s %-34s %s"
            % (marker, vector["name"], vector["cases"][0]["digest"][:32])
        )
    print("\n* = the draft does not settle this; the digest records our reading")
    print("written:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
