from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    SatRootError,
    export_publication_registry_preset_from_workspace,
    lint_publication_registry_publication,
    lint_publication_registry_workspace_collection,
    main as satroot_main,
    summarize_publication_registry_publication,
    summarize_publication_registry_workspace_collection,
)
from satroot_profile_federation_smoke import run_profile_federation_smoke


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_profile_federation_surface(report: Mapping[str, Any]) -> dict[str, Any]:
    profile_matrix = report.get("profile_matrix", {})
    registry_workspace = report.get("publication_registry_workspace", {})
    federated_registry_collection = report.get("federated_publication_registry_workspace_collection", {})
    return {
        "ok": report.get("ok"),
        "report_path": report.get("report_path"),
        "profile_count": profile_matrix.get("profile_count"),
        "profiles": profile_matrix.get("profiles"),
        "publication_registry_artifact_count": registry_workspace.get("artifact_count"),
        "federated_publication_registry_workspace_collection_dir": federated_registry_collection.get("collection_dir"),
    }


def _compact_registry_collection_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "collection_dir": summary.get("collection_dir"),
        "summary_path": summary.get("summary_path"),
        "workspace_count": summary.get("workspace_count"),
        "publication_registry_workspace_dirs": summary.get("publication_registry_workspace_dirs"),
        "registry_workspaces": [
            {
                "workspace_name": entry.get("workspace_name"),
                "artifact_count": entry.get("artifact_count"),
                "publication_metadata_bundle_count": entry.get("publication_metadata_bundle_count"),
                "publication_registry_workspace_dir": entry.get("publication_registry_workspace_dir"),
                "publication_registry_dir": entry.get("publication_registry_dir"),
            }
            for entry in summary.get("registry_workspaces", [])
            if isinstance(entry, Mapping)
        ],
    }


def _compact_registry_publication_summary(
    publication_dir: Path,
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    payload = json.loads(publication_dir.joinpath("publication_registry.json").read_text(encoding="utf-8"))
    return {
        "publication_dir": str(publication_dir.resolve()),
        "publication_registry_manifest_path": str(
            publication_dir.joinpath("publication_registry_manifest.json").resolve()
        ),
        "publication_registry_payload_path": str(publication_dir.joinpath("publication_registry.json").resolve()),
        "signature_scheme": summary.get("signature_scheme"),
        "signature_key_id": summary.get("signature_key_id"),
        "component_count": summary.get("component_count"),
        "publication_registry_hash": summary.get("publication_registry_hash"),
        "index": summary.get("index"),
        "source_publication_registry_workspace_dir": payload.get("source_publication_registry_workspace_dir"),
        "source_publication_registry_workspace_collection_dir": payload.get(
            "source_publication_registry_workspace_collection_dir"
        ),
    }


def _bootstrap_publication_registry_publication_from_preset(
    *,
    preset_path: Path,
    output_dir: Path,
    signature_scheme: str,
    key_id: str,
) -> Path:
    output_dir = output_dir.resolve()
    exit_code = satroot_main(
        [
            "bootstrap-publication-registry-publication",
            "--preset-json",
            str(preset_path.resolve()),
            "--scheme",
            signature_scheme,
            "--key-id",
            key_id,
            "--output-dir",
            str(output_dir),
        ]
    )
    if exit_code != 0:
        raise SatRootError(
            "bootstrap-publication-registry-publication failed while bootstrapping collection-backed registry publication"
        )
    return output_dir


def run_federated_registry_collection_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
    profile_federation_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    if profile_federation_report is None:
        profile_federation_report = run_profile_federation_smoke(
            output_path / "profile_federation",
            bundle_scheme=bundle_scheme,
        )
    registry_collection_dir = Path(
        str(
            profile_federation_report["federated_publication_registry_workspace_collection"][
                "collection_dir"
            ]
        )
    ).resolve()
    registry_collection_summary = summarize_publication_registry_workspace_collection(registry_collection_dir)
    registry_collection_lint = lint_publication_registry_workspace_collection(registry_collection_dir)

    preset_dir = output_path / "preset_staging"
    preset_dir.mkdir(parents=True, exist_ok=True)
    collection_backed_preset_path = preset_dir / "federated_collection_backed_publication_registry.json"
    collection_backed_preset = {
        "type": "SATROOT-PUBLICATION-REGISTRY-PRESET",
        "version": "0.1",
        "publication_registry_workspace_collection_dir": str(registry_collection_dir),
        "registry": {
            "channel": "federation",
            "label": "Federated Collection-Backed Publication Registry Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
    }
    _write_json(collection_backed_preset_path, collection_backed_preset)

    registry_publication_dir = _bootstrap_publication_registry_publication_from_preset(
        preset_path=collection_backed_preset_path,
        output_dir=output_path / "publication_registry_publication",
        signature_scheme=bundle_scheme,
        key_id="publication-registry-key",
    )
    registry_publication_summary = summarize_publication_registry_publication(registry_publication_dir)
    registry_publication_lint = lint_publication_registry_publication(registry_publication_dir)

    roundtrip_export_dir = output_path / "roundtrip_exports"
    roundtrip_export_dir.mkdir(parents=True, exist_ok=True)
    exported_preset_path = roundtrip_export_dir / "exported_federated_publication_registry.json"
    exported_preset = export_publication_registry_preset_from_workspace(
        registry_publication_dir,
        output_path=exported_preset_path,
    )
    _write_json(exported_preset_path, exported_preset)

    roundtrip_registry_publication_dir = _bootstrap_publication_registry_publication_from_preset(
        preset_path=exported_preset_path,
        output_dir=output_path / "publication_registry_publication_roundtrip",
        signature_scheme=bundle_scheme,
        key_id="publication-registry-roundtrip-key",
    )
    roundtrip_registry_publication_summary = summarize_publication_registry_publication(
        roundtrip_registry_publication_dir
    )
    roundtrip_registry_publication_lint = lint_publication_registry_publication(
        roundtrip_registry_publication_dir
    )

    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "profile_federation": _compact_profile_federation_surface(profile_federation_report),
        "profile_federation_report_path": profile_federation_report.get("report_path"),
        "publication_registry_workspace_collection": _compact_registry_collection_summary(
            registry_collection_summary
        ),
        "publication_registry_workspace_collection_lint": registry_collection_lint,
        "publication_registry_preset_path": str(collection_backed_preset_path.resolve()),
        "publication_registry_publication": _compact_registry_publication_summary(
            registry_publication_dir,
            registry_publication_summary,
        ),
        "publication_registry_publication_lint": registry_publication_lint,
        "exported_publication_registry_preset_path": str(exported_preset_path.resolve()),
        "exported_publication_registry_preset": exported_preset,
        "roundtrip_publication_registry_publication": _compact_registry_publication_summary(
            roundtrip_registry_publication_dir,
            roundtrip_registry_publication_summary,
        ),
        "roundtrip_publication_registry_publication_lint": roundtrip_registry_publication_lint,
    }
    report["ok"] = all(
        [
            report["profile_federation"]["ok"] is True,
            report["publication_registry_workspace_collection_lint"]["ok"] is True,
            report["publication_registry_publication_lint"]["ok"] is True,
            report["roundtrip_publication_registry_publication_lint"]["ok"] is True,
        ]
    )

    report_path = output_path / "federated_registry_collection_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the SATROOT federated registry collection smoke: build the mixed-profile "
            "federation surface, snapshot its top-level registry workspace collection, "
            "bootstrap a top-level publication registry publication from that collection-backed "
            "preset, export the preset back out, and bootstrap the publication again."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_federated_registry_collection_smoke_run",
        help="Directory where the federated registry collection smoke outputs and report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_federated_registry_collection_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
