from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_singleton_demo_bundle_index_from_presets,
    lint_bundle_collection,
    lint_bundle_index_artifact,
    summarize_bundle_collection,
    summarize_bundle_index_artifact,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_PRESET_JSON = REPO_ROOT / "examples" / "catalog_presets" / "receipt_invoice_catalog.json"
PROFILE = "SATROOT-RECEIPT-1"


def _load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("receipt demo bundle-index smoke preset input must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stage_receipt_preset_variants(base_preset_json: str | Path, output_dir: Path) -> list[Path]:
    base_preset = _load_json_object(base_preset_json)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = [
        (
            "receipt_bundle_alpha.json",
            "RECBIDX01",
            "Receipt Bundle Alpha",
            {
                "document_type": "invoice-receipt",
                "reference_id": "INV-2026-BIDX-ALPHA",
                "issuer_entity": "ops-ledger-alpha",
                "counterparty_entity": "vendor-alpha",
                "settlement_unit": "USD",
                "intended_use": "receipt-bundle-alpha",
            },
            {
                "holder_account": "receipt_holder_alpha",
                "archive_account": "receipt_archive_alpha",
                "retire": False,
            },
        ),
        (
            "receipt_bundle_beta.json",
            "RECBIDX02",
            "Receipt Bundle Beta",
            {
                "document_type": "invoice-receipt",
                "reference_id": "INV-2026-BIDX-BETA",
                "issuer_entity": "ops-ledger-beta",
                "counterparty_entity": "vendor-beta",
                "settlement_unit": "EUR",
                "intended_use": "receipt-bundle-beta",
            },
            {
                "holder_account": "receipt_holder_beta",
                "archive_account": "receipt_archive_beta",
                "retire": False,
            },
        ),
    ]

    staged_paths: list[Path] = []
    for filename, symbol, name, profile_fields, structure_fields in variants:
        payload = copy.deepcopy(base_preset)
        symbol_overrides = dict(payload.get("symbol_overrides", {}))
        symbol_overrides[PROFILE] = symbol
        payload["symbol_overrides"] = symbol_overrides

        name_overrides = dict(payload.get("name_overrides", {}))
        name_overrides[PROFILE] = name
        payload["name_overrides"] = name_overrides

        profile_field_overrides = {
            **dict(payload.get("profile_field_overrides", {})),
            PROFILE: profile_fields,
        }
        payload["profile_field_overrides"] = profile_field_overrides

        profile_structure_overrides = {
            **dict(payload.get("profile_structure_overrides", {})),
            PROFILE: structure_fields,
        }
        payload["profile_structure_overrides"] = profile_structure_overrides

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


def run_receipt_demo_bundle_index_smoke(
    output_dir: str | Path,
    *,
    base_preset_json: str | Path = DEFAULT_BASE_PRESET_JSON,
    bundle_scheme: str = "hmac-sha256",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    staged_preset_paths = _stage_receipt_preset_variants(
        base_preset_json,
        output_path / "preset_staging",
    )
    generated = bootstrap_singleton_demo_bundle_index_from_presets(
        staged_preset_paths,
        profile=PROFILE,
        bundle_scheme=bundle_scheme,
        output_dir=output_path,
        bundle_index_metadata_overrides={
            "channel": "receipt",
            "label": "Receipt Demo Bundle Index Smoke",
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
        "profile": PROFILE,
        "bundle_scheme": bundle_scheme,
        "base_preset_json": str(Path(base_preset_json).resolve()),
        "staged_preset_paths": [str(path.resolve()) for path in staged_preset_paths],
        "generated_workspace_count": generated["summary"]["generated_workspace_count"],
        "generated_bundle_count": generated["summary"]["generated_bundle_count"],
        "generated_profiles": generated["summary"]["generated_profiles"],
        "generated_bundle_workspaces_dir": generated["summary"][
            "generated_bundle_workspaces_dir"
        ],
        "bundle_collection": _compact_bundle_collection_summary(
            bundle_collection_summary,
            bundle_collection_dir,
        ),
        "bundle_collection_lint": _compact_bundle_collection_lint(bundle_collection_lint),
        "bundle_index": _compact_bundle_index_summary(bundle_index_summary, bundle_index_path),
        "bundle_index_lint": _compact_bundle_index_lint(bundle_index_lint),
    }
    report["ok"] = (
        report["generated_workspace_count"] == 2
        and report["generated_bundle_count"] == 2
        and report["bundle_collection_lint"]["ok"] is True
        and report["bundle_index_lint"]["ok"] is True
    )

    report_path = output_path / "receipt_demo_bundle_index_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the receipt singleton demo bundle-index convenience flow from "
            "staged presets and emit a compact verification report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_receipt_demo_bundle_index_smoke_run",
        help="Directory where generated receipt bundles, the bundle collection, bundle index, and report will be written.",
    )
    parser.add_argument(
        "--base-preset-json",
        default=str(DEFAULT_BASE_PRESET_JSON),
        help="Checked-in receipt demo catalog preset used as the source template for staged smoke variants.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signing scheme for generated receipt demo bundles.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_receipt_demo_bundle_index_smoke(
        args.output_dir,
        base_preset_json=args.base_preset_json,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
