from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from satroot1 import (
    bootstrap_signed_ledger_bundle,
    bootstrap_singleton_object_demo_ledger,
    replay,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_JSON = REPO_ROOT / "examples" / "events_event1.json"
PROFILE = "SATROOT-EVENT-1"
BUNDLE_SCHEME = "hmac-sha256"


def _load_events(events_json: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(events_json).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("event profile smoke events input must be a JSON array")
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"event profile smoke event {index} must be a JSON object")
    return payload


def run_event_profile_smoke(
    output_dir: str | Path,
    *,
    events_json: str | Path = DEFAULT_EVENTS_JSON,
    bundle_scheme: str = BUNDLE_SCHEME,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    loaded_events = _load_events(events_json)
    replayed = replay(loaded_events)
    replay_hash_first = replayed.state_hash()
    replay_hash_second = replay(loaded_events).state_hash()

    scaffolded = bootstrap_singleton_object_demo_ledger(
        profile=PROFILE,
        symbol="EVENT1",
        name="SATROOT Telemetry Stream",
        holder_account="publisher_node",
        next_holder="successor_publisher",
        retire=False,
    )
    scaffold_snapshot = scaffolded["final_state_snapshot"]

    bundle = bootstrap_signed_ledger_bundle(scaffolded["events"], scheme=bundle_scheme)
    bundle_state = bundle["final_state_snapshot"]

    checks = {
        "example_profile_matches": replayed.profile == PROFILE,
        "example_mode_matches": replayed.profile_mode == "single-stream",
        "example_replay_deterministic": replay_hash_first == replay_hash_second,
        "example_single_unit_outstanding": sum(replayed.balances.values()) == 1
        and replayed.balances.get("successor_publisher") == 1,
        "scaffold_profile_matches": scaffold_snapshot["profile"] == PROFILE,
        "scaffold_handoff_completed": scaffold_snapshot["balances"].get("successor_publisher")
        == "1",
        "signed_bundle_verified": bundle["scheme"] == bundle_scheme
        and bundle_state["profile"] == PROFILE
        and bundle_state["balances"].get("successor_publisher") == "1",
    }

    report: dict[str, Any] = {
        "lane": "event-profile",
        "profile": PROFILE,
        "bundle_scheme": bundle_scheme,
        "events_json": str(Path(events_json).resolve()),
        "ledger_replay": {
            "event_count": len(loaded_events),
            "symbol": replayed.symbol,
            "profile": replayed.profile,
            "profile_mode": replayed.profile_mode,
            "stream_type": replayed.genesis_metadata.get("stream_type"),
            "stream_subject": replayed.genesis_metadata.get("stream_subject"),
            "sequence_policy": replayed.genesis_metadata.get("sequence_policy"),
            "balances": dict(sorted(replayed.balances.items())),
            "state_hash": replay_hash_first,
        },
        "checks": checks,
    }
    report["ok"] = all(checks.values())

    report_path = output_path / "event_profile_smoke_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report["report_path"] = str(report_path.resolve())
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the checked-in SATROOT-EVENT-1 stream-head example, scaffold a "
            "fresh single-stream demo ledger, and verify a signed bundle over it."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_event_profile_smoke_run",
        help="Directory where the event profile smoke report will be written.",
    )
    parser.add_argument(
        "--events-json",
        default=str(DEFAULT_EVENTS_JSON),
        help="Event-stream example events JSON to replay.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default=BUNDLE_SCHEME,
        help="Signature scheme for the generated demo bundle.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_event_profile_smoke(
        args.output_dir,
        events_json=args.events_json,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
