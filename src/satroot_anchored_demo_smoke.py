from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Sequence

from satroot1 import (
    SatRootError,
    bootstrap_signed_ledger_bundle,
    bootstrap_singleton_object_demo_ledger,
    ed25519_available,
    make_ed25519_verifier,
    replay,
    validate_root_id,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = "SATROOT-IDENTITY-1"
BUNDLE_SCHEME = "ed25519"
PLACEHOLDER_ROOT_ID = "6" * 64 + ":0"
ROOT_LIFECYCLE_RULE = (
    "Root satoshi custody and movement stay separate from semantic transfer: "
    "SATROOT state changes only through valid protocol events bound to the "
    "namespace root_id, and no ledger event kind models root custody."
)


def run_anchored_demo_smoke(
    output_dir: str | Path,
    *,
    root_id: str = PLACEHOLDER_ROOT_ID,
) -> dict[str, Any]:
    if not ed25519_available():
        raise SatRootError(
            "cryptography package is required for the anchored demo smoke lane; "
            "install the [crypto] extra"
        )
    validate_root_id(root_id)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    ledger = bootstrap_singleton_object_demo_ledger(
        profile=PROFILE,
        symbol="ANCHOR1",
        name="Anchored Identity Demo",
        root_id=root_id,
        holder_account="node_alpha",
        next_holder="rotated_controller",
        retire=False,
    )
    events = ledger["events"]

    bundle = bootstrap_signed_ledger_bundle(events, scheme=BUNDLE_SCHEME)
    verifier = make_ed25519_verifier(bundle["material"]["public_keys"])
    replay_hash_first = replay(bundle["signed_events"], verifier=verifier).state_hash()
    replay_hash_second = replay(bundle["signed_events"], verifier=verifier).state_hash()

    foreign_root_rejected = False
    foreign_root_error = None
    foreign_events = copy.deepcopy(events)
    foreign_events[1]["root_id"] = "7" * 64 + ":0"
    try:
        replay(foreign_events)
    except SatRootError as exc:
        foreign_root_rejected = "root_id mismatch" in str(exc)
        foreign_root_error = str(exc)

    final_snapshot = bundle["final_state_snapshot"]
    lifecycle_actions = sorted(
        {event["action"] for event in bundle["signed_events"] if "action" in event}
    )
    custody_actions = [
        action
        for action in lifecycle_actions
        if action not in {"genesis", "mint", "transfer", "burn", "freeze", "rotate-authority"}
    ]

    checks = {
        "root_id_bound_to_state": final_snapshot["root_id"] == root_id,
        "ed25519_bundle_verified": (
            bundle["scheme"] == BUNDLE_SCHEME
            and replay_hash_first == bundle["final_state_hash"]
        ),
        "replay_deterministic": replay_hash_first == replay_hash_second,
        "foreign_root_rejected": foreign_root_rejected,
        "no_custody_event_kinds": not custody_actions,
    }

    report: dict[str, Any] = {
        "lane": "anchored-demo",
        "profile": PROFILE,
        "bundle_scheme": BUNDLE_SCHEME,
        "root_id": root_id,
        "root_is_placeholder": root_id == PLACEHOLDER_ROOT_ID,
        "event_count": len(bundle["signed_events"]),
        "lifecycle_actions": lifecycle_actions,
        "final_state_hash": bundle["final_state_hash"],
        "checks": checks,
        "foreign_root_error": foreign_root_error,
        "root_lifecycle": {
            "rule": ROOT_LIFECYCLE_RULE,
            "semantic_state_hash": bundle["final_state_hash"],
            "custody_note": (
                "Moving the root satoshi on-chain does not appear in this ledger and "
                "cannot alter the semantic state hash; binding a real outpoint only "
                "changes root_id, never the event rules."
            ),
        },
    }
    report["ok"] = all(checks.values())

    signed_events_path = output_path / "signed_events.json"
    signed_events_path.write_text(
        json.dumps(bundle["signed_events"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    public_keys_path = output_path / "public_keys.json"
    public_keys_path.write_text(
        json.dumps(bundle["material"]["public_keys"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["signed_events_path"] = str(signed_events_path)
    report["public_keys_path"] = str(public_keys_path)

    report_path = output_path / "anchored_demo_smoke_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report["report_path"] = str(report_path)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the anchored identity demo lane: bind a root_id to one demo "
            "namespace, sign its lifecycle with ed25519, and verify replay, "
            "foreign-root rejection, and root-lifecycle separation."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_anchored_demo_smoke_run",
        help="Directory where the signed ledger, public keys, and report will be written.",
    )
    parser.add_argument(
        "--root-id",
        default=PLACEHOLDER_ROOT_ID,
        help=(
            "Namespace root_id as <txid>:<vout>. Defaults to the demo placeholder; "
            "pass a real one-satoshi outpoint only when intentionally anchoring."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_anchored_demo_smoke(args.output_dir, root_id=args.root_id)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
