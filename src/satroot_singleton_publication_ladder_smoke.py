from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot_singleton_demo_bundle_index_matrix_smoke import (
    run_singleton_demo_bundle_index_matrix_smoke,
)
from satroot_singleton_demo_release_catalog_index_matrix_smoke import (
    run_singleton_demo_release_catalog_index_matrix_smoke,
)
from satroot_singleton_demo_release_catalog_matrix_smoke import (
    run_singleton_demo_release_catalog_matrix_smoke,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_layer(report: Mapping[str, Any], *, layer_key: str) -> dict[str, Any]:
    return {
        "ok": report.get("ok"),
        "profile_count": report.get("profile_count"),
        "report_path": report.get("report_path"),
        "profiles": report.get("profiles"),
        "layer_key": layer_key,
    }


def run_singleton_publication_ladder_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    bundle_index_report = run_singleton_demo_bundle_index_matrix_smoke(
        output_path / "bundle_index",
        bundle_scheme=bundle_scheme,
    )
    release_catalog_report = run_singleton_demo_release_catalog_matrix_smoke(
        output_path / "release_catalog",
        bundle_scheme=bundle_scheme,
    )
    release_catalog_index_report = run_singleton_demo_release_catalog_index_matrix_smoke(
        output_path / "release_catalog_index",
        bundle_scheme=bundle_scheme,
    )

    layer_reports = {
        "bundle_index": bundle_index_report,
        "release_catalog": release_catalog_report,
        "release_catalog_index": release_catalog_index_report,
    }
    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "layer_count": len(layer_reports),
        "layers": {
            name: _compact_layer(layer_report, layer_key=name)
            for name, layer_report in layer_reports.items()
        },
        "layer_reports": layer_reports,
    }
    report["ok"] = all(layer_report.get("ok") is True for layer_report in layer_reports.values())

    report_path = output_path / "singleton_publication_ladder_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full singleton publication ladder across the receipt, identity, "
            "and license bundle-index, release-catalog, and release-catalog-index "
            "matrix smoke workflows."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_singleton_publication_ladder_smoke_run",
        help="Directory where singleton ladder layer runs and the consolidated report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated singleton bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_singleton_publication_ladder_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
