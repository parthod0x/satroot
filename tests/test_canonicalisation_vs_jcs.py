"""SATROOT canonicalisation against RFC 8785 (JCS).

These pin an empirical result rather than an assumption: the two schemes
agree on every input class SATROOT permits, and diverge only on object
keys containing characters outside the Basic Multilingual Plane, which
the schema does not allow in field names.
"""

import pytest

import satroot_jcs as jcs
from satroot1 import SatRootError, canonical_json


def test_schemes_agree_on_everything_satroot_permits():
    report = jcs.run_comparison()
    assert report["disagree"] == 2, report["disagreeing_cases"]
    assert set(report["disagreeing_cases"]) == {
        "non-BMP key vs BMP key",
        "mathematical alphanumerics",
    }


def test_divergence_is_exactly_utf16_versus_codepoint_key_order():
    record = {"\U0001F600": 1, "＀": 2}
    j = jcs.jcs_serialize(record)
    s = canonical_json(record)
    assert j != s
    # JCS puts the astral character first (surrogate pair sorts low).
    assert j.index("\U0001F600") < j.index("＀")
    # Code-point ordering puts it last.
    assert s.index("\U0001F600") > s.index("＀")


def test_no_schema_valid_satroot_record_can_reach_the_divergence():
    """Field names are ASCII, so the divergence is unreachable in practice."""
    from satroot1 import scaffold_genesis_record, build_scaffold_root_id

    genesis = scaffold_genesis_record(
        symbol="JCS1", name="jcs", root_id=build_scaffold_root_id(),
        mint_authority="issuer", decimals=0, initial_balance="1",
    )

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)

    assert all(k.isascii() for k in keys(genesis))
    assert jcs.jcs_serialize(genesis) == canonical_json(genesis)


def test_neither_scheme_normalises_unicode():
    nfc, nfd = "é", "é"
    assert nfc != nfd
    record = {nfc: 1, nfd: 2}
    assert len(record) == 2
    # Both schemes agree, and both keep the two forms distinct.
    assert jcs.jcs_serialize(record) == canonical_json(record)
    assert "é" in jcs.jcs_serialize(record)


def test_floats_are_rejected_rather_than_approximated():
    with pytest.raises(SatRootError):
        jcs.jcs_serialize({"a": 1.5})
