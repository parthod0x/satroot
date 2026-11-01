"""A producer continuing an existing version-0.1 ledger (3.0.1).

3.0.0 let `replay` and `verify_signed_ledger_bundle` admit an unbound ledger
with `allow_unbound_keys`, but the helpers a producer appends and exports
with replayed without it. So a service could verify its customers' existing
ledgers and do nothing else with them, short of re-signing - which moves
every state hash and orphans the anchors those customers hold.
"""
from __future__ import annotations

import pytest

from satroot1 import (
    MACHINE_DEMO_CATALOG_FIELD_DEFAULTS,
    MACHINE_DEMO_CATALOG_PROFILE,
    SatRootError,
    annotate_ledger_events,
    append_signed_event_to_ledger,
    derive_ed25519_public_keys,
    ed25519_available,
    make_ed25519_signer,
    make_ed25519_verifier,
    replay,
    scaffold_event_from_ledger,
    scaffold_genesis_record,
    scaffold_machine_credit_consumption_event,
    sign_event_record,
)

PRIVATE_KEYS = {"issuer-key": "11" * 32, "agent-key": "22" * 32}
SIGNER_KEY_IDS = {"issuer": "issuer-key", "agent": "agent-key"}


def _unbound_ledger():
    genesis = scaffold_genesis_record(
        symbol="CRAGENT",
        name="Agent credits",
        root_id="b" * 64 + ":0",
        mint_authority="issuer",
        decimals=0,
        initial_balance="1000",
        profile=MACHINE_DEMO_CATALOG_PROFILE,
        profile_fields=dict(MACHINE_DEMO_CATALOG_FIELD_DEFAULTS),
    )
    signer = make_ed25519_signer(PRIVATE_KEYS)
    events = [sign_event_record(genesis, scheme="ed25519", key_id="issuer-key", signer=signer)]
    assert events[0]["version"] == "0.1" and "account_keys" not in events[0]
    return events, signer, make_ed25519_verifier(derive_ed25519_public_keys(PRIVATE_KEYS))


def _grant(events, verifier, **flag):
    return scaffold_event_from_ledger(events, action="transfer", signer="issuer", from_account="issuer",
                                      to_account="agent", amount="50", verifier=verifier, **flag)


def test_the_helpers_refuse_an_unbound_ledger_by_default():
    if not ed25519_available():
        pytest.skip("ed25519 extra not installed")
    events, signer, verifier = _unbound_ledger()
    with pytest.raises(SatRootError, match="unbound|allow_unbound_keys|not bound"):
        _grant(events, verifier)
    with pytest.raises(SatRootError, match="unbound|allow_unbound_keys|not bound"):
        annotate_ledger_events(events, verifier=verifier)
    with pytest.raises(SatRootError, match="unbound|allow_unbound_keys|not bound"):
        scaffold_machine_credit_consumption_event(events, signer="agent", amount="1", verifier=verifier)
    event = _grant(events, verifier, allow_unbound_keys=True)
    with pytest.raises(SatRootError, match="unbound|allow_unbound_keys|not bound"):
        append_signed_event_to_ledger(events, event, scheme="ed25519", signer_key_ids=SIGNER_KEY_IDS,
                                      signer=signer, verifier=verifier)


def test_a_producer_continues_an_unbound_ledger_knowingly_and_its_hashes_do_not_move():
    if not ed25519_available():
        pytest.skip("ed25519 extra not installed")
    events, signer, verifier = _unbound_ledger()
    before = replay(events, verifier=verifier, allow_unbound_keys=True).state_hash()

    event = _grant(events, verifier, allow_unbound_keys=True)
    events = append_signed_event_to_ledger(events, event, scheme="ed25519", signer_key_ids=SIGNER_KEY_IDS,
                                           signer=signer, verifier=verifier, allow_unbound_keys=True)
    burn = scaffold_machine_credit_consumption_event(events, signer="agent", amount="7", verifier=verifier,
                                                     allow_unbound_keys=True)
    events = append_signed_event_to_ledger(events, burn, scheme="ed25519", signer_key_ids=SIGNER_KEY_IDS,
                                           signer=signer, verifier=verifier, allow_unbound_keys=True)

    # Continued, not converted: still 0.1, no binding event inserted.
    assert [e["version"] for e in events] == ["0.1"] * 3
    assert [e["action"] for e in events[1:]] == ["transfer", "burn"]
    state = replay(events, verifier=verifier, allow_unbound_keys=True)
    assert state.snapshot()["balances"] == {"agent": "43", "issuer": "950"}

    annotated = annotate_ledger_events(events, verifier=verifier, allow_unbound_keys=True)
    assert annotated[0]["state_hash"] == before
    assert annotated[-1]["state_hash"] == state.state_hash()
