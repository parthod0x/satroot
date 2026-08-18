from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_singleton_demo_release_catalog_index_publication_from_presets,
    bootstrap_singleton_demo_release_catalog_publication_from_presets,
    lint_release_collection,
    lint_signed_release_catalog_index_publication,
    lint_signed_release_catalog_publication,
    summarize_release_collection,
    summarize_signed_release_catalog_index_publication,
    summarize_signed_release_catalog_publication,
)


def load_json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stage_singleton_preset_variants(
    base_preset_json: str | Path,
    *,
    profile: str,
    variants: Sequence[tuple[str, str, str, Mapping[str, Any], Mapping[str, Any], Mapping[str, str]]],
    output_dir: Path,
) -> list[Path]:
    base_preset = load_json_object(
        base_preset_json,
        label="singleton demo release smoke preset input",
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    staged_paths: list[Path] = []
    for filename, symbol, name, profile_fields, structure_fields, release_metadata in variants:
        payload = copy.deepcopy(base_preset)

        symbol_overrides = dict(payload.get("symbol_overrides", {}))
        symbol_overrides[profile] = symbol
        payload["symbol_overrides"] = symbol_overrides

        name_overrides = dict(payload.get("name_overrides", {}))
        name_overrides[profile] = name
        payload["name_overrides"] = name_overrides

        profile_field_overrides = {
            **dict(payload.get("profile_field_overrides", {})),
            profile: dict(profile_fields),
        }
        payload["profile_field_overrides"] = profile_field_overrides

        profile_structure_overrides = {
            **dict(payload.get("profile_structure_overrides", {})),
            profile: dict(structure_fields),
        }
        payload["profile_structure_overrides"] = profile_structure_overrides
        payload["release"] = dict(release_metadata)

        preset_path = output_dir / filename
        write_json(preset_path, payload)
        staged_paths.append(preset_path)

    return staged_paths


def compact_release_collection_summary(summary: Mapping[str, Any], collection_dir: Path) -> dict[str, Any]:
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


def compact_release_catalog_summary(summary: Mapping[str, Any], release_catalog_dir: Path) -> dict[str, Any]:
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


def compact_release_catalog_index_summary(
    summary: Mapping[str, Any], release_catalog_index_dir: Path
) -> dict[str, Any]:
    return {
        "release_catalog_index_dir": str(release_catalog_index_dir.resolve()),
        "release_catalog_index_path": summary.get("release_catalog_index_resolved_path"),
        "release_catalog_index_manifest_path": str(
            (release_catalog_index_dir / "release_catalog_index_manifest.json").resolve()
        ),
        "release_catalog_count": summary.get("release_catalog_count"),
        "index": summary.get("index"),
        "catalog_labels": summary.get("catalog_labels"),
    }


def compact_collection_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "release_count_matches": lint_report.get("release_count_matches"),
        "release_lint_failures": lint_report.get("release_lint_failures"),
    }


def compact_release_catalog_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "release_count_matches": lint_report.get("release_count_matches"),
        "catalog_metadata_matches": lint_report.get("catalog_metadata_matches"),
        "missing_release_directories": lint_report.get("missing_release_directories"),
    }


def compact_release_catalog_index_lint(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "release_catalog_count_matches": lint_report.get("release_catalog_count_matches"),
        "index_metadata_matches": lint_report.get("index_metadata_matches"),
        "missing_release_catalog_directories": lint_report.get(
            "missing_release_catalog_directories"
        ),
    }


def run_singleton_demo_release_catalog_smoke(
    output_dir: str | Path,
    *,
    profile: str,
    base_preset_json: str | Path,
    variants: Sequence[tuple[str, str, str, Mapping[str, Any], Mapping[str, Any], Mapping[str, str]]],
    bundle_scheme: str = "hmac-sha256",
    signature_scheme: str | None = None,
    release_key_id: str = "release-key",
    catalog_key_id: str = "catalog-key",
    catalog_metadata: Mapping[str, str],
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    resolved_signature_scheme = signature_scheme or bundle_scheme

    staged_preset_paths = stage_singleton_preset_variants(
        base_preset_json,
        profile=profile,
        variants=variants,
        output_dir=output_path / "preset_staging",
    )
    generated = bootstrap_singleton_demo_release_catalog_publication_from_presets(
        staged_preset_paths,
        profile=profile,
        bundle_scheme=bundle_scheme,
        output_dir=output_path,
        release_key_id=release_key_id,
        signature_scheme=resolved_signature_scheme,
        key_id=catalog_key_id,
        catalog_metadata=catalog_metadata,
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
        "profile": profile,
        "bundle_scheme": bundle_scheme,
        "signature_scheme": resolved_signature_scheme,
        "base_preset_json": str(Path(base_preset_json).resolve()),
        "staged_preset_paths": [str(path.resolve()) for path in staged_preset_paths],
        "generated_release_count": generated["summary"]["generated_release_count"],
        "generated_profiles": generated["summary"]["generated_profiles"],
        "release_collection_workspace_dir": generated["summary"]["release_collection_workspace_dir"],
        "release_collection_workspace_summary_path": generated["summary"][
            "release_collection_workspace_summary_path"
        ],
        "release_collection": compact_release_collection_summary(
            release_collection_summary,
            release_collection_dir,
        ),
        "release_collection_lint": compact_collection_lint(release_collection_lint),
        "release_catalog_publication": compact_release_catalog_summary(
            release_catalog_summary,
            release_catalog_publication_dir,
        ),
        "release_catalog_publication_lint": compact_release_catalog_lint(
            release_catalog_lint
        ),
    }
    report["ok"] = (
        report["generated_release_count"] == 2
        and report["release_collection_lint"]["ok"] is True
        and report["release_catalog_publication_lint"]["ok"] is True
    )

    report_path = output_path / f"{profile.lower()}_demo_release_catalog_smoke_report.json"
    write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    write_json(report_path, report)
    return report


def run_singleton_demo_release_catalog_index_smoke(
    output_dir: str | Path,
    *,
    profile: str,
    base_preset_json: str | Path,
    variants: Sequence[tuple[str, str, str, Mapping[str, Any], Mapping[str, Any], Mapping[str, str]]],
    bundle_scheme: str = "hmac-sha256",
    catalog_signature_scheme: str | None = None,
    index_signature_scheme: str | None = None,
    release_key_id: str = "release-key",
    catalog_key_id: str = "catalog-key",
    index_key_id: str = "index-key",
    catalog_metadata: Mapping[str, str],
    index_metadata: Mapping[str, str],
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    resolved_catalog_signature_scheme = catalog_signature_scheme or bundle_scheme
    resolved_index_signature_scheme = index_signature_scheme or bundle_scheme

    staged_preset_paths = stage_singleton_preset_variants(
        base_preset_json,
        profile=profile,
        variants=variants,
        output_dir=output_path / "preset_staging",
    )
    generated = bootstrap_singleton_demo_release_catalog_index_publication_from_presets(
        staged_preset_paths,
        profile=profile,
        bundle_scheme=bundle_scheme,
        output_dir=output_path,
        release_key_id=release_key_id,
        catalog_signature_scheme=resolved_catalog_signature_scheme,
        catalog_key_id=catalog_key_id,
        index_signature_scheme=resolved_index_signature_scheme,
        index_key_id=index_key_id,
        catalog_metadata=catalog_metadata,
        index_metadata=index_metadata,
    )

    release_collection_dir = Path(str(generated["summary"]["release_collection_dir"])).resolve()
    release_catalog_publication_dir = Path(
        str(generated["summary"]["release_catalog_publication_dir"])
    ).resolve()
    release_catalog_index_publication_dir = Path(
        str(generated["summary"]["release_catalog_index_publication_dir"])
    ).resolve()

    release_collection_summary = summarize_release_collection(release_collection_dir)
    release_collection_lint = lint_release_collection(release_collection_dir)
    release_catalog_summary = summarize_signed_release_catalog_publication(
        release_catalog_publication_dir
    )
    release_catalog_lint = lint_signed_release_catalog_publication(
        release_catalog_publication_dir
    )
    release_catalog_index_summary = summarize_signed_release_catalog_index_publication(
        release_catalog_index_publication_dir
    )
    release_catalog_index_lint = lint_signed_release_catalog_index_publication(
        release_catalog_index_publication_dir
    )

    report: dict[str, Any] = {
        "profile": profile,
        "bundle_scheme": bundle_scheme,
        "catalog_signature_scheme": resolved_catalog_signature_scheme,
        "index_signature_scheme": resolved_index_signature_scheme,
        "base_preset_json": str(Path(base_preset_json).resolve()),
        "staged_preset_paths": [str(path.resolve()) for path in staged_preset_paths],
        "generated_release_count": generated["summary"]["generated_release_count"],
        "generated_profiles": generated["summary"]["generated_profiles"],
        "release_catalog_publication_workspace_dir": generated["summary"][
            "release_catalog_publication_workspace_dir"
        ],
        "release_catalog_publication_workspace_summary_path": generated["summary"][
            "release_catalog_publication_workspace_summary_path"
        ],
        "release_collection": compact_release_collection_summary(
            release_collection_summary,
            release_collection_dir,
        ),
        "release_collection_lint": compact_collection_lint(release_collection_lint),
        "release_catalog_publication": compact_release_catalog_summary(
            release_catalog_summary,
            release_catalog_publication_dir,
        ),
        "release_catalog_publication_lint": compact_release_catalog_lint(
            release_catalog_lint
        ),
        "release_catalog_index_publication": compact_release_catalog_index_summary(
            release_catalog_index_summary,
            release_catalog_index_publication_dir,
        ),
        "release_catalog_index_publication_lint": compact_release_catalog_index_lint(
            release_catalog_index_lint
        ),
    }
    report["ok"] = (
        report["generated_release_count"] == 2
        and report["release_collection_lint"]["ok"] is True
        and report["release_catalog_publication_lint"]["ok"] is True
        and report["release_catalog_index_publication_lint"]["ok"] is True
    )

    report_path = output_path / f"{profile.lower()}_demo_release_catalog_index_smoke_report.json"
    write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    write_json(report_path, report)
    return report
