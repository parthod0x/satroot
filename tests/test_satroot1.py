import copy
import json
from pathlib import Path

import pytest

from satroot1 import SatRootError, event_id, load_profile_registry, replay, sha256_hex, signing_payload


ROOT = Path(__file__).resolve().parents[1]


def load_events(name="events_floor1.json"):
    return json.loads((ROOT / "examples" / name).read_text())


def test_replay_demo_ledger():
    state = replay(load_events())
    assert state.symbol == "FLOOR1"
    assert state.supply == 999_000_000
    assert state.balances["issuer"] == 750_000_000
    assert state.balances["alice"] == 150_000_000
    assert state.balances["bob"] == 99_000_000


def test_reject_overspend():
    events = load_events()
    bad = copy.deepcopy(events[-1])
    bad["sequence"] = 4
    bad["prev_event_id"] = event_id(events[-1])
    bad["from"] = "bob"
    bad["amount"] = "999999999999"
    bad["signer"] = "bob"
    events.append(bad)
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_wrong_root():
    events = load_events()
    events[1]["root_id"] = "f" * 64 + ":0"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_zero_amount_transfer():
    events = load_events()
    bad = copy.deepcopy(events[1])
    bad["amount"] = "0"
    events[1] = bad
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_missing_signature():
    events = load_events()
    bad = copy.deepcopy(events[1])
    del bad["signature"]
    events[1] = bad
    with pytest.raises(SatRootError):
        replay(events)


def test_replay_stable_profile_demo():
    state = replay(load_events("events_usdroot1.json"))
    assert state.symbol == "USDROOT1"
    assert state.decimals == 2
    assert state.supply == 24_995_000
    assert state.balances["issuer"] == 23_500_000
    assert state.balances["merchant"] == 1_245_000
    assert state.balances["api_node"] == 250_000


def test_replay_machine_profile_demo():
    state = replay(load_events("events_apicredit1.json"))
    assert state.symbol == "APICREDIT1"
    assert state.decimals == 0
    assert state.supply == 99_800_000
    assert state.balances["issuer"] == 95_000_000
    assert state.balances["tenant_a"] == 3_800_000
    assert state.balances["worker_node"] == 1_000_000


def test_replay_receipt_profile_demo():
    state = replay(load_events("events_receipt1.json"))
    assert state.symbol == "RECEIPT1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["buyer"] == 0
    assert state.balances["archive"] == 0


def test_replay_identity_profile_demo():
    state = replay(load_events("events_identity1.json"))
    assert state.symbol == "IDENTITY1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["node_alpha"] == 0
    assert state.balances["rotated_controller"] == 0


def test_replay_license_profile_demo():
    state = replay(load_events("events_license1.json"))
    assert state.symbol == "LICENSE1"
    assert state.decimals == 0
    assert state.supply == 0
    assert state.balances["issuer"] == 0
    assert state.balances["customer"] == 0
    assert state.balances["archive"] == 0


def test_reject_unknown_profile():
    events = load_events()
    events[0]["profile"] = "SATROOT-UNKNOWN-1"
    events[0]["profile_mode"] = "unknown-mode"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_bad_profile_mode():
    events = load_events("events_usdroot1.json")
    events[0]["profile_mode"] = "wrong-mode"
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_event_id_mismatch():
    events = load_events()
    events[1]["event_id"] = "sha256:" + ("0" * 64)
    with pytest.raises(SatRootError):
        replay(events)


def test_reject_state_hash_mismatch():
    events = load_events()
    events[1]["state_hash"] = "sha256:" + ("0" * 64)
    with pytest.raises(SatRootError):
        replay(events)


def test_accept_matching_event_id_and_state_hash():
    events = load_events()
    probe = replay(events[:2])
    events[1]["state_hash"] = probe.state_hash()
    events[1]["event_id"] = event_id(events[1])
    final_state = replay(events)
    assert final_state.symbol == "FLOOR1"


def test_profile_registry_contains_supported_profiles():
    registry = load_profile_registry()
    assert registry["SATROOT-STABLE-1"]["profile_mode"] == "reference-only"
    assert registry["SATROOT-LICENSE-1"]["required_fields"][-1] == "intended_use"


def test_reject_missing_required_profile_field():
    events = load_events("events_identity1.json")
    del events[0]["subject_id"]
    with pytest.raises(SatRootError):
        replay(events)


def test_signing_payload_excludes_unsigned_fields():
    event = copy.deepcopy(load_events()[1])
    event["event_id"] = "sha256:" + ("1" * 64)
    event["state_hash"] = "sha256:" + ("2" * 64)
    payload = signing_payload(event)
    parsed = json.loads(payload)
    assert "signature" not in parsed
    assert "event_id" not in parsed
    assert "state_hash" not in parsed
    assert parsed["action"] == "transfer"


def test_replay_with_custom_signature_verifier():
    events = load_events()
    prev = event_id(events[0])
    for event in events[1:]:
        event["prev_event_id"] = prev
        event["signature"] = "sha256:" + sha256_hex(signing_payload(event))
        prev = event_id(event)

    def hash_verifier(event, payload):
        return event["signature"] == "sha256:" + sha256_hex(payload)

    state = replay(events, verifier=hash_verifier)
    assert state.symbol == "FLOOR1"
