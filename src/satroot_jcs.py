"""RFC 8785 JSON Canonicalization Scheme, and comparison against SATROOT's.

SATROOT canonicalises with sorted-key, separator-tight, non-ASCII-preserving
JSON. Several drafts in the IETF SCITT orbit use RFC 8785 (JCS) for the same
digest-binding purpose. Whether the two agree is a checkable question, and
this module exists to check it rather than assert it.

The two differ in exactly one respect that can be exercised: **JCS sorts
object keys by UTF-16 code unit, while Python's ``sort_keys=True`` sorts by
Unicode code point.** Those orders *can* diverge - not always - when an
astral-plane key is compared against a high-BMP key, because UTF-16
represents astral characters as surrogate pairs beginning 0xD800-0xDBFF,
which sort below characters in 0xE000-0xFFFF. Two astral keys compare the
same way under both schemes.

Numbers are deliberately out of scope here. RFC 8785 requires ECMAScript
``Number::toString`` semantics, which is a genuinely subtle algorithm; this
implementation rejects floats rather than approximating it. SATROOT never
emits a JSON number for a quantity - all amounts are digit strings - so the
comparison below is unaffected. An implementation intending general JCS
conformance must handle numbers and should not use this module for that.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from satroot1 import SatRootError, canonical_json


def _utf16_sort_key(name: str) -> bytes:
    """RFC 8785 section 3.2.3: sort by UTF-16 code units.

    Lone surrogates are rejected: RFC 8785 requires them to be an error,
    and ``surrogatepass`` would sort them silently.
    """
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SatRootError(f"lone surrogate in object key: {name!r}") from exc
    return name.encode("utf-16-be")


def jcs_serialize(value: Any) -> str:
    """Serialise per RFC 8785, for the value types SATROOT permits."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        raise SatRootError(
            "float serialisation is out of scope; RFC 8785 requires "
            "ECMAScript Number::toString semantics"
        )
    if isinstance(value, int):
        # RFC 8785 requires ECMAScript Number::toString, which switches to
        # exponential form at 1e21 and cannot exactly represent integers
        # beyond 2**53. str() diverges on both. Reject rather than render
        # incorrectly; SATROOT never emits a JSON number for a quantity.
        if abs(value) > 2 ** 53:
            raise SatRootError(
                f"integer {value} exceeds the exactly-representable range "
                "(2**53); ECMAScript Number::toString rendering is not "
                "implemented here"
            )
        return str(value)
    if isinstance(value, str):
        # JSON string escaping is identical between RFC 8785 and Python's
        # json module: short escapes for \\b \\t \\n \\f \\r \\" \\\\, \\uXXXX
        # for other control characters, everything else literal UTF-8.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(jcs_serialize(v) for v in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=_utf16_sort_key)
        return "{" + ",".join(
            json.dumps(k, ensure_ascii=False) + ":" + jcs_serialize(value[k])
            for k in keys
        ) + "}"
    raise SatRootError(f"unsupported type for JCS: {type(value).__name__}")


def compare(value: Any) -> Dict[str, Any]:
    """Serialise one value both ways and report whether they agree."""
    try:
        jcs = jcs_serialize(value)
    except SatRootError as exc:
        return {"agree": None, "error": str(exc)}
    satroot = canonical_json(value)
    return {
        "agree": jcs == satroot,
        "jcs": jcs,
        "satroot": satroot,
    }


def divergence_cases() -> List[Tuple[str, Any]]:
    """Inputs chosen to find disagreement, not to demonstrate agreement."""
    return [
        # Plain records: expected to agree.
        ("ascii keys", {"b": "2", "a": "1", "c": "3"}),
        ("nested", {"z": {"b": 1, "a": 2}, "a": [3, 2, 1]}),
        ("empty containers", {"a": {}, "b": []}),
        ("null and booleans", {"a": None, "b": True, "c": False}),
        # Strings that exercise escaping.
        ("control characters", {"k": "line\nbreak\ttab\x00null"}),
        ("quotes and backslashes", {"k": 'he said "hi" \\ bye'}),
        ("non-ASCII values", {"k": "café — naïve — 日本語"}),
        ("emoji in value", {"k": "receipt 🧾 issued"}),
        # Key ordering: BMP only, expected to agree.
        ("non-ASCII keys, BMP", {"é": 1, "a": 2, "z": 3, "ü": 4}),
        ("CJK keys", {"日": 1, "本": 2, "a": 3}),
        # The documented divergence: non-BMP keys sort differently.
        ("non-BMP key vs BMP key", {"\U0001F600": 1, "＀": 2}),
        ("two non-BMP keys", {"\U0001F600": 1, "\U0001F601": 2}),
        ("mathematical alphanumerics", {"\U0001D400": 1, "�": 2}),
        # Unicode normalisation: neither scheme normalises, so NFC and NFD
        # forms of the same text are different keys in both. Worth pinning.
        # These are genuinely distinct byte sequences: C3 A9 (U+00E9, NFC)
        # and 65 CC 81 (e + U+0301, NFD). Verified by test, because writing
        # them as literals makes the case vacuous if an editor normalises.
        ("NFC vs NFD keys", {"é": 1, "é": 2}),
        ("NFC vs NFD on the value side", {"a": "é", "b": "é"}),
    ]


def run_comparison() -> Dict[str, Any]:
    """Compare both canonicalisations across the divergence cases."""
    results = []
    for label, value in divergence_cases():
        outcome = compare(value)
        results.append({"case": label, **outcome})
    agreements = [r for r in results if r.get("agree") is True]
    disagreements = [r for r in results if r.get("agree") is False]
    return {
        "total": len(results),
        "agree": len(agreements),
        "disagree": len(disagreements),
        "disagreeing_cases": [r["case"] for r in disagreements],
        "results": results,
    }


def main() -> int:
    report = run_comparison()
    for r in report["results"]:
        mark = {True: "agree   ", False: "DIVERGE ", None: "skipped "}[r.get("agree")]
        print(f"{mark} {r['case']}")
        if r.get("agree") is False:
            # Escape for terminals that cannot render astral-plane characters.
            print(f"           jcs     : {r['jcs'].encode('unicode_escape').decode()}")
            print(f"           satroot : {r['satroot'].encode('unicode_escape').decode()}")
    print(f"\n{report['agree']}/{report['total']} agree, {report['disagree']} diverge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# jcs-n, per draft-mih-sokolov-scitt-payload-binding-01
# ---------------------------------------------------------------------------


def strip_absent(value: Any) -> Any:
    """Remove, bottom-up and recursively, members whose value is null, an
    empty array, or an empty object.

    This is step 1 of ``jcs-n`` in draft-mih-sokolov-scitt-payload-binding-01.
    Note that the "n" denotes *absent-field* normalisation, not Unicode
    normalisation: the draft applies RFC 8785 without adding NFC or any other
    Unicode normalisation step.
    """
    if isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            v = strip_absent(v)
            if v is None or v == {} or v == []:
                continue
            cleaned[k] = v
        return cleaned
    if isinstance(value, list):
        return [strip_absent(v) for v in value]
    return value


def jcs_n(value: Any, exclusion_set: Optional[Iterable[str]] = None) -> str:
    """The ``jcs-n`` digest, per draft-mih-sokolov-scitt-payload-binding-01.

    The full construction is::

        lowercase_hex(SHA-256(JCS(normalize(P minus exclusion_set))))

    The exclusion set is declared by the payload class and covers fields
    carrying the derived identifier itself, or referencing other records in
    a chain, so that a record's content address stays stable regardless of
    what later chains to it. Omitting it computes only steps 1-4 of section
    3.1, which is not the complete construction.
    """
    import hashlib

    if not isinstance(value, dict):
        raise SatRootError("jcs-n is defined over a JSON object")
    reduced = value
    if exclusion_set is not None:
        excluded = set(exclusion_set)  # materialise once; generators are consumed
        reduced = {k: v for k, v in value.items() if k not in excluded}
    canonical = jcs_serialize(strip_absent(reduced))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def satroot_digest(value: Any) -> str:
    """SATROOT's equivalent: canonicalise as-is, SHA-256, hex."""
    import hashlib

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _illustrative_digest_difference(value: Any) -> Dict[str, Any]:
    """Illustrative only - NOT a meaningful comparison.

    The payload-binding draft states that digests are comparable only
    within one digest context. Comparing a jcs-n digest against SATROOT's
    compares two deliberately different contexts, so a difference carries
    no information. Retained to demonstrate that, not to report it.
    """
    return {
        "agree": jcs_n(value) == satroot_digest(value),
        "jcs_n": jcs_n(value),
        "satroot": satroot_digest(value),
        "stripped": strip_absent(value) != value,
    }
