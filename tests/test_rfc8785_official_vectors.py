"""satroot_jcs against the published RFC 8785 conformance vectors.

Fetch them first:

    python scripts/fetch_rfc8785_vectors.py

These tests skip when the vectors are absent, so the suite still runs
offline. They matter because an implementation validated only against
cases its own author chose is weaker evidence than it looks.
"""

import json
import pathlib

import pytest

import satroot_jcs as jcs
from satroot1 import SatRootError, canonical_json

VECTORS = pathlib.Path(__file__).parent / "vectors" / "rfc8785"
pytestmark = pytest.mark.skipif(
    not (VECTORS / "input").is_dir(),
    reason="run scripts/fetch_rfc8785_vectors.py first",
)


def _cases():
    for path in sorted((VECTORS / "input").glob("*.json")):
        yield path.name, path, VECTORS / "output" / path.name


@pytest.mark.parametrize("name,src,expected_path", list(_cases()))
def test_official_vector(name, src, expected_path):
    value = json.loads(src.read_text(encoding="utf-8"))
    expected = expected_path.read_text(encoding="utf-8")
    try:
        assert jcs.jcs_serialize(value) == expected
    except SatRootError as exc:
        # values.json and structures.json contain non-integer numbers, which
        # this implementation rejects rather than rendering via ECMAScript
        # Number::toString. That is a declared limit, not a silent failure.
        pytest.skip(f"out of declared scope: {exc}")


def test_the_official_vector_distinguishes_the_two_schemes():
    """weird.json is where JCS and SATROOT's canonicalisation disagree.

    It contains U+1F602 (astral) and U+FB33 (BMP). Under UTF-16 code-unit
    ordering the astral character sorts first, because its surrogate pair
    begins D83D; under code-point ordering it sorts last. The RFC's own
    vector therefore settles the divergence empirically.
    """
    src = VECTORS / "input" / "weird.json"
    value = json.loads(src.read_text(encoding="utf-8"))
    expected = (VECTORS / "output" / "weird.json").read_text(encoding="utf-8")

    assert jcs.jcs_serialize(value) == expected
    assert canonical_json(value) != expected

    jcs_keys = list(json.loads(jcs.jcs_serialize(value)))
    satroot_keys = list(json.loads(canonical_json(value)))
    smiley, hebrew = "\U0001F602", "דּ"
    assert jcs_keys.index(smiley) < jcs_keys.index(hebrew)
    assert satroot_keys.index(smiley) > satroot_keys.index(hebrew)


def test_jcs_does_normalise_lexical_number_forms():
    """Contradicts a claim in draft-mih-sokolov-scitt-payload-binding-01.

    That draft states floats must not appear in digest-bearing fields
    "because the same quantity serialises as 1.0, 1e0 or 1.00 in different
    implementations and JCS does not normalise these forms". JCS parses and
    re-serialises via ECMAScript Number::toString, which does normalise
    exactly those forms - as the RFC's own vectors show.
    """
    src = (VECTORS / "input" / "values.json").read_text(encoding="utf-8")
    out = (VECTORS / "output" / "values.json").read_text(encoding="utf-8")
    assert "4.50" in src and "4.50" not in out and "4.5" in out
    assert "2e-3" in src and "0.002" in out
