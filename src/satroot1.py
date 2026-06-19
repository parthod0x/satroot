"""SATROOT-1 v0.1 reference balance engine.

This is intentionally small and dependency-free.
It validates ledger arithmetic, sequence order, root consistency,
and basic authority placeholders. Real deployments must replace
`verify_signature_placeholder` with actual signature verification.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional


class SatRootError(ValueError):
    pass


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def event_id(event: Dict[str, Any]) -> str:
    """Return the canonical event hash.

    The event_id excludes `event_id` if present so records can carry their own ID.
    """
    cleaned = {k: v for k, v in event.items() if k != "event_id"}
    return "sha256:" + sha256_hex(canonical_json(cleaned))


def parse_amount(value: str) -> int:
    if not isinstance(value, str) or not value.isdigit():
        raise SatRootError(f"invalid amount: {value!r}")
    return int(value)


def verify_signature_placeholder(event: Dict[str, Any]) -> bool:
    """Placeholder for real signature checks.

    v0.1 test records may use signature='demo'. Production records must use
    a real signature scheme over canonical_json(event without signature).
    """
    return event.get("signature") == "demo"


def require_fields(event: Dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in event]
    if missing:
        raise SatRootError("missing required field(s): " + ", ".join(missing))


def parse_positive_amount(value: str) -> int:
    amount = parse_amount(value)
    if amount <= 0:
        raise SatRootError(f"amount must be positive: {value!r}")
    return amount


@dataclass
class SatRootState:
    root_id: str
    symbol: str
    name: str
    decimals: int
    max_supply: Optional[int]
    mint_authority: str
    balances: Dict[str, int] = field(default_factory=dict)
    supply: int = 0
    sequence: int = 0
    last_event_id: Optional[str] = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "root_id": self.root_id,
            "symbol": self.symbol,
            "name": self.name,
            "decimals": self.decimals,
            "max_supply": str(self.max_supply) if self.max_supply is not None else None,
            "mint_authority": self.mint_authority,
            "balances": {k: str(v) for k, v in sorted(self.balances.items()) if v != 0},
            "supply": str(self.supply),
            "sequence": self.sequence,
            "last_event_id": self.last_event_id,
        }

    def state_hash(self) -> str:
        return "sha256:" + sha256_hex(canonical_json(self.snapshot()))


def apply_genesis(event: Dict[str, Any]) -> SatRootState:
    require_fields(
        event,
        [
            "protocol",
            "version",
            "action",
            "root_id",
            "sequence",
            "symbol",
            "name",
            "decimals",
            "max_supply",
            "mint_authority",
            "initial_balances",
        ],
    )
    if event.get("protocol") != "SATROOT-1" or event.get("version") != "0.1":
        raise SatRootError("unsupported protocol/version")
    if event.get("action") != "genesis":
        raise SatRootError("first event must be genesis")
    if event.get("sequence") != 0:
        raise SatRootError("genesis sequence must be 0")

    initial = {acct: parse_amount(amount) for acct, amount in event.get("initial_balances", {}).items()}
    supply = sum(initial.values())
    max_supply = parse_amount(event["max_supply"]) if event.get("max_supply") is not None else None
    if max_supply is not None and supply > max_supply:
        raise SatRootError("initial supply exceeds max supply")

    state = SatRootState(
        root_id=event["root_id"],
        symbol=event["symbol"],
        name=event["name"],
        decimals=int(event.get("decimals", 0)),
        max_supply=max_supply,
        mint_authority=event["mint_authority"],
        balances=initial,
        supply=supply,
        sequence=0,
        last_event_id=event_id(event),
    )
    return state


def require_next_event(state: SatRootState, event: Dict[str, Any]) -> None:
    require_fields(event, ["protocol", "version", "action", "root_id", "sequence", "prev_event_id", "signer", "signature"])
    if event.get("protocol") != "SATROOT-1" or event.get("version") != "0.1":
        raise SatRootError("unsupported protocol/version")
    if event.get("root_id") != state.root_id:
        raise SatRootError("root_id mismatch")
    if event.get("sequence") != state.sequence + 1:
        raise SatRootError("bad sequence")
    if event.get("prev_event_id") != state.last_event_id:
        raise SatRootError("bad prev_event_id")
    if not verify_signature_placeholder(event):
        raise SatRootError("signature verification failed")


def apply_event(state: SatRootState, event: Dict[str, Any]) -> SatRootState:
    next_state = copy.deepcopy(state)
    require_next_event(next_state, event)

    action = event.get("action")
    amount = parse_positive_amount(event.get("amount", "0"))

    if action == "mint":
        require_fields(event, ["to", "amount"])
        if event.get("signer") != next_state.mint_authority:
            raise SatRootError("unauthorized mint")
        to = event["to"]
        if next_state.max_supply is not None and next_state.supply + amount > next_state.max_supply:
            raise SatRootError("mint exceeds max supply")
        next_state.balances[to] = next_state.balances.get(to, 0) + amount
        next_state.supply += amount

    elif action == "transfer":
        require_fields(event, ["from", "to", "amount"])
        sender = event["from"]
        recipient = event["to"]
        # v0.1 placeholder: signer must equal sender account string.
        if event.get("signer") != sender:
            raise SatRootError("unauthorized transfer")
        if next_state.balances.get(sender, 0) < amount:
            raise SatRootError("insufficient balance")
        next_state.balances[sender] -= amount
        next_state.balances[recipient] = next_state.balances.get(recipient, 0) + amount

    elif action == "burn":
        require_fields(event, ["from", "amount"])
        burner = event["from"]
        if event.get("signer") != burner:
            raise SatRootError("unauthorized burn")
        if next_state.balances.get(burner, 0) < amount:
            raise SatRootError("insufficient balance")
        next_state.balances[burner] -= amount
        next_state.supply -= amount

    else:
        raise SatRootError(f"unsupported action: {action}")

    next_state.sequence = event["sequence"]
    next_state.last_event_id = event_id(event)
    return next_state


def replay(events: Iterable[Dict[str, Any]]) -> SatRootState:
    iterator = iter(events)
    try:
        first = next(iterator)
    except StopIteration as exc:
        raise SatRootError("empty ledger") from exc

    state = apply_genesis(first)
    for event in iterator:
        state = apply_event(state, event)
    return state


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Replay a SATROOT-1 JSON event file")
    parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    args = parser.parse_args()
    with open(args.events_json, "r", encoding="utf-8") as f:
        events = json.load(f)
    result = replay(events)
    print(canonical_json(result.snapshot()))
    print("state_hash=" + result.state_hash())
