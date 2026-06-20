"""SATROOT-1 v0.1 reference balance engine.

This is intentionally small and dependency-free.
It validates ledger arithmetic, sequence order, root consistency,
and basic authority placeholders. Real deployments must replace
`verify_signature_placeholder` with actual signature verification.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import hmac
import importlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence


class SatRootError(ValueError):
    pass


ROOT_ID_RE = re.compile(r"^[a-fA-F0-9]{64}:[0-9]+$")
PROFILE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "protocol" / "satroot1.profile-registry.json"
SignatureVerifier = Callable[[Dict[str, Any], str], bool]
SignerFunction = Callable[[str, str], str]
SUPPORTED_SIGNATURE_SCHEMES = {"demo", "hmac-sha256", "ed25519"}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@functools.lru_cache(maxsize=1)
def load_profile_registry() -> Dict[str, Dict[str, Any]]:
    with PROFILE_REGISTRY_PATH.open("r", encoding="utf-8") as f:
        registry = json.load(f)

    if registry.get("protocol") != "SATROOT-1" or registry.get("version") != "0.1":
        raise SatRootError("unsupported profile registry version")

    profiles = registry.get("profiles")
    if not isinstance(profiles, list):
        raise SatRootError("invalid profile registry format")

    loaded: Dict[str, Dict[str, Any]] = {}
    for entry in profiles:
        if not isinstance(entry, dict):
            raise SatRootError("invalid profile registry entry")
        require_fields(entry, ["profile", "profile_mode", "required_genesis_fields"])
        profile = entry["profile"]
        profile_mode = entry["profile_mode"]
        required_fields = entry["required_genesis_fields"]
        if not isinstance(required_fields, list) or not all(isinstance(field, str) for field in required_fields):
            raise SatRootError(f"invalid required_genesis_fields for {profile!r}")
        loaded[profile] = {
            "profile_mode": profile_mode,
            "required_fields": required_fields,
        }
    return loaded


def event_id(event: Dict[str, Any]) -> str:
    """Return the canonical event hash.

    The event_id excludes `event_id` and `state_hash` if present so records can
    carry their own ID while still attaching a post-application state commitment.
    """
    cleaned = {k: v for k, v in event.items() if k not in {"event_id", "state_hash"}}
    return "sha256:" + sha256_hex(canonical_json(cleaned))


def signing_payload(event: Dict[str, Any]) -> str:
    """Return the canonical payload that should be signed for an event.

    Signature material excludes fields that are either transport metadata or
    post-application commitments.
    """
    cleaned = {k: v for k, v in event.items() if k not in {"signature", "event_id", "state_hash"}}
    return canonical_json(cleaned)


def parse_amount(value: str) -> int:
    if not isinstance(value, str) or not value.isdigit():
        raise SatRootError(f"invalid amount: {value!r}")
    return int(value)


def demo_signature_verifier(event: Dict[str, Any], payload: str) -> bool:
    """Default demo verifier used by the reference engine.

    v0.1 test records may use signature='demo'. Production records must use
    a real signature scheme over `signing_payload(event)`.
    """
    return event.get("signature_scheme", "demo") == "demo" and event.get("signature") == "demo"


def _coerce_secret(secret: str | bytes) -> bytes:
    if isinstance(secret, bytes):
        return secret
    if isinstance(secret, str):
        return secret.encode("utf-8")
    raise SatRootError("unsupported secret type")


def hmac_sha256_sign(payload: str, secret: str | bytes) -> str:
    secret_bytes = _coerce_secret(secret)
    digest = hmac.new(secret_bytes, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return "hmac-sha256:" + digest


def make_hmac_sha256_verifier(shared_secrets: Mapping[str, str | bytes]) -> SignatureVerifier:
    """Build a reference verifier for shared-secret HMAC signatures.

    This is useful for controlled environments and integration testing.
    It is not a public-key signature scheme.
    """

    def verifier(event: Dict[str, Any], payload: str) -> bool:
        if event.get("signature_scheme") != "hmac-sha256":
            return False
        key_id = event.get("signature_key_id")
        if not isinstance(key_id, str) or not key_id:
            return False
        secret = shared_secrets.get(key_id)
        if secret is None:
            return False
        expected = hmac_sha256_sign(payload, secret)
        signature = event.get("signature")
        return isinstance(signature, str) and hmac.compare_digest(signature, expected)

    return verifier


def ed25519_available() -> bool:
    return importlib.util.find_spec("cryptography") is not None


def _load_ed25519_primitives() -> tuple[Any, Any, Any]:
    if not ed25519_available():
        raise SatRootError("cryptography package is required for ed25519 support")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

    return Ed25519PrivateKey, Ed25519PublicKey, serialization


def _coerce_hex_bytes(value: str, label: str, expected_length: Optional[int] = None) -> bytes:
    if not isinstance(value, str):
        raise SatRootError(f"{label} must be a hex string")
    try:
        raw = bytes.fromhex(value)
    except ValueError as exc:
        raise SatRootError(f"invalid hex for {label}") from exc
    if expected_length is not None and len(raw) != expected_length:
        raise SatRootError(f"invalid byte length for {label}")
    return raw


def ed25519_public_key_hex(private_key_hex: str) -> str:
    Ed25519PrivateKey, _, serialization = _load_ed25519_primitives()
    private_key = Ed25519PrivateKey.from_private_bytes(_coerce_hex_bytes(private_key_hex, "private_key_hex", 32))
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return public_bytes.hex()


def ed25519_sign(payload: str, private_key_hex: str) -> str:
    Ed25519PrivateKey, _, _ = _load_ed25519_primitives()
    private_key = Ed25519PrivateKey.from_private_bytes(_coerce_hex_bytes(private_key_hex, "private_key_hex", 32))
    signature = private_key.sign(payload.encode("utf-8"))
    return "ed25519:" + signature.hex()


def make_ed25519_verifier(public_keys: Mapping[str, str]) -> SignatureVerifier:
    """Build a reference verifier for Ed25519 signatures.

    This path requires the optional `cryptography` dependency and uses raw
    32-byte public keys encoded as lowercase hex strings.
    """
    _, Ed25519PublicKey, _ = _load_ed25519_primitives()

    def verifier(event: Dict[str, Any], payload: str) -> bool:
        if event.get("signature_scheme") != "ed25519":
            return False
        key_id = event.get("signature_key_id")
        if not isinstance(key_id, str) or not key_id:
            return False
        public_key_hex = public_keys.get(key_id)
        if public_key_hex is None:
            return False
        signature = event.get("signature")
        if not isinstance(signature, str) or not signature.startswith("ed25519:"):
            return False
        try:
            public_key = Ed25519PublicKey.from_public_bytes(_coerce_hex_bytes(public_key_hex, "public_key_hex", 32))
            signature_bytes = _coerce_hex_bytes(signature.split(":", 1)[1], "signature", 64)
            public_key.verify(signature_bytes, payload.encode("utf-8"))
            return True
        except Exception:
            return False

    return verifier


def make_hmac_sha256_signer(shared_secrets: Mapping[str, str | bytes]) -> SignerFunction:
    def signer(payload: str, key_id: str) -> str:
        secret = shared_secrets.get(key_id)
        if secret is None:
            raise SatRootError(f"missing secret for key_id: {key_id}")
        return hmac_sha256_sign(payload, secret)

    return signer


def make_ed25519_signer(private_keys: Mapping[str, str]) -> SignerFunction:
    def signer(payload: str, key_id: str) -> str:
        private_key_hex = private_keys.get(key_id)
        if private_key_hex is None:
            raise SatRootError(f"missing private key for key_id: {key_id}")
        return ed25519_sign(payload, private_key_hex)

    return signer


def require_fields(event: Dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if field not in event]
    if missing:
        raise SatRootError("missing required field(s): " + ", ".join(missing))


def parse_positive_amount(value: str) -> int:
    amount = parse_amount(value)
    if amount <= 0:
        raise SatRootError(f"amount must be positive: {value!r}")
    return amount


def validate_root_id(root_id: str) -> None:
    if not isinstance(root_id, str) or not ROOT_ID_RE.fullmatch(root_id):
        raise SatRootError(f"invalid root_id: {root_id!r}")


def parse_decimals(value: Any) -> int:
    if not isinstance(value, int) or value < 0 or value > 18:
        raise SatRootError(f"invalid decimals: {value!r}")
    return value


def require_account_name(name: Any, field_name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise SatRootError(f"invalid account name for {field_name}: {name!r}")
    return name


def validate_signature_metadata(event: Dict[str, Any]) -> None:
    scheme = event.get("signature_scheme", "demo")
    if not isinstance(scheme, str) or scheme not in SUPPORTED_SIGNATURE_SCHEMES:
        raise SatRootError(f"unsupported signature_scheme: {scheme!r}")

    key_id = event.get("signature_key_id")
    if scheme == "demo":
        if key_id is not None:
            raise SatRootError("signature_key_id is not allowed for demo signatures")
        return

    if not isinstance(key_id, str) or not key_id.strip():
        raise SatRootError(f"signature_key_id is required for {scheme}")


def validate_stated_event_id(event: Dict[str, Any]) -> None:
    stated = event.get("event_id")
    if stated is not None and stated != event_id(event):
        raise SatRootError("event_id mismatch")


def validate_profile_genesis(event: Dict[str, Any]) -> None:
    profile = event.get("profile")
    if profile is None:
        return

    rules = load_profile_registry().get(profile)
    if rules is None:
        raise SatRootError(f"unsupported profile: {profile}")

    require_fields(event, ["profile_mode", *rules["required_fields"]])
    if event.get("profile_mode") != rules["profile_mode"]:
        raise SatRootError(f"bad profile_mode for {profile}")


def validate_state_hash(event: Dict[str, Any], state: "SatRootState") -> None:
    stated = event.get("state_hash")
    if stated is not None and stated != state.state_hash():
        raise SatRootError("state_hash mismatch")


@dataclass
class SatRootState:
    root_id: str
    symbol: str
    name: str
    decimals: int
    max_supply: Optional[int]
    mint_authority: str
    profile: Optional[str] = None
    profile_mode: Optional[str] = None
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
            "profile": self.profile,
            "profile_mode": self.profile_mode,
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
    validate_root_id(event["root_id"])
    validate_stated_event_id(event)
    validate_profile_genesis(event)
    if event.get("transfer_model") != "account-ledger":
        raise SatRootError("unsupported transfer_model")

    initial = {
        require_account_name(acct, "initial_balances"): parse_amount(amount)
        for acct, amount in event.get("initial_balances", {}).items()
    }
    supply = sum(initial.values())
    max_supply = parse_amount(event["max_supply"]) if event.get("max_supply") is not None else None
    if max_supply is not None and supply > max_supply:
        raise SatRootError("initial supply exceeds max supply")

    state = SatRootState(
        root_id=event["root_id"],
        symbol=event["symbol"],
        name=event["name"],
        decimals=parse_decimals(event.get("decimals", 0)),
        max_supply=max_supply,
        mint_authority=event["mint_authority"],
        profile=event.get("profile"),
        profile_mode=event.get("profile_mode"),
        balances=initial,
        supply=supply,
        sequence=0,
        last_event_id=event_id(event),
    )
    validate_state_hash(event, state)
    return state


def verify_signature(event: Dict[str, Any], verifier: SignatureVerifier) -> None:
    payload = signing_payload(event)
    if not verifier(event, payload):
        raise SatRootError("signature verification failed")


def require_next_event(state: SatRootState, event: Dict[str, Any], verifier: SignatureVerifier) -> None:
    require_fields(event, ["protocol", "version", "action", "root_id", "sequence", "prev_event_id", "signer", "signature"])
    if event.get("protocol") != "SATROOT-1" or event.get("version") != "0.1":
        raise SatRootError("unsupported protocol/version")
    if event.get("root_id") != state.root_id:
        raise SatRootError("root_id mismatch")
    if event.get("sequence") != state.sequence + 1:
        raise SatRootError("bad sequence")
    if event.get("prev_event_id") != state.last_event_id:
        raise SatRootError("bad prev_event_id")
    validate_stated_event_id(event)
    validate_signature_metadata(event)
    if event.get("profile") not in (None, state.profile):
        raise SatRootError("profile mismatch")
    if event.get("profile_mode") not in (None, state.profile_mode):
        raise SatRootError("profile_mode mismatch")
    verify_signature(event, verifier)


def apply_event(state: SatRootState, event: Dict[str, Any], verifier: SignatureVerifier = demo_signature_verifier) -> SatRootState:
    next_state = copy.deepcopy(state)
    require_next_event(next_state, event, verifier)

    action = event.get("action")
    amount = parse_positive_amount(event.get("amount", "0"))

    if action == "mint":
        require_fields(event, ["to", "amount"])
        if event.get("signer") != next_state.mint_authority:
            raise SatRootError("unauthorized mint")
        to = require_account_name(event["to"], "to")
        if next_state.max_supply is not None and next_state.supply + amount > next_state.max_supply:
            raise SatRootError("mint exceeds max supply")
        next_state.balances[to] = next_state.balances.get(to, 0) + amount
        next_state.supply += amount

    elif action == "transfer":
        require_fields(event, ["from", "to", "amount"])
        sender = require_account_name(event["from"], "from")
        recipient = require_account_name(event["to"], "to")
        # v0.1 placeholder: signer must equal sender account string.
        if event.get("signer") != sender:
            raise SatRootError("unauthorized transfer")
        if next_state.balances.get(sender, 0) < amount:
            raise SatRootError("insufficient balance")
        next_state.balances[sender] -= amount
        next_state.balances[recipient] = next_state.balances.get(recipient, 0) + amount

    elif action == "burn":
        require_fields(event, ["from", "amount"])
        burner = require_account_name(event["from"], "from")
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
    validate_state_hash(event, next_state)
    return next_state


def replay(events: Iterable[Dict[str, Any]], verifier: SignatureVerifier = demo_signature_verifier) -> SatRootState:
    iterator = iter(events)
    try:
        first = next(iterator)
    except StopIteration as exc:
        raise SatRootError("empty ledger") from exc

    state = apply_genesis(first)
    for event in iterator:
        state = apply_event(state, event, verifier=verifier)
    return state


def sign_event_record(
    event: Dict[str, Any],
    *,
    scheme: str,
    key_id: Optional[str] = None,
    signer: Optional[SignerFunction] = None,
) -> Dict[str, Any]:
    signed = copy.deepcopy(event)
    if scheme == "demo":
        signed.pop("signature_key_id", None)
        signed["signature_scheme"] = "demo"
        signed["signature"] = "demo"
    else:
        if signer is None:
            raise SatRootError("signer function is required for non-demo signatures")
        if not isinstance(key_id, str) or not key_id.strip():
            raise SatRootError("key_id is required for non-demo signatures")
        signed["signature_scheme"] = scheme
        signed["signature_key_id"] = key_id
        signed["signature"] = signer(signing_payload(signed), key_id)
    signed["event_id"] = event_id(signed)
    return signed


def sign_ledger_events(
    events: Sequence[Dict[str, Any]],
    *,
    scheme: str,
    signer_key_ids: Optional[Mapping[str, str]] = None,
    signer: Optional[SignerFunction] = None,
    verifier: SignatureVerifier = demo_signature_verifier,
    include_state_hash: bool = False,
) -> list[Dict[str, Any]]:
    if not events:
        raise SatRootError("empty ledger")

    signed_events = copy.deepcopy(list(events))
    state = apply_genesis(signed_events[0])
    previous_event_id = state.last_event_id

    for event in signed_events[1:]:
        event["prev_event_id"] = previous_event_id
        if scheme == "demo":
            signed = sign_event_record(event, scheme="demo")
        else:
            signer_name = event.get("signer")
            if not isinstance(signer_name, str) or not signer_name:
                raise SatRootError("signer is required for non-demo signatures")
            if signer_key_ids is None:
                raise SatRootError("signer_key_ids are required for non-demo signatures")
            key_id = signer_key_ids.get(signer_name)
            if key_id is None:
                raise SatRootError(f"missing signer_key_id for signer: {signer_name}")
            signed = sign_event_record(event, scheme=scheme, key_id=key_id, signer=signer)

        next_state = apply_event(state, signed, verifier=verifier)
        if include_state_hash:
            signed["state_hash"] = next_state.state_hash()
        event.clear()
        event.update(signed)
        state = next_state
        previous_event_id = state.last_event_id

    return signed_events


def _load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _write_output(data: Any, output_path: Optional[str]) -> None:
    rendered = _dump_json(data)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
    else:
        sys.stdout.write(rendered)


def build_cli_parser() -> Any:
    import argparse

    parser = argparse.ArgumentParser(description="SATROOT-1 utilities")
    subparsers = parser.add_subparsers(dest="command")

    replay_parser = subparsers.add_parser("replay", help="Replay a SATROOT-1 JSON event file")
    replay_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")

    sign_event_parser = subparsers.add_parser("sign-event", help="Sign a single SATROOT-1 event record")
    sign_event_parser.add_argument("event_json", help="Path to a JSON event object")
    sign_event_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], required=True)
    sign_event_parser.add_argument("--key-id", help="Signature key identifier for non-demo schemes")
    sign_event_parser.add_argument("--secret", help="Shared secret for hmac-sha256 signing")
    sign_event_parser.add_argument("--private-key-hex", help="Hex-encoded Ed25519 private key")
    sign_event_parser.add_argument("--output", help="Optional output path")

    sign_ledger_parser = subparsers.add_parser("sign-ledger", help="Sign a SATROOT-1 ledger array")
    sign_ledger_parser.add_argument("events_json", help="Path to JSON array of SATROOT-1 events")
    sign_ledger_parser.add_argument("--scheme", choices=["demo", "hmac-sha256", "ed25519"], required=True)
    sign_ledger_parser.add_argument("--signer-key-map-json", help="Path to JSON mapping signer -> key_id")
    sign_ledger_parser.add_argument("--secrets-json", help="Path to JSON mapping key_id -> shared secret")
    sign_ledger_parser.add_argument("--private-keys-json", help="Path to JSON mapping key_id -> private key hex")
    sign_ledger_parser.add_argument("--include-state-hash", action="store_true", help="Attach state_hash to each signed event")
    sign_ledger_parser.add_argument("--output", help="Optional output path")

    return parser


def _signer_and_verifier_from_args(args: Any) -> tuple[Optional[SignerFunction], SignatureVerifier, Optional[Mapping[str, str]]]:
    if args.scheme == "demo":
        return None, demo_signature_verifier, None
    if args.scheme == "hmac-sha256":
        if not args.secrets_json:
            raise SatRootError("--secrets-json is required for hmac-sha256")
        secrets = _load_json_file(args.secrets_json)
        if not isinstance(secrets, dict):
            raise SatRootError("secrets-json must contain an object")
        return make_hmac_sha256_signer(secrets), make_hmac_sha256_verifier(secrets), secrets
    if args.scheme == "ed25519":
        if not args.private_keys_json:
            raise SatRootError("--private-keys-json is required for ed25519")
        private_keys = _load_json_file(args.private_keys_json)
        if not isinstance(private_keys, dict):
            raise SatRootError("private-keys-json must contain an object")
        public_keys = {key_id: ed25519_public_key_hex(private_key_hex) for key_id, private_key_hex in private_keys.items()}
        return make_ed25519_signer(private_keys), make_ed25519_verifier(public_keys), private_keys
    raise SatRootError(f"unsupported scheme: {args.scheme}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_cli_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if argv is None and len(sys.argv) == 2:
            args = parser.parse_args(["replay", sys.argv[1]])
        else:
            parser.print_help()
            return 2

    if args.command == "replay":
        events = _load_json_file(args.events_json)
        result = replay(events)
        print(canonical_json(result.snapshot()))
        print("state_hash=" + result.state_hash())
        return 0

    if args.command == "sign-event":
        event = _load_json_file(args.event_json)
        if not isinstance(event, dict):
            raise SatRootError("event_json must contain a JSON object")
        if args.scheme == "demo":
            signed = sign_event_record(event, scheme="demo")
        elif args.scheme == "hmac-sha256":
            if not args.secret or not args.key_id:
                raise SatRootError("--secret and --key-id are required for hmac-sha256")
            signed = sign_event_record(
                event,
                scheme="hmac-sha256",
                key_id=args.key_id,
                signer=make_hmac_sha256_signer({args.key_id: args.secret}),
            )
        elif args.scheme == "ed25519":
            if not args.private_key_hex or not args.key_id:
                raise SatRootError("--private-key-hex and --key-id are required for ed25519")
            signed = sign_event_record(
                event,
                scheme="ed25519",
                key_id=args.key_id,
                signer=make_ed25519_signer({args.key_id: args.private_key_hex}),
            )
        else:
            raise SatRootError(f"unsupported scheme: {args.scheme}")
        _write_output(signed, args.output)
        return 0

    if args.command == "sign-ledger":
        events = _load_json_file(args.events_json)
        if not isinstance(events, list):
            raise SatRootError("events_json must contain a JSON array")
        signer, verifier, _ = _signer_and_verifier_from_args(args)
        signer_key_ids = None
        if args.scheme != "demo":
            if not args.signer_key_map_json:
                raise SatRootError("--signer-key-map-json is required for non-demo ledger signing")
            signer_key_ids = _load_json_file(args.signer_key_map_json)
            if not isinstance(signer_key_ids, dict):
                raise SatRootError("signer-key-map-json must contain an object")
        signed_ledger = sign_ledger_events(
            events,
            scheme=args.scheme,
            signer_key_ids=signer_key_ids,
            signer=signer,
            verifier=verifier,
            include_state_hash=args.include_state_hash,
        )
        _write_output(signed_ledger, args.output)
        return 0

    raise SatRootError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
