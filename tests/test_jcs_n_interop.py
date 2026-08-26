"""SATROOT digests against jcs-n, from draft-mih-sokolov-scitt-payload-binding-01.

jcs-n is: strip absent members (null, empty array, empty object) bottom-up
and recursively, apply RFC 8785, SHA-256, lowercase hex. The "n" is
absent-field normalisation, NOT Unicode normalisation - the draft adds no
NFC step.

These tests pin an interoperability result: the two schemes disagree on the
ordinary SATROOT state snapshot, because that snapshot carries members jcs-n
removes.
"""

import pytest

import satroot1 as sr
import satroot_jcs as jcs
from satroot1 import SatRootError


def _snapshot(**kwargs):
    genesis = sr.scaffold_genesis_record(
        symbol="JCSN", name="jcs-n interop",
        root_id=sr.build_scaffold_root_id(),
        mint_authority="issuer", decimals=0, initial_balance="1",
        **kwargs,
    )
    signed = sr.sign_event_record(genesis, scheme="demo", key_id=None, signer=None)
    return sr.replay([signed]).commitment_snapshot()


def test_jcs_n_strips_members_satroot_retains():
    """The concrete divergence, on a record the protocol produces normally."""
    snapshot = _snapshot()
    stripped = sorted(set(snapshot) - set(jcs.strip_absent(snapshot)))
    # An unprofiled ledger with no frozen accounts loses three members.
    assert stripped == ["frozen_accounts", "profile", "profile_mode"]
    assert jcs.jcs_n(snapshot) != jcs.satroot_digest(snapshot)


def test_absent_field_stripping_is_recursive_and_bottom_up():
    """A nested object emptied by stripping is itself stripped."""
    record = {"a": 1, "b": {"c": None, "d": []}, "e": {"f": {"g": None}}}
    assert jcs.strip_absent(record) == {"a": 1}


def test_records_without_absent_members_agree():
    record = {"a": "1", "b": {"c": "2"}, "d": ["x"]}
    assert jcs.jcs_n(record) == jcs.satroot_digest(record)


def test_jcs_n_does_not_normalise_unicode():
    """The 'n' is absent-field normalisation only; NFC and NFD stay distinct."""
    nfc, nfd = "é", "é"
    record = {nfc: 1, nfd: 2}
    assert len(record) == 2
    assert jcs.strip_absent(record) == record
    # Both forms survive; no NFC folding is applied.
    assert nfd in jcs.jcs_serialize(jcs.strip_absent(record))


def test_digest_is_lowercase_hex_of_expected_length():
    digest = jcs.jcs_n({"a": 1})
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


# --- The findings worth reporting, as opposed to the arithmetic ------------


def test_only_object_members_are_removed_not_array_elements():
    """The conforming reading, which RFC 8259 settles unambiguously.

    RFC 8259 defines `member = string name-separator value`, occurring only
    inside an object; array contents are elements. The draft uses the terms
    correspondingly - "empty array (zero elements)" against "empty object
    (zero members)". So an object that empties inside an array stays in the
    array, and its parent member survives.

    Not an ambiguity in the specification. It is, however, a place a
    generic recursive prune would diverge, which a test vector prevents.
    """
    record = {"a": [{"b": None}]}
    assert jcs.strip_absent(record) == {"a": [{}]}
    assert jcs.jcs_n(record) != jcs.jcs_n({})


def test_array_elements_that_are_null_or_empty_are_retained():
    assert jcs.strip_absent({"a": [None]}) == {"a": [None]}
    assert jcs.strip_absent({"a": [{}, []]}) == {"a": [{}, []]}


def test_falsy_but_present_values_must_survive():
    """A nonconforming implementation would strip these; a vector prevents it.

    Note the draft's own wording is slightly imprecise here: it says members
    "explicitly set to a non-null value are not removed", but an empty array
    and an empty object are themselves non-null values and *are* removed.
    """
    record = {"a": False, "b": 0, "c": "", "d": None, "e": [], "f": {}}
    assert jcs.strip_absent(record) == {"a": False, "b": 0, "c": ""}


def test_jcs_n_deliberately_collapses_four_distinct_inputs():
    """Absent, null, empty array and empty object share one digest."""
    digests = {
        jcs.jcs_n({}),
        jcs.jcs_n({"x": None}),
        jcs.jcs_n({"x": []}),
        jcs.jcs_n({"x": {}}),
    }
    assert len(digests) == 1


def test_exclusion_set_is_applied_before_normalisation():
    assert jcs.jcs_n({"a": 1, "id": "x"}, exclusion_set=["id"]) == jcs.jcs_n({"a": 1})


def test_integers_beyond_exact_representation_are_rejected():
    """Guarded at 2**53, the exactly-representable boundary.

    ECMAScript Number::toString also switches to exponential form at 1e21,
    which str() does not; both are beyond this implementation's scope, and
    the 2**53 guard is the stricter of the two.
    """
    import pytest
    from satroot1 import SatRootError

    jcs.jcs_serialize(2 ** 53)
    with pytest.raises(SatRootError):
        jcs.jcs_serialize(10 ** 21)


def test_nfc_and_nfd_fixtures_are_genuinely_distinct():
    """Guards against an editor silently normalising the source file."""
    import unicodedata

    cases = dict(jcs.divergence_cases())
    record = cases["NFC vs NFD keys"]
    assert len(record) == 2, "fixture collapsed - the case would be vacuous"
    keys = list(record)
    assert unicodedata.normalize("NFC", keys[0]) == unicodedata.normalize("NFC", keys[1])
    assert keys[0] != keys[1]


def test_lone_surrogate_in_a_value_raises_satroot_error():
    """RFC 8785 3.2.2.2 - and symmetrically with keys.

    The guard used to cover keys only, so a lone surrogate in a value passed
    jcs_serialize and surfaced as UnicodeEncodeError from inside jcs_n.
    """
    lone = "\ud800"
    with pytest.raises(SatRootError):
        jcs.jcs_serialize({"a": lone})
    with pytest.raises(SatRootError):
        jcs.jcs_serialize({lone: "a"})
    with pytest.raises(SatRootError):
        jcs.jcs_n({"a": lone})


def test_deep_nesting_raises_satroot_error_not_recursion_error():
    deep = {}
    node = deep
    for _ in range(jcs.MAX_JSON_DEPTH + 10):
        node["a"] = {}
        node = node["a"]
    with pytest.raises(SatRootError):
        jcs.jcs_serialize(deep)
    with pytest.raises(SatRootError):
        jcs.strip_absent(deep)


def test_exclusion_set_is_top_level_name_scoped():
    """Pins the reading the draft does not settle.

    Section 13.2's only registered example is {capsule_id, chain}, which
    cannot distinguish name-scoped from path-scoped exclusion. This
    implementation excludes top-level names only; a nested member sharing
    the name survives. Recorded so the choice is visible rather than
    accidental.
    """
    payload = {"chain": "drop me", "inner": {"chain": "keep me"}}
    assert jcs.jcs_n(payload, ["chain"]) == jcs.jcs_n({"inner": {"chain": "keep me"}})
