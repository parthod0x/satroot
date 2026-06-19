import copy
import json
from pathlib import Path

import pytest

from satroot1 import SatRootError, event_id, replay


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
