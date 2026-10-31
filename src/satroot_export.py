"""Offline verifier for an export of a signed SATROOT ledger with an action log
and RFC 3161 timestamp anchors (the format satledger produces). Apache-2.0.

Run it from the installed satroot package, outside the export:

    pip install "satroot[crypto,validation]>=3"
    python -I -m satroot_export /path/to/export
    python -I -m satroot_export /path/to/export --expect-action-head sha256:... \
        --expect-genesis sha256:... --public-keys-json keys-you-kept.json

Why from the package and not from the export. Until satroot 3.0.0 this code
travelled inside every export as `verify_export.py`, beside a `tokenverify.py`
holding the timestamp authorities it trusts. An external review replaced the
export's `tokenverify.py` and the export still passed: the party under
examination supplied the examining code and its trust list. The verifier and
the authority list now come from the published package; `-I` keeps the
current directory off the import path; and the verifier refuses to run if any
module it has loaded resolves inside the export.

What it establishes, and what it does not, is stated in the result and in
the notes it prints: completeness needs a head you retained, and the keys and
genesis are the export's own unless you pin them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import satroot1 as sr

from satroot_tsa import TokenError, verify_token

GENESIS_PREV = "genesis"

SIGNED_FIELDS = ("agent_id", "seq", "prev_hash", "recorded_at", "kind", "detail")
ENVELOPE_FIELDS = ("entry_hash", "key_id", "signature")
ALLOWED_FIELDS = frozenset(SIGNED_FIELDS + ENVELOPE_FIELDS)


class VerificationError(Exception):
    """Raised when an export fails a structural, chain or signature check."""


# ---------------------------------------------------------------------------
# Action log
# ---------------------------------------------------------------------------


def entry_hash(entry: Mapping[str, Any]) -> str:
    return "sha256:" + sr.sha256_hex(sr.canonical_json(entry))


def read_jsonl(text: str) -> List[Dict[str, Any]]:
    """Parse the log, turning a truncated final line into a typed error."""
    out: List[Dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError as exc:
            raise VerificationError(
                f"action log line {number} is not valid JSON "
                f"(a partial write, most likely): {exc}"
            ) from exc
    return out


def verify_chain(
    entries: List[Dict[str, Any]],
    public_keys: Mapping[str, str],
    *,
    expected_count: Optional[int] = None,
    expected_prev_head: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify hashes, chain links and signatures.

    ``expected_count`` and ``expected_prev_head`` must come from the
    customer's own retained state, never from the export being checked.
    Only the head comparison is evidence of continuity: a count alone says
    nothing against a same-length re-signed chain, which is why
    ``truncation_checked`` reports the head comparison specifically.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    prev = GENESIS_PREV
    for index, record in enumerate(entries):
        if not isinstance(record, dict):
            raise VerificationError(f"entry {index}: not a JSON object")
        unknown = set(record) - ALLOWED_FIELDS
        if unknown:
            raise VerificationError(
                f"entry {index}: unsigned field(s) present: {sorted(unknown)}"
            )
        missing = [key for key in SIGNED_FIELDS if key not in record]
        if missing:
            raise VerificationError(f"entry {index}: missing field(s): {missing}")
        entry = {key: record[key] for key in SIGNED_FIELDS}
        if record.get("seq") != index:
            raise VerificationError(f"entry {index}: sequence mismatch")
        if entry["prev_hash"] != prev:
            raise VerificationError(f"entry {index}: broken chain link")
        expected = entry_hash(entry)
        if record.get("entry_hash") != expected:
            raise VerificationError(f"entry {index}: entry_hash mismatch")

        key_id = record.get("key_id")
        public_hex = public_keys.get(key_id, "")
        signature = record.get("signature", "")
        if not public_hex or not signature.startswith("ed25519:"):
            raise VerificationError(
                f"entry {index}: missing key or malformed signature"
            )
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
                bytes.fromhex(signature.split(":", 1)[1]), expected.encode("utf-8")
            )
        except Exception as exc:  # noqa: BLE001
            raise VerificationError(f"entry {index}: signature invalid") from exc
        prev = expected

    head = prev if entries else GENESIS_PREV
    head_compared = False
    count_compared = False

    if expected_count is not None:
        if len(entries) < expected_count:
            raise VerificationError(
                f"chain is shorter than expected: {len(entries)} entries, "
                f"expected at least {expected_count} - entries have been removed"
            )
        count_compared = True
    if expected_prev_head is not None and expected_prev_head != GENESIS_PREV:
        if expected_prev_head not in {r["entry_hash"] for r in entries}:
            raise VerificationError(
                "previously seen head is absent from this chain: history was "
                "rewritten, not merely extended"
            )
        head_compared = True

    return {
        "ok": True,
        "entry_count": len(entries),
        "head_hash": head,
        "truncation_checked": head_compared,
        "count_compared": count_compared,
        "head_compared": head_compared,
    }


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------


def build_checkpoint(
    *,
    root_id: str,
    state_hash: str,
    event_count: int,
    action_log_head: str,
    action_log_entries: int,
) -> bytes:
    """The document a Time-Stamp Authority stamps: ledger and action log."""
    return sr.canonical_json(
        {
            "protocol": "SATROOT-1",
            "kind": "satledger-checkpoint",
            "root_id": root_id,
            "state_hash": state_hash,
            "event_count": event_count,
            "action_log_head": action_log_head,
            "action_log_entries": action_log_entries,
        }
    ).encode("utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _refuse_shadowed_imports(export_path: Path) -> None:
    """Refuse to run if any loaded module resolves inside the export.

    Every module, not a list of the ones known to matter: the guard used to
    check `satroot1` alone, and an export-supplied `tokenverify.py` - the
    module holding the trusted authority list - was imported and passed.
    """
    import satroot_commitment  # noqa: F401  (loaded here so it is checked)
    import satroot_onchain_envelope_smoke  # noqa: F401

    export_resolved = export_path.resolve()
    for module in list(sys.modules.values()):
        origin = getattr(module, "__file__", None)
        if not origin:
            continue
        try:
            resolved = Path(origin).resolve()
        except OSError:
            continue
        if export_resolved == resolved or export_resolved in resolved.parents:
            raise VerificationError(
                f"{module.__name__} was imported from inside the export "
                f"({resolved}). The export cannot supply the code that checks "
                "it. Run the verifier from a different directory, or install "
                "satroot and use the installed copy."
            )


def verify_export(
    export_dir: str | Path,
    *,
    expected_action_count: Optional[int] = None,
    expected_action_head: Optional[str] = None,
    expected_signer_sha256: Optional[str] = None,
    public_keys: Optional[Mapping[str, str]] = None,
    expected_genesis_event_id: Optional[str] = None,
    allow_unbound_keys: bool = True,
) -> Dict[str, Any]:
    """Verify an export end to end.

    public_keys and expected_genesis_event_id are what you hold, from an
    earlier export or an anchor; without them the bundle's own (unsigned) key
    file and genesis are used, and the result says so. allow_unbound_keys
    admits a version-0.1 ledger, whose keys are bound to no account - every
    export written before satroot 3.0.0 - and the result reports keys_bound.

    Establishes: the bundle and action log are internally consistent, they
    agree with each other, every file shipped was checked rather than
    carried, and every anchor pins a ledger prefix this export reproduces.

    Does **not** establish completeness unless a retained head is supplied.
    A prefix of a valid signed chain is a valid signed chain, and satledger
    holds the signing keys.
    """
    import satroot_commitment as commitment
    from satroot_onchain_envelope_smoke import parse_envelope_script

    export_path = Path(export_dir)
    _refuse_shadowed_imports(export_path)
    bundle = sr.verify_signed_ledger_bundle(
        export_path / "bundle", public_keys=public_keys,
        expected_genesis_event_id=expected_genesis_event_id, allow_unbound_keys=allow_unbound_keys)
    if public_keys is None:
        public_keys = _read_json(export_path / "bundle" / "public_keys.json")
    entries = read_jsonl(
        (export_path / "action_log.jsonl").read_text(encoding="utf-8")
    )
    chain = verify_chain(
        entries,
        public_keys,
        expected_count=expected_action_count,
        expected_prev_head=expected_action_head,
    )

    head = _read_json(export_path / "action_log_head.json")
    if head.get("head_hash") != chain["head_hash"]:
        raise VerificationError("action_log_head.json does not match chain")
    if head.get("entry_count") != chain["entry_count"]:
        raise VerificationError(
            f"action_log_head.json claims {head.get('entry_count')} entries, "
            f"chain has {chain['entry_count']}"
        )
    if head.get("ledger_event_count") != len(_read_json(
        export_path / "bundle" / "signed_events.json"
    )):
        raise VerificationError(
            "action_log_head.json records a different ledger event count than "
            "the bundle contains"
        )
    if head.get("ledger_state_hash") != bundle.get("final_state_hash"):
        raise VerificationError(
            "action_log_head.json is bound to a different ledger state "
            f"({head.get('ledger_state_hash')}) than the bundle "
            f"({bundle.get('final_state_hash')})"
        )

    anchors_path = export_path / "anchor_commitments.json"
    if not anchors_path.exists():
        raise VerificationError("anchor_commitments.json is missing")
    anchors = _read_json(anchors_path)
    if not isinstance(anchors, list):
        raise VerificationError("anchor_commitments.json is not a list")

    events = _read_json(export_path / "bundle" / "signed_events.json")
    verifier = sr.make_ed25519_verifier(public_keys)

    published = 0
    pinned_count = 0
    previous_count = -1
    pinned_event_count = 0
    attestations = []
    for index, anchor in enumerate(anchors):
        for field in ("root_id", "state_hash", "event_count"):
            if field not in anchor:
                raise VerificationError(f"anchor {index}: missing {field}")
        if anchor["root_id"] != bundle.get("root_id"):
            raise VerificationError(f"anchor {index}: root_id does not match")

        count = anchor["event_count"]
        if count <= previous_count:
            raise VerificationError(
                f"anchor {index}: event_count {count} does not advance on "
                f"{previous_count}; the anchor history runs backwards"
            )
        previous_count = count
        if count > len(events):
            raise VerificationError(
                f"anchor {index} commits to {count} events but the ledger holds "
                f"{len(events)}: history has been truncated"
            )
        if sr.replay(events[:count], verifier=verifier,
                     allow_unbound_keys=allow_unbound_keys).state_hash() != anchor["state_hash"]:
            raise VerificationError(
                f"anchor {index} commits to a state this ledger does not produce "
                f"at event {count}: history has been rewritten"
            )

        script_hex = anchor.get("envelope_script_hex")
        if not script_hex:
            raise VerificationError(f"anchor {index}: no envelope_script_hex")
        try:
            envelope = parse_envelope_script(bytes.fromhex(script_hex))
        except Exception as exc:  # noqa: BLE001
            raise VerificationError(
                f"anchor {index}: envelope script does not parse: {exc}"
            ) from exc
        if anchor.get("content_type") not in (None, envelope.get("content_type")):
            raise VerificationError(
                f"anchor {index}: content_type does not match its own script"
            )
        carried = envelope["payload"]
        if (
            carried.get("root_id") != anchor["root_id"]
            or carried.get("state_hash") != anchor["state_hash"]
        ):
            raise VerificationError(
                f"anchor {index}: envelope script commits to a different state"
            )
        if anchor.get("payload_json") and anchor["payload_json"] != sr.canonical_json(
            carried
        ):
            raise VerificationError(
                f"anchor {index}: payload_json does not match its own script"
            )

        # `published: false` used to skip the token, the checkpoint digest and
        # both action-log checks - so flipping one flag and deleting the token
        # directory turned a truncated log into a passing export. An anchor
        # that carries token fields must be checked whatever the flag says.
        # Only fields a *published* anchor has. checkpoint_digest is written
        # for unpublished anchors too, so including it rejected them all.
        carries_token_fields = any(
            anchor.get(field) is not None for field in ("token_file", "tsa_url")
        )
        if not anchor.get("published"):
            if carries_token_fields:
                raise VerificationError(
                    f"anchor {index}: marked unpublished but carries timestamp "
                    "fields; published anchors cannot be demoted"
                )
            continue
        token_name = anchor.get("token_file")
        if not token_name:
            raise VerificationError(
                f"anchor {index}: marked published with no token_file"
            )
        if not re.fullmatch(r"[0-9]{8}-[0-9a-f]{16}\.tsr", token_name):
            # Used as a path component: "../private_keys.json" would otherwise
            # resolve outside the token directory, and on the export side copy
            # an agent's signing keys into the customer's download.
            raise VerificationError(
                f"anchor {index}: token_file is not a plain token name: {token_name!r}"
            )
        token_path = export_path / "anchor_tokens" / token_name
        if not token_path.exists():
            raise VerificationError(
                f"anchor {index}: token file {token_name} is missing"
            )
        for field in ("action_log_head", "action_log_entries"):
            if field not in anchor:
                raise VerificationError(
                    f"anchor {index}: published anchor without {field}"
                )
        expected_digest = commitment.commitment_digest(
            build_checkpoint(
                root_id=anchor["root_id"],
                state_hash=anchor["state_hash"],
                event_count=anchor["event_count"],
                action_log_head=anchor["action_log_head"],
                action_log_entries=anchor["action_log_entries"],
            )
        )
        try:
            attestation = verify_token(
                token_path.read_bytes(),
                expected_digest,
                expected_signer_sha256=expected_signer_sha256,
            )
        except TokenError as exc:
            raise VerificationError(f"anchor {index}: {exc}") from exc
        attestations.append(
            {
                "event_count": anchor["event_count"],
                "gen_time": attestation["gen_time"],
                "signer_sha256": attestation["signer_sha256"],
                "signer_pinned": attestation["signer_pinned"],
            }
        )
        if attestation["signer_pinned"]:
            pinned_count += 1
        if anchor.get("checkpoint_digest") not in (None, expected_digest.hex()):
            raise VerificationError(
                f"anchor {index}: recorded checkpoint_digest is wrong"
            )
        if anchor["action_log_entries"] > chain["entry_count"]:
            raise VerificationError(
                f"anchor {index} attests {anchor['action_log_entries']} action "
                f"entries but the log holds {chain['entry_count']}: the action "
                "log has been truncated"
            )
        # One claim, not two: the attested head must be the head *at* the
        # attested count. Checked separately, an anchor could name entry 0's
        # hash with a count of 2 and both facts would be independently true.
        attested_head = anchor["action_log_head"]
        attested_entries = anchor["action_log_entries"]
        if attested_entries == 0:
            if attested_head != GENESIS_PREV:
                raise VerificationError(
                    f"anchor {index} attests 0 entries but names a head"
                )
        else:
            actual = entries[attested_entries - 1]["entry_hash"]
            if actual != attested_head:
                raise VerificationError(
                    f"anchor {index} attests head {attested_head} at entry "
                    f"{attested_entries}, but this log has {actual} there: "
                    "the action log has been rewritten"
                )
        published += 1
        pinned_event_count = max(pinned_event_count, anchor["event_count"])

    return {
        "bundle": bundle,
        "action_log": chain,
        "anchors": {
            "count": len(anchors),
            "published": published,
            # Computed, not asserted. This was a hardcoded True, so it read
            # true even for an empty anchor list.
            "all_pin_a_real_prefix": len(anchors) > 0,
            "attests_action_log": published > 0,
            # Named so it cannot be read as "the authority issued this".
            # It means: a signature verified under the certificate the token
            # itself carries.
            "token_signature_verified": published > 0,
            "signers_pinned": pinned_count,
            # The only field that means third-party evidence.
            "third_party_timestamp_verified": pinned_count == published > 0,
            "attestations": attestations,
            "note": (
                "each published anchor's CMS signature, content binding and "
                "imprint are verified, and its genTime is reported. The "
                "certificate comes from the token itself, so this is "
                "third-party evidence only where signer_pinned is true or you "
                "validated the chain yourself"
            ),
        },
        # Named for what it is. A retained action-log head proves action-log
        # continuity; it says nothing about whether the ledger was rewritten.
        "action_log_continuity_checked": chain["truncation_checked"],
        "keys_bound": bundle["keys_bound"],
        "keys_pinned": bundle["keys_pinned"],
        "genesis_pinned": bundle["genesis_pinned"],
        "ledger_completeness_checked": False,
        # Only anchors that actually carry a verified signature count.
        "history_pinned_to_event": pinned_event_count,
        "anchors_present_pin_to_event": previous_count if anchors else 0,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -I -m satroot_export",
        description="Verify an export offline, from the installed satroot package.",
    )
    parser.add_argument("export_dir", help="the export directory")
    parser.add_argument(
        "--expect-action-head",
        default=None,
        help=(
            "an action-log head you retained from a PREVIOUS export. This is "
            "the only check that detects deletion; without it a shorter "
            "history is indistinguishable from a shorter history."
        ),
    )
    parser.add_argument("--expect-action-count", type=int, default=None)
    parser.add_argument(
        "--allow-untrusted-tsa",
        action="store_true",
        help=(
            "accept anchors whose timestamp authority is neither built in nor "
            "pinned. The result then means internal consistency only."
        ),
    )
    parser.add_argument(
        "--trust-tsa-sha256",
        default=None,
        help=(
            "SHA-256 fingerprint of the timestamp authority certificate you "
            "trust. Without it a token's signature is checked against the "
            "certificate the token itself carries, which a forger also "
            "controls."
        ),
    )
    parser.add_argument("--public-keys-json", default=None,
                        help="key_id -> Ed25519 public key hex that you kept; without it the export's own unsigned key file is used")
    parser.add_argument("--expect-genesis", default=None,
                        help="the genesis event id you kept from an earlier export")
    parser.add_argument("--require-bound-keys", action="store_true",
                        help="refuse a version-0.1 ledger, whose keys are bound to no account")
    args = parser.parse_args(argv)

    try:
        pinned_keys = _read_json(Path(args.public_keys_json)) if args.public_keys_json else None
        result = verify_export(
            args.export_dir,
            expected_action_count=args.expect_action_count,
            expected_action_head=args.expect_action_head,
            expected_signer_sha256=args.trust_tsa_sha256,
            public_keys=pinned_keys,
            expected_genesis_event_id=args.expect_genesis,
            allow_unbound_keys=not args.require_bound_keys,
        )
    except VerificationError as exc:
        print(f"FAILED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED ({type(exc).__name__}): {exc}")
        return 1

    print(json.dumps(result, indent=2, default=str))
    anchors = result["anchors"]
    unpinned = anchors["published"] and not anchors["third_party_timestamp_verified"]
    if unpinned and not args.allow_untrusted_tsa:
        print(
            "\nFAILED: this export carries timestamp anchors whose authority is "
            "not trusted.\n"
            "These tokens carry their signing certificate, so an operator can "
            "mint\nboth. Signature checks alone cannot tell the two apart.\n\n"
            "Pass --trust-tsa-sha256 <fingerprint obtained from the authority "
            "itself>,\nor --allow-untrusted-tsa to accept internal consistency "
            "only.",
            file=sys.stderr,
        )
        return 1

    if not result["action_log_continuity_checked"]:
        print(
            "\nNOTE: action-log continuity was NOT checked. Pass "
            "--expect-action-head with a head you kept from an earlier export.",
            file=sys.stderr,
        )
    if not result["keys_pinned"] or not result["genesis_pinned"]:
        print(
            "NOTE: the ledger was checked against the export's own %s. Pass "
            "--public-keys-json and --expect-genesis with what you kept from an "
            "earlier export to check it against yours." % (
                " and ".join(x for x, ok in (("keys", result["keys_pinned"]),
                                             ("genesis", result["genesis_pinned"])) if not ok)),
            file=sys.stderr,
        )
    if not result["keys_bound"]:
        print(
            "NOTE: this ledger is version 0.1: its signing keys are not bound to "
            "accounts (exports written before satroot 3.0.0).",
            file=sys.stderr,
        )
    if not result["ledger_completeness_checked"]:
        print(
            "NOTE: ledger completeness was NOT checked. Anchors pin the "
            "prefixes they name, but an operator can obtain a fresh honest "
            "timestamp for a rewritten history. Retain a prior anchor to "
            "detect that.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
