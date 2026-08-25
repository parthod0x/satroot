"""SATROOT digests against jcs-n, from draft-mih-sokolov-scitt-payload-binding-01.

jcs-n is: strip absent members (null, empty array, empty object) bottom-up
and recursively, apply RFC 8785, SHA-256, lowercase hex. The "n" is
absent-field normalisation, NOT Unicode normalisation - the draft adds no
NFC step.

These tests pin an interoperability result: the two schemes disagree on the
ordinary SATROOT state snapshot, because that snapshot carries members jcs-n
removes.
"""

import satroot1 as sr
import satroot_jcs as jcs


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
