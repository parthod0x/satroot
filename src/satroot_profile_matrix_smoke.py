from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot_event_profile_smoke import run_event_profile_smoke
from satroot_identity_profile_smoke import run_identity_profile_smoke
from satroot_license_profile_smoke import run_license_profile_smoke
from satroot_machine_profile_smoke import run_machine_profile_smoke
from satroot_receipt_profile_smoke import run_receipt_profile_smoke
from satroot_stable_profile_smoke import run_stable_profile_smoke


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_lane_report(report: Mapping[str, Any]) -> dict[str, Any]:
    ledger = report.get("ledger_replay", {})
    registry = report.get("publication_registry_workspace", {})
    return {
        "ok": report.get("ok"),
        "profile": ledger.get("profile"),
        "profile_mode": ledger.get("profile_mode"),
        "symbol": ledger.get("symbol"),
        "state_hash": ledger.get("state_hash"),
        "report_path": report.get("report_path"),
        "publication_registry_manifest_path": registry.get("publication_registry_manifest_path"),
    }


def run_profile_matrix_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    lane_reports = {
        "stable": run_stable_profile_smoke(output_path / "stable", bundle_scheme=bundle_scheme),
        "machine": run_machine_profile_smoke(output_path / "machine", bundle_scheme=bundle_scheme),
        "receipt": run_receipt_profile_smoke(output_path / "receipt", bundle_scheme=bundle_scheme),
        "identity": run_identity_profile_smoke(output_path / "identity", bundle_scheme=bundle_scheme),
        "license": run_license_profile_smoke(output_path / "license", bundle_scheme=bundle_scheme),
        "event": run_event_profile_smoke(output_path / "event", bundle_scheme=bundle_scheme),
    }

    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "profile_count": len(lane_reports),
        "profiles": {name: _compact_lane_report(lane_report) for name, lane_report in lane_reports.items()},
        "profile_reports": lane_reports,
    }
    report["ok"] = all(
        lane.get("ok") is True and lane.get("publication_registry_workspace_lint", {}).get("ok") is True
        for lane in lane_reports.values()
    )

    report_path = output_path / "profile_matrix_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all released SATROOT profile smoke workflows and emit one "
            "consolidated profile-matrix report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_profile_matrix_smoke_run",
        help="Directory where per-profile smoke workspaces and the consolidated report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_profile_matrix_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
