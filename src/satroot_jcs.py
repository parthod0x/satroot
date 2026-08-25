"""RFC 8785 JSON Canonicalization Scheme, and comparison against SATROOT's.

SATROOT canonicalises with sorted-key, separator-tight, non-ASCII-preserving
JSON. Several drafts in the IETF SCITT orbit use RFC 8785 (JCS) for the same
digest-binding purpose. Whether the two agree is a checkable question, and
this module exists to check it rather than assert it.

The two differ in exactly one respect that can be exercised: **JCS sorts
object keys by UTF-16 code unit, while Python's ``sort_keys=True`` sorts by
Unicode code point.** Those orders diverge whenever a key contains a
character outside the Basic Multilingual Plane, because UTF-16 represents
such characters as surrogate pairs beginning with 0xD800-0xDBFF, which sort
below characters in the range 0xE000-0xFFFF.

Numbers are deliberately out of scope here. RFC 8785 requires ECMAScript
``Number::toString`` semantics, which is a genuinely subtle algorithm; this
implementation rejects floats rather than approximating it. SATROOT never
emits a JSON number for a quantity - all amounts are digit strings - so the
comparison below is unaffected. An implementation intending general JCS
conformance must handle numbers and should not use this module for that.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from satroot1 import SatRootError, canonical_json


def _utf16_sort_key(name: str) -> bytes:
    """RFC 8785 section 3.2.3: sort by UTF-16 code units."""
    return name.encode("utf-16-be", errors="surrogatepass")


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
        # Written with explicit escapes: as literals, the source file's own
        # encoding collapses them and the case becomes vacuous.
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
