from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot_identity_demo_release_catalog_index_smoke import (
    run_identity_demo_release_catalog_index_smoke,
)
from satroot_license_demo_release_catalog_index_smoke import (
    run_license_demo_release_catalog_index_smoke,
)
from satroot_receipt_demo_release_catalog_index_smoke import (
    run_receipt_demo_release_catalog_index_smoke,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_lane_report(report: Mapping[str, Any]) -> dict[str, Any]:
    publication = report.get("release_catalog_index_publication", {})
    return {
        "ok": report.get("ok"),
        "profile": report.get("profile"),
        "generated_release_count": report.get("generated_release_count"),
        "report_path": report.get("report_path"),
        "release_catalog_index_manifest_path": publication.get(
            "release_catalog_index_manifest_path"
        ),
        "index_label": publication.get("index", {}).get("label")
        if isinstance(publication.get("index"), Mapping)
        else None,
    }


def run_singleton_demo_release_catalog_index_matrix_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    lane_reports = {
        "receipt": run_receipt_demo_release_catalog_index_smoke(
            output_path / "receipt",
            bundle_scheme=bundle_scheme,
        ),
        "identity": run_identity_demo_release_catalog_index_smoke(
            output_path / "identity",
            bundle_scheme=bundle_scheme,
        ),
        "license": run_license_demo_release_catalog_index_smoke(
            output_path / "license",
            bundle_scheme=bundle_scheme,
        ),
    }

    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "profile_count": len(lane_reports),
        "profiles": {name: _compact_lane_report(lane) for name, lane in lane_reports.items()},
        "profile_reports": lane_reports,
    }
    report["ok"] = all(
        lane.get("ok") is True and lane.get("release_catalog_index_publication_lint", {}).get("ok") is True
        for lane in lane_reports.values()
    )

    report_path = output_path / "singleton_demo_release_catalog_index_matrix_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the receipt, identity, and license singleton demo release-catalog-index "
            "smoke workflows and emit one consolidated matrix report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_singleton_demo_release_catalog_index_matrix_smoke_run",
        help="Directory where per-profile singleton release-catalog-index smoke runs and the consolidated report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle, release, catalog, and index artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_singleton_demo_release_catalog_index_matrix_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
