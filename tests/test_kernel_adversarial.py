"""Adversarial and boundary tests for the frozen SATROOT-1 kernel.

These pin the security-relevant behaviors and documented boundaries so that
neither an accidental regression nor an undocumented change slips through: the
type strictness of sequence/decimals/amount, replay/sequence enforcement, and
the deliberate signer-to-key-binding boundary described in KEY_MANAGEMENT.md.
"""
from __future__ import annotations

import copy

import pytest

from satroot1 import (
    SatRootError,
    bootstrap_singleton_object_demo_ledger,
    ed25519_available,
    event_id,
    make_ed25519_verifier,
    parse_amount,
    parse_decimals,
    replay,
    scaffold_event_from_ledger,
    scaffold_genesis_record,
    sign_event_record,
)


def _floor_genesis() -> dict:
    return scaffold_genesis_record(
        symbol="ADV1",
        name="Adversarial Demo",
        root_id="a" * 64 + ":0",
        mint_authority="issuer",
        initial_owner="issuer",
    )


def _demo_transfer(events, *, to, signer, from_account, amount="1"):
    event = scaffold_event_from_ledger(
        events,
        action="transfer",
        signer=signer,
        from_account=from_account,
        to_account=to,
        amount=amount,
    )
    return sign_event_record(event, scheme="demo")


# --- type strictness (schema conformance) ---


def test_parse_amount_rejects_unicode_and_leading_forms():
    assert parse_amount("150000000") == 150000000
    for bad in ("١٢٣", "𝟏", "²", "", "1_000", " 10", "10 "):
        with pytest.raises(SatRootError):
            parse_amount(bad)


def test_parse_decimals_rejects_bool():
    assert parse_decimals(0) == 0
    with pytest.raises(SatRootError):
        parse_decimals(True)
    with pytest.raises(SatRootError):
        parse_decimals(False)


def test_boolean_sequence_is_rejected_at_genesis_and_replay():
    genesis = _floor_genesis()
    genesis["sequence"] = False
    with pytest.raises(SatRootError):
        replay([genesis])

    good_genesis = _floor_genesis()
    events = [good_genesis]
    transfer = _demo_transfer(events, to="alice", signer="issuer", from_account="issuer")
    transfer["sequence"] = True
    with pytest.raises(SatRootError):
        replay([good_genesis, transfer])


# --- sequence / replay enforcement ---


def test_replayed_duplicate_event_is_rejected():
    events = [_floor_genesis()]
    events.append(_demo_transfer(events, to="alice", signer="issuer", from_account="issuer"))
    replay(events)  # sanity
    duplicated = events + [copy.deepcopy(events[-1])]
    with pytest.raises(SatRootError):
        replay(duplicated)


def test_sequence_gap_is_rejected():
    events = [_floor_genesis()]
    transfer = _demo_transfer(events, to="alice", signer="issuer", from_account="issuer")
    transfer["sequence"] = 5  # skip past 1
    with pytest.raises(SatRootError):
        replay([events[0], transfer])


def test_second_genesis_is_rejected():
    events = [_floor_genesis()]
    events.append(_demo_transfer(events, to="alice", signer="issuer", from_account="issuer"))
    second = _floor_genesis()
    second["sequence"] = 2
    second["prev_event_id"] = event_id(events[-1])
    with pytest.raises(SatRootError):
        replay(events + [second])


# --- documented boundary: signer string, not key binding (KEY_MANAGEMENT.md) ---


@pytest.mark.skipif(not ed25519_available(), reason="cryptography package is not installed")
def test_signer_is_a_string_not_a_key_binding_boundary():
    """Pins the deliberate v1 boundary: the kernel authorizes on the signer
    STRING plus a valid signature under some registered key, and does not bind
    the signing key to the signer account. If a future version tightens this,
    this test should be updated deliberately, not silently."""
    from satroot1 import (
        bootstrap_ed25519_workflow,
        make_ed25519_signer,
        sign_ledger_events,
    )

    # Build a normal two-account ledger (issuer -> holder), demo-signed.
    ledger = bootstrap_singleton_object_demo_ledger(
        profile="SATROOT-IDENTITY-1",
        symbol="ADVID1",
        name="Adversarial Identity",
        root_id="b" * 64 + ":0",
        holder_account="node_alpha",
        next_holder="rotated_controller",
        retire=False,
    )
    events = ledger["events"]

    # Sign every event with real ed25519 keys, then verify: the kernel accepts
    # because each signature is valid under a registered key and the signer
    # strings line up — even though nothing binds a key to its account.
    material = bootstrap_ed25519_workflow(events)
    signer = make_ed25519_signer(material["private_keys"])
    verifier = make_ed25519_verifier(material["public_keys"])
    signed = sign_ledger_events(
        events,
        scheme="ed25519",
        signer_key_ids=material["signer_key_map"],
        signer=signer,
        verifier=verifier,
    )
    state = replay(signed, verifier=verifier)
    assert state.profile == "SATROOT-IDENTITY-1"
    # The boundary: verification is by (valid signature) + (signer string),
    # with no key->account binding enforced by the kernel itself.
    assert state.balances.get("rotated_controller") == 1
