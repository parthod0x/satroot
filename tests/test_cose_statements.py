"""COSE_Sign1 encoding of SATROOT events.

These pin the properties that make the encoding useful to anyone working
on SCITT: the CBOR is deterministic and matches RFC 8949's published test
vectors, the signature is over the raw Sig_structure so it interoperates
with other COSE implementations, and the payload still replays to the
same state hash the ledger had before encoding.
"""

import json

import pytest

import satroot1 as sr
import satroot_cose as sc
from satroot1 import SatRootError


# RFC 8949 Appendix A, restricted to the types COSE structures use.
RFC8949_VECTORS = [
    (0, "00"), (1, "01"), (10, "0a"), (23, "17"), (24, "1818"), (100, "1864"),
    (1000, "1903e8"), (1000000, "1a000f4240"),
    (-1, "20"), (-10, "29"), (-100, "3863"), (-1000, "3903e7"),
    (b"", "40"), (b"\x01\x02\x03\x04", "4401020304"),
    ("", "60"), ("a", "6161"), ("IETF", "6449455446"),
    ([], "80"), ([1, 2, 3], "83010203"),
    ({1: 2, 3: 4}, "a201020304"),
]


@pytest.mark.parametrize("value,expected", RFC8949_VECTORS)
def test_cbor_matches_rfc8949_vectors(value, expected):
    assert sc.cbor_encode(value).hex() == expected


def test_cbor_roundtrips():
    for value, _ in RFC8949_VECTORS:
        assert sc.cbor_decode(sc.cbor_encode(value)) == value


def test_cbor_map_keys_are_sorted_by_encoded_bytes():
    """RFC 8949 4.2.1 - deterministic encoding requires this ordering."""
    a = sc.cbor_encode({3: "c", 1: "a", 2: "b"})
    b = sc.cbor_encode({1: "a", 2: "b", 3: "c"})
    assert a == b


def test_cbor_rejects_booleans_explicitly():
    """bool subclasses int; encoding it as one would be a silent corruption."""
    with pytest.raises(SatRootError):
        sc.cbor_encode(True)


def _ledger():
    demo = sr.bootstrap_machine_credit_demo_ledger(symbol="COSE1", name="COSE demo")
    bundle = sr.bootstrap_signed_ledger_bundle(demo["events"], scheme="ed25519")
    return bundle


@pytest.mark.skipif(not sr.ed25519_available(), reason="cryptography not installed")
def test_ledger_encodes_and_every_statement_verifies():
    bundle = _ledger()
    material = bundle["material"]
    statements = sc.encode_ledger(
        bundle["signed_events"],
        issuer="satroot-test",
        private_keys=material["private_keys"],
        signer_key_ids=material["signer_key_map"],
    )
    assert len(statements) == len(bundle["signed_events"])

    for statement in statements:
        parsed = sc.parse_statement(statement)
        assert parsed["alg"] == sc.ALG_EDDSA
        assert parsed["content_type"] == sc.SATROOT_CONTENT_TYPE
        result = sc.verify_statement(statement, material["public_keys"][parsed["kid"]])
        assert result["signature_valid"] is True


@pytest.mark.skipif(not sr.ed25519_available(), reason="cryptography not installed")
def test_every_statement_shares_the_namespace_as_subject():
    """A Transparency Service groups a ledger by subject; this is that key."""
    bundle = _ledger()
    root_id = bundle["signed_events"][0]["root_id"]
    statements = sc.encode_ledger(
        bundle["signed_events"],
        issuer="satroot-test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )
    assert {sc.parse_statement(s)["subject"] for s in statements} == {root_id}


@pytest.mark.skipif(not sr.ed25519_available(), reason="cryptography not installed")
def test_encoded_payloads_replay_to_the_same_state_hash():
    """The encoding must be lossless with respect to protocol semantics."""
    bundle = _ledger()
    statements = sc.encode_ledger(
        bundle["signed_events"],
        issuer="satroot-test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )
    recovered = [json.loads(sc.parse_statement(s)["payload"]) for s in statements]
    verifier = sr.make_ed25519_verifier(bundle["material"]["public_keys"])
    assert sr.replay(recovered, verifier=verifier).state_hash() == bundle["final_state_hash"]


@pytest.mark.skipif(not sr.ed25519_available(), reason="cryptography not installed")
def test_tampered_statement_fails_verification():
    bundle = _ledger()
    statements = sc.encode_ledger(
        bundle["signed_events"],
        issuer="satroot-test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )
    mutated = bytearray(statements[1])
    mutated[-1] ^= 0x01
    parsed = sc.parse_statement(bytes(mutated))
    result = sc.verify_statement(bytes(mutated), bundle["material"]["public_keys"][parsed["kid"]])
    assert result["signature_valid"] is False


def test_empty_ledger_is_rejected():
    with pytest.raises(SatRootError):
        sc.encode_ledger([], issuer="x", private_keys={}, signer_key_ids={})
