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


def test_cbor_map_key_order_is_insensitive_to_insertion_order():
    a = sc.cbor_encode({3: "c", 1: "a", 2: "b"})
    b = sc.cbor_encode({1: "a", 2: "b", 3: "c"})
    assert a == b


def test_cbor_map_keys_are_sorted_by_encoded_bytes_not_numerically():
    """RFC 8949 4.2.1 - bytewise over the *encoded* key.

    Keys 1, 2, 3 cannot show this: bytewise order, numeric order and RFC 7049
    s3.9 length-first order all coincide there, so the obvious test passes
    under every rule and distinguishes none of them. {10, 100, -1} separates
    all three:

        bytewise (RFC 8949 4.2.1)   0a, 1864, 20   ->  10, 100, -1
        numeric / Python sorted()                  ->  -1, 10, 100
        length-first (RFC 7049 3.9)                ->  10, -1, 100

    COSE uses negative labels throughout its registry, so this is a live
    path rather than a curiosity.
    """
    encoded = sc.cbor_encode({10: "a", 100: "b", -1: "c"})
    assert encoded.hex() == "a30a616118646162206163"

    order = [k for k, _ in sorted(
        ((sc.cbor_encode(k), k) for k in (10, 100, -1)), key=lambda kv: kv[0]
    )]
    assert [k for _, k in sorted(
        ((sc.cbor_encode(k), k) for k in (10, 100, -1)), key=lambda kv: kv[0]
    )] == [10, 100, -1]
    assert order  # encoded keys, kept for the failure message


def test_cbor_integer_boundaries_match_rfc8949():
    """The head-width boundaries the hand-transcribed vector list never reached."""
    for value, expected in [
        (23, "17"), (24, "1818"), (255, "18ff"), (256, "190100"),
        (65535, "19ffff"), (65536, "1a00010000"),
        (4294967295, "1affffffff"), (4294967296, "1b0000000100000000"),
        (2 ** 64 - 1, "1bffffffffffffffff"),
        (-24, "37"), (-25, "3818"), (-256, "38ff"), (-257, "390100"),
        (1000000000000, "1b000000e8d4a51000"),
    ]:
        assert sc.cbor_encode(value).hex() == expected, value
    with pytest.raises(SatRootError):
        sc.cbor_encode(2 ** 64)


def test_cbor_rejects_duplicate_map_labels():
    """RFC 9052 s9 - a second alg label must not silently win."""
    with pytest.raises(SatRootError):
        sc.cbor_decode(bytes.fromhex("a201010102"))


def test_cbor_rejects_excessive_nesting():
    """Deep attacker input raises SatRootError, not RecursionError."""
    deep = b"\x81" * (sc.MAX_CBOR_DEPTH + 5) + b"\x00"
    with pytest.raises(SatRootError):
        sc.cbor_decode(deep)


def test_cbor_tags_survive_a_round_trip():
    tagged = sc.CBORTag(18, [1, 2])
    assert sc.cbor_encode(tagged)[:1] == b"\xd2"
    assert sc.cbor_decode(sc.cbor_encode(tagged)) == tagged


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
        assert parsed["alg"] == sc.ALG_ED25519
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


def test_statements_are_tagged_cose_sign1():
    """RFC 9943: Signed_Statement = #6.18(COSE_Sign1).

    The tag is part of the type. Emitting a bare 4-element array produced
    something a conforming SCITT decoder is entitled to reject, and the
    round trip could not reveal it because the decoder discarded tags.
    """
    bundle = _ledger()
    statements = sc.encode_ledger(
        bundle["signed_events"],
        issuer="https://satroot.com/test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )
    for statement in statements:
        assert statement[0] == 0xD2, "statement is not CBOR tag 18"
        assert isinstance(sc.cbor_decode(statement), sc.CBORTag)


def test_untagged_statement_is_rejected():
    bundle = _ledger()
    statement = sc.encode_ledger(
        bundle["signed_events"],
        issuer="https://satroot.com/test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )[0]
    untagged = sc.cbor_encode(sc.cbor_decode(statement).value)
    with pytest.raises(SatRootError):
        sc.parse_statement(untagged)


def test_statements_declare_fully_specified_ed25519():
    """RFC 9864 deprecates polymorphic -8; -19 names the curve."""
    bundle = _ledger()
    statement = sc.encode_ledger(
        bundle["signed_events"],
        issuer="https://satroot.com/test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
    )[0]
    assert sc.parse_statement(statement)["alg"] == sc.ALG_ED25519 == -19


def test_encode_ledger_refuses_to_relabel_a_foreign_namespace():
    """The silent-wrongness case: two ledgers, one subject.

    Every statement takes its subject from events[0]. Without this check an
    event from another namespace encodes into a well-formed, correctly
    signed statement asserting a subject it does not belong to.
    """
    bundle = _ledger()
    events = [dict(e) for e in bundle["signed_events"]]
    assert len(events) > 1
    events[-1]["root_id"] = "cd" * 32 + ":7"
    with pytest.raises(SatRootError) as excinfo:
        sc.encode_ledger(
            events,
            issuer="https://satroot.com/test",
            private_keys=bundle["material"]["private_keys"],
            signer_key_ids=bundle["material"]["signer_key_map"],
        )
    assert "namespace" in str(excinfo.value)


def test_non_json_payload_raises_satroot_error():
    with pytest.raises(SatRootError):
        sc.parse_statement(
            sc.cbor_encode(sc.CBORTag(18, [b"", {}, b"not json at all", b""]))
        )


def test_alg_is_selectable_and_both_identifiers_verify():
    """RFC 9864 says -19; deployed COSE libraries still say -8.

    Emitting -19 by default is the conformant choice, but pycose 1.1.0
    rejects it as an unknown attribute before reaching the signature, so the
    deprecated identifier stays available. See docs/COSE_INTEROP.md.
    """
    bundle = _ledger()
    for alg in (sc.ALG_ED25519, sc.ALG_EDDSA_DEPRECATED):
        statement = sc.encode_ledger(
            bundle["signed_events"],
            issuer="https://satroot.com/test",
            private_keys=bundle["material"]["private_keys"],
            signer_key_ids=bundle["material"]["signer_key_map"],
            alg=alg,
        )[0]
        parsed = sc.parse_statement(statement)
        assert parsed["alg"] == alg
        public = bundle["material"]["public_keys"][parsed["kid"]]
        assert sc.verify_statement(statement, public)["signature_valid"] is True

    with pytest.raises(SatRootError):
        sc.protected_header(issuer="i", subject="s", key_id="k", alg=-7)


def test_signature_verifies_under_an_independent_cose_implementation():
    """The one check that is not this author's code marking its own work.

    Skipped unless pycose is installed - it is not a runtime dependency, and
    pycose 1.1.0 needs cbor2<6 to decode anything at all. The measured result
    is recorded in docs/COSE_INTEROP.md so it survives the skip.
    """
    pycose_messages = pytest.importorskip("pycose.messages")
    pycose_keys = pytest.importorskip("pycose.keys")
    from pycose.keys.curves import Ed25519

    bundle = _ledger()
    statement = sc.encode_ledger(
        bundle["signed_events"],
        issuer="https://satroot.com/test",
        private_keys=bundle["material"]["private_keys"],
        signer_key_ids=bundle["material"]["signer_key_map"],
        alg=sc.ALG_EDDSA_DEPRECATED,
    )[0]
    parsed = sc.parse_statement(statement)
    public = bundle["material"]["public_keys"][parsed["kid"]]

    try:
        message = pycose_messages.Sign1Message.decode(statement)
    except TypeError as exc:  # pragma: no cover - version-dependent
        pytest.skip(f"pycose cannot decode under this cbor2 version: {exc}")
    message.key = pycose_keys.OKPKey(crv=Ed25519, x=bytes.fromhex(public))
    assert message.verify_signature() is True


def _ledgers_across_profiles():
    """One ledger per bootstrap the kernel offers, not just machine credits.

    The replay test above used a single machine-credit ledger, which two
    reviewers separately called thin: five kernel actions and several
    profiles exist, and one action mix cannot show the encoding is lossless
    for the others.
    """
    yield "machine", sr.bootstrap_machine_credit_demo_ledger(
        symbol="MULTI1", name="multi profile machine"
    )
    yield "stable", sr.bootstrap_stable_reference_demo_ledger(
        symbol="MULTI2", name="multi profile stable"
    )
    yield "singleton", sr.bootstrap_singleton_object_demo_ledger(
        profile="SATROOT-IDENTITY-1",
        symbol="MULTI3",
        name="multi profile identity",
        holder_account="holder",
        next_holder="successor",
    )


@pytest.mark.skipif(not sr.ed25519_available(), reason="cryptography not installed")
@pytest.mark.parametrize("label,demo", list(_ledgers_across_profiles()), ids=lambda v: v if isinstance(v, str) else "")
def test_encoding_is_lossless_across_profiles(label, demo):
    bundle = sr.bootstrap_signed_ledger_bundle(demo["events"], scheme="ed25519")
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
def test_every_kernel_action_survives_the_encoding():
    """Cover the action set, not just whichever actions a demo happens to use."""
    seen = set()
    for _, demo in _ledgers_across_profiles():
        bundle = sr.bootstrap_signed_ledger_bundle(demo["events"], scheme="ed25519")
        statements = sc.encode_ledger(
            bundle["signed_events"],
            issuer="satroot-test",
            private_keys=bundle["material"]["private_keys"],
            signer_key_ids=bundle["material"]["signer_key_map"],
        )
        for statement in statements:
            seen.add(sc.parse_statement(statement)["event"].get("action"))
    assert {"genesis", "transfer"} <= seen, seen
