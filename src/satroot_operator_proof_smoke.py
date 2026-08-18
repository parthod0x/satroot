from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot_federated_registry_collection_smoke import run_federated_registry_collection_smoke
from satroot_profile_federation_smoke import run_profile_federation_smoke
from satroot_publication_ladder_smoke import run_publication_ladder_smoke
from satroot_singleton_publication_ladder_smoke import (
    run_singleton_publication_ladder_smoke,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_surface(report: Mapping[str, Any], *, surface_key: str) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "ok": report.get("ok"),
        "report_path": report.get("report_path"),
        "surface_key": surface_key,
    }

    if "layer_count" in report:
        compact["layer_count"] = report.get("layer_count")
        compact["layers"] = report.get("layers")

    if surface_key == "profile_federation":
        profile_matrix = report.get("profile_matrix", {})
        registry_workspace = report.get("publication_registry_workspace", {})
        compact["profile_count"] = profile_matrix.get("profile_count")
        compact["profiles"] = profile_matrix.get("profiles")
        compact["publication_registry_artifact_count"] = registry_workspace.get("artifact_count")
    elif surface_key == "federated_registry_collection":
        collection_summary = report.get("publication_registry_workspace_collection", {})
        registry_publication = report.get("publication_registry_publication", {})
        roundtrip_registry_publication = report.get("roundtrip_publication_registry_publication", {})
        compact["workspace_count"] = collection_summary.get("workspace_count")
        compact["publication_registry_component_count"] = registry_publication.get("component_count")
        compact["roundtrip_publication_registry_component_count"] = roundtrip_registry_publication.get(
            "component_count"
        )

    return compact


def run_operator_proof_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    publication_ladder_report = run_publication_ladder_smoke(
        output_path / "publication_ladder",
        bundle_scheme=bundle_scheme,
    )
    singleton_publication_ladder_report = run_singleton_publication_ladder_smoke(
        output_path / "singleton_publication_ladder",
        bundle_scheme=bundle_scheme,
    )
    profile_federation_report = run_profile_federation_smoke(
        output_path / "profile_federation",
        bundle_scheme=bundle_scheme,
    )
    federated_registry_collection_report = run_federated_registry_collection_smoke(
        output_path / "federated_registry_collection",
        bundle_scheme=bundle_scheme,
        profile_federation_report=profile_federation_report,
    )

    surface_reports = {
        "publication_ladder": publication_ladder_report,
        "singleton_publication_ladder": singleton_publication_ladder_report,
        "profile_federation": profile_federation_report,
        "federated_registry_collection": federated_registry_collection_report,
    }
    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "surface_count": len(surface_reports),
        "surfaces": {
            name: _compact_surface(surface_report, surface_key=name)
            for name, surface_report in surface_reports.items()
        },
        "surface_reports": surface_reports,
    }
    report["ok"] = all(surface_report.get("ok") is True for surface_report in surface_reports.values())

    report_path = output_path / "operator_proof_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the top-level SATROOT operator proof surface across the stable/machine "
            "publication ladder, the singleton publication ladder, and the mixed-profile "
            "federation proof, plus the collection-backed federated registry publication round trip."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_operator_proof_smoke_run",
        help="Directory where operator-proof surfaces and the consolidated report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_operator_proof_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
