from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_machine_demo_release_catalog_publication_from_presets,
    lint_release_collection,
    lint_signed_release_catalog_publication,
    summarize_release_collection,
    summarize_signed_release_catalog_publication,
)


from satroot1 import examples_root as _examples_root

EXAMPLES_ROOT = _examples_root()
DEFAULT_BASE_PRESET_JSON = EXAMPLES_ROOT / "catalog_presets" / "machine_compute_catalog.json"


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("machine demo release catalog smoke preset input must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stage_machine_preset_variants(base_preset_json: str | Path, output_dir: Path) -> list[Path]:
    base_preset = _load_json_object(base_preset_json)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = [
        (
            "machine_compute_alpha.json",
            "MCATREL01",
            "Machine Catalog Alpha",
            {
                "service_scope": "alpha-render",
                "billing_unit": "job",
                "consumption_model": "burn-on-use",
                "intended_use": "alpha-catalog-credit",
            },
            {
                "channel": "alpha",
                "label": "Machine Catalog Alpha Release",
                "published_at": "2026-08-14T00:00:00Z",
            },
        ),
        (
            "machine_compute_beta.json",
            "MCATREL02",
            "Machine Catalog Beta",
            {
                "service_scope": "beta-render",
                "billing_unit": "minute",
                "consumption_model": "burn-on-use",
                "intended_use": "beta-catalog-credit",
            },
            {
                "channel": "beta",
                "label": "Machine Catalog Beta Release",
                "published_at": "2026-08-15T00:00:00Z",
            },
        ),
    ]

    staged_paths: list[Path] = []
    for filename, symbol, name, profile_fields, release_metadata in variants:
        payload = copy.deepcopy(base_preset)
        symbol_overrides = dict(payload.get("symbol_overrides", {}))
        symbol_overrides["SATROOT-MACHINE-1"] = symbol
        payload["symbol_overrides"] = symbol_overrides

        name_overrides = dict(payload.get("name_overrides", {}))
        name_overrides["SATROOT-MACHINE-1"] = name
        payload["name_overrides"] = name_overrides

        profile_field_overrides = {
            **dict(payload.get("profile_field_overrides", {})),
            "SATROOT-MACHINE-1": profile_fields,
        }
        payload["profile_field_overrides"] = profile_field_overrides
        payload["release"] = release_metadata

        preset_path = output_dir / filename
        _write_json(preset_path, payload)
        staged_paths.append(preset_path)
    return staged_paths


def _compact_release_collection_summary(summary: Mapping[str, Any], collection_dir: Path) -> dict[str, Any]:
    releases = summary.get("releases", [])
    bundle_symbols = sorted(
        {
            symbol
            for entry in releases
            if isinstance(entry, Mapping)
            for symbol in entry.get("bundle_symbols", [])
            if isinstance(symbol, str)
        }
    )
    release_labels = [
        entry.get("release", {}).get("label")
        for entry in releases
        if isinstance(entry, Mapping) and isinstance(entry.get("release"), Mapping)
    ]
    return {
        "collection_dir": str(collection_dir.resolve()),
        "summary_path": str((collection_dir / "summary.json").resolve()),
        "release_count": summary.get("release_count"),
        "bundle_symbols": bundle_symbols,
        "release_labels": release_labels,
    }


def _compact_release_catalog_summary(summary: Mapping[str, Any], release_catalog_dir: Path) -> dict[str, Any]:
    return {
        "release_catalog_dir": str(release_catalog_dir.resolve()),
        "release_catalog_path": summary.get("release_catalog_resolved_path"),
        "release_catalog_manifest_path": str(
            (release_catalog_dir / "release_catalog_manifest.json").resolve()
        ),
        "release_count": summary.get("release_count"),
        "catalog": summary.get("catalog"),
        "release_labels": summary.get("release_labels"),
        "bundle_symbols": sorted(
            {
                symbol
                for entry in summary.get("releases", [])
                if isinstance(entry, Mapping)
                for symbol in entry.get("bundle_symbols", [])
                if isinstance(symbol, str)
            }
        ),
    }


def _compact_collection_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "release_count_matches": lint_report.get("release_count_matches"),
        "release_lint_failures": lint_report.get("release_lint_failures"),
    }


def _compact_release_catalog_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "release_count_matches": lint_report.get("release_count_matches"),
        "catalog_metadata_matches": lint_report.get("catalog_metadata_matches"),
        "missing_release_directories": lint_report.get("missing_release_directories"),
    }


def run_machine_demo_release_catalog_smoke(
    output_dir: str | Path,
    *,
    base_preset_json: str | Path = DEFAULT_BASE_PRESET_JSON,
    bundle_scheme: str = "hmac-sha256",
    signature_scheme: str | None = None,
    release_key_id: str = "release-key",
    catalog_key_id: str = "catalog-key",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    resolved_signature_scheme = signature_scheme or bundle_scheme

    staged_preset_paths = _stage_machine_preset_variants(
        base_preset_json,
        output_path / "preset_staging",
    )
    generated = bootstrap_machine_demo_release_catalog_publication_from_presets(
        staged_preset_paths,
        bundle_scheme=bundle_scheme,
        output_dir=output_path,
        release_key_id=release_key_id,
        signature_scheme=resolved_signature_scheme,
        key_id=catalog_key_id,
        catalog_metadata={
            "channel": "machine",
            "label": "Machine Demo Release Catalog Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
    )

    release_collection_dir = Path(str(generated["summary"]["release_collection_dir"])).resolve()
    release_catalog_publication_dir = Path(
        str(generated["summary"]["release_catalog_publication_dir"])
    ).resolve()
    release_collection_summary = summarize_release_collection(release_collection_dir)
    release_collection_lint = lint_release_collection(release_collection_dir)
    release_catalog_summary = summarize_signed_release_catalog_publication(
        release_catalog_publication_dir
    )
    release_catalog_lint = lint_signed_release_catalog_publication(
        release_catalog_publication_dir
    )

    report: dict[str, Any] = {
        "profile": "SATROOT-MACHINE-1",
        "bundle_scheme": bundle_scheme,
        "signature_scheme": resolved_signature_scheme,
        "base_preset_json": str(Path(base_preset_json).resolve()),
        "staged_preset_paths": [str(path.resolve()) for path in staged_preset_paths],
        "generated_release_count": generated["summary"]["generated_release_count"],
        "release_collection_workspace_dir": generated["summary"]["release_collection_workspace_dir"],
        "release_collection_workspace_summary_path": generated["summary"][
            "release_collection_workspace_summary_path"
        ],
        "release_collection": _compact_release_collection_summary(
            release_collection_summary,
            release_collection_dir,
        ),
        "release_collection_lint": _compact_collection_lint(release_collection_lint),
        "release_catalog_publication": _compact_release_catalog_summary(
            release_catalog_summary,
            release_catalog_publication_dir,
        ),
        "release_catalog_publication_lint": _compact_release_catalog_lint(release_catalog_lint),
    }
    report["ok"] = (
        report["generated_release_count"] == 2
        and report["release_collection_lint"]["ok"] is True
        and report["release_catalog_publication_lint"]["ok"] is True
    )

    report_path = output_path / "machine_demo_release_catalog_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the machine demo release-catalog publication convenience flow from "
            "staged presets and emit a compact verification report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_machine_demo_release_catalog_smoke_run",
        help="Directory where the generated release collection, catalog publication, and report will be written.",
    )
    parser.add_argument(
        "--base-preset-json",
        default=str(DEFAULT_BASE_PRESET_JSON),
        help="Checked-in machine demo catalog preset used as the source template for staged smoke variants.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signing scheme for generated bundle, release, and collection artifacts.",
    )
    parser.add_argument(
        "--signature-scheme",
        default=None,
        help="Optional release-catalog publication signing override; defaults to --bundle-scheme.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_machine_demo_release_catalog_smoke(
        args.output_dir,
        base_preset_json=args.base_preset_json,
        bundle_scheme=args.bundle_scheme,
        signature_scheme=args.signature_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
