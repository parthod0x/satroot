from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_machine_demo_bundle_index_from_presets,
    lint_bundle_collection,
    lint_bundle_index_artifact,
    summarize_bundle_collection,
    summarize_bundle_index_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_PRESET_JSON = REPO_ROOT / "examples" / "catalog_presets" / "machine_compute_catalog.json"


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("machine demo bundle-index smoke preset input must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stage_machine_preset_variants(base_preset_json: str | Path, output_dir: Path) -> list[Path]:
    base_preset = _load_json_object(base_preset_json)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = [
        (
            "machine_bundle_alpha.json",
            "MBIDX01",
            "Machine Bundle Alpha",
            {
                "service_scope": "alpha-bundle",
                "billing_unit": "job",
                "consumption_model": "burn-on-use",
                "intended_use": "alpha-bundle-credit",
            },
        ),
        (
            "machine_bundle_beta.json",
            "MBIDX02",
            "Machine Bundle Beta",
            {
                "service_scope": "beta-bundle",
                "billing_unit": "minute",
                "consumption_model": "burn-on-use",
                "intended_use": "beta-bundle-credit",
            },
        ),
    ]

    staged_paths: list[Path] = []
    for filename, symbol, name, profile_fields in variants:
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

        preset_path = output_dir / filename
        _write_json(preset_path, payload)
        staged_paths.append(preset_path)
    return staged_paths


def _compact_bundle_collection_summary(summary: Mapping[str, Any], collection_dir: Path) -> dict[str, Any]:
    bundles = summary.get("bundles", [])
    bundle_symbols = sorted(
        entry.get("symbol")
        for entry in bundles
        if isinstance(entry, Mapping) and isinstance(entry.get("symbol"), str)
    )
    profiles = sorted(
        {
            entry.get("profile")
            for entry in bundles
            if isinstance(entry, Mapping) and isinstance(entry.get("profile"), str)
        }
    )
    return {
        "collection_dir": str(collection_dir.resolve()),
        "summary_path": str((collection_dir / "summary.json").resolve()),
        "bundle_count": summary.get("bundle_count"),
        "bundle_symbols": bundle_symbols,
        "profiles": profiles,
    }


def _compact_bundle_collection_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "bundle_count_matches": lint_report.get("bundle_count_matches"),
        "bundle_lint_failures": lint_report.get("bundle_lint_failures"),
    }


def _compact_bundle_index_summary(summary: Mapping[str, Any], bundle_index_path: Path) -> dict[str, Any]:
    return {
        "bundle_index_path": str(bundle_index_path.resolve()),
        "bundle_index_hash": summary.get("bundle_index_hash"),
        "bundle_count": summary.get("bundle_count"),
        "release": summary.get("release"),
        "bundle_symbols": summary.get("bundle_symbols"),
    }


def _compact_bundle_index_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "bundle_count": lint_report.get("bundle_count"),
        "duplicate_bundle_ids": lint_report.get("duplicate_bundle_ids"),
        "missing_bundle_directories": lint_report.get("missing_bundle_directories"),
        "missing_bundle_manifests": lint_report.get("missing_bundle_manifests"),
        "manifest_hash_mismatches": lint_report.get("manifest_hash_mismatches"),
        "bundle_manifest_metadata_mismatches": lint_report.get("bundle_manifest_metadata_mismatches"),
    }


def run_machine_demo_bundle_index_smoke(
    output_dir: str | Path,
    *,
    base_preset_json: str | Path = DEFAULT_BASE_PRESET_JSON,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    staged_preset_paths = _stage_machine_preset_variants(
        base_preset_json,
        output_path / "preset_staging",
    )
    generated = bootstrap_machine_demo_bundle_index_from_presets(
        staged_preset_paths,
        bundle_scheme=bundle_scheme,
        output_dir=output_path,
        bundle_index_metadata_overrides={
            "channel": "machine",
            "label": "Machine Demo Bundle Index Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
    )

    bundle_collection_dir = Path(str(generated["summary"]["bundle_collection_dir"])).resolve()
    bundle_index_path = Path(str(generated["summary"]["bundle_index_path"])).resolve()

    bundle_collection_summary = summarize_bundle_collection(bundle_collection_dir)
    bundle_collection_lint = lint_bundle_collection(bundle_collection_dir)
    bundle_index_summary = summarize_bundle_index_artifact(bundle_index_path)
    bundle_index_lint = lint_bundle_index_artifact(bundle_index_path)

    report: dict[str, Any] = {
        "profile": "SATROOT-MACHINE-1",
        "bundle_scheme": bundle_scheme,
        "base_preset_json": str(Path(base_preset_json).resolve()),
        "staged_preset_paths": [str(path.resolve()) for path in staged_preset_paths],
        "generated_bundle_count": generated["summary"]["generated_bundle_count"],
        "generated_bundles_dir": generated["summary"]["generated_bundles_dir"],
        "bundle_collection": _compact_bundle_collection_summary(
            bundle_collection_summary,
            bundle_collection_dir,
        ),
        "bundle_collection_lint": _compact_bundle_collection_lint(bundle_collection_lint),
        "bundle_index": _compact_bundle_index_summary(bundle_index_summary, bundle_index_path),
        "bundle_index_lint": _compact_bundle_index_lint(bundle_index_lint),
    }
    report["ok"] = (
        report["generated_bundle_count"] == 2
        and report["bundle_collection_lint"]["ok"] is True
        and report["bundle_index_lint"]["ok"] is True
    )

    report_path = output_path / "machine_demo_bundle_index_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the machine demo bundle-index convenience flow from staged presets "
            "and emit a compact verification report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_machine_demo_bundle_index_smoke_run",
        help="Directory where generated machine bundles, the bundle collection, bundle index, and report will be written.",
    )
    parser.add_argument(
        "--base-preset-json",
        default=str(DEFAULT_BASE_PRESET_JSON),
        help="Checked-in machine demo catalog preset used as the source template for staged smoke variants.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signing scheme for generated machine demo bundles.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_machine_demo_bundle_index_smoke(
        args.output_dir,
        base_preset_json=args.base_preset_json,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
