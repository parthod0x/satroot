from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_machine_credit_demo_catalog_workspace,
    bootstrap_machine_credit_publication_registry_workspace,
    lint_demo_catalog_workspace,
    lint_publication_catalog_workspace,
    lint_publication_network_workspace,
    lint_publication_registry_workspace,
    publish_machine_publication_network_workspace,
    publish_machine_publication_stack_workspace,
    replay,
    summarize_demo_catalog_workspace,
    summarize_publication_catalog_workspace,
    summarize_publication_network_workspace,
    summarize_publication_registry_workspace,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS_JSON = REPO_ROOT / "examples" / "events_apicredit1.json"


def _load_events(events_json: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(events_json).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("machine profile smoke events input must be a JSON array")
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"machine profile smoke event {index} must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compact_catalog_summary(summary: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    return {
        "workspace_dir": str(source_dir.resolve()),
        "summary_path": str((source_dir / "summary.json").resolve()),
        "artifact_count": summary.get("artifact_count"),
        "publication_metadata_bundle_count": summary.get("publication_metadata_bundle_count"),
        "publication_metadata_bundle_names": summary.get("publication_metadata_bundle_names"),
        "publication_metadata_artifact_kinds": summary.get("publication_metadata_artifact_kinds"),
        "publication_descriptor_index_dir": summary.get("publication_descriptor_index_dir"),
        "publication_metadata_catalog_dir": summary.get("publication_metadata_catalog_dir"),
    }


def _compact_demo_catalog_summary(summary: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    return {
        "workspace_dir": str(source_dir.resolve()),
        "summary_path": str((source_dir / "summary.json").resolve()),
        "bundle_count": summary.get("bundle_count"),
        "bundle_names": summary.get("bundle_names"),
        "bundle_profiles": summary.get("bundle_profiles"),
        "release_dir": summary.get("release_dir"),
        "release_manifest_path": summary.get("release_manifest_path"),
    }


def _compact_network_summary(summary: Mapping[str, Any], source_dir: Path) -> dict[str, Any]:
    return {
        "workspace_dir": str(source_dir.resolve()),
        "summary_path": str((source_dir / "summary.json").resolve()),
        "workspace_count": summary.get("workspace_count"),
        "workspace_names": summary.get("workspace_names"),
        "release_catalog_index_dir": summary.get("release_catalog_index_dir"),
        "release_catalog_index_manifest_path": summary.get("release_catalog_index_manifest_path"),
    }


def _compact_registry_summary(summary: Mapping[str, Any], workspace_dir: Path) -> dict[str, Any]:
    return {
        "workspace_dir": str(workspace_dir.resolve()),
        "summary_path": str((workspace_dir / "summary.json").resolve()),
        "artifact_count": summary.get("artifact_count"),
        "publication_metadata_bundle_count": summary.get("publication_metadata_bundle_count"),
        "publication_metadata_bundle_names": summary.get("publication_metadata_bundle_names"),
        "publication_metadata_artifact_kinds": summary.get("publication_metadata_artifact_kinds"),
        "release_catalog_index_dir": summary.get("release_catalog_index_dir"),
        "publication_descriptor_index_dir": summary.get("publication_descriptor_index_dir"),
        "publication_metadata_catalog_dir": summary.get("publication_metadata_catalog_dir"),
        "publication_registry_dir": summary.get("publication_registry_dir"),
        "publication_registry_manifest_path": summary.get("publication_registry_manifest_path"),
    }


def _compact_lint_report(lint_report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ok": lint_report.get("ok"),
        "metadata_bundle_lint_failures": lint_report.get("metadata_bundle_lint_failures"),
        "workspace_lint_failures": lint_report.get("workspace_lint_failures"),
        "release_catalog_index_lint_ok": (
            lint_report.get("release_catalog_index_lint", {}).get("ok")
            if isinstance(lint_report.get("release_catalog_index_lint"), Mapping)
            else None
        ),
        "publication_descriptor_index_lint_ok": (
            lint_report.get("publication_descriptor_index_lint", {}).get("ok")
            if isinstance(lint_report.get("publication_descriptor_index_lint"), Mapping)
            else None
        ),
        "publication_network_lint_ok": (
            lint_report.get("publication_network_lint", {}).get("ok")
            if isinstance(lint_report.get("publication_network_lint"), Mapping)
            else None
        ),
        "publication_registry_lint_ok": (
            lint_report.get("publication_registry_lint", {}).get("ok")
            if isinstance(lint_report.get("publication_registry_lint"), Mapping)
            else None
        ),
    }


def run_machine_profile_smoke(
    output_dir: str | Path,
    *,
    events_json: str | Path = DEFAULT_EVENTS_JSON,
    bundle_scheme: str = "hmac-sha256",
    release_key_id: str = "release-key",
    release_catalog_key_id: str = "release-catalog-key",
    release_catalog_index_key_id: str = "release-catalog-index-key",
    publication_descriptor_index_key_id: str = "publication-descriptor-index-key",
    publication_metadata_key_id: str = "publication-metadata-key",
    publication_metadata_catalog_key_id: str = "publication-metadata-catalog-key",
    publication_registry_key_id: str = "publication-registry-key",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    loaded_events = _load_events(events_json)
    replayed = replay(loaded_events)
    genesis = loaded_events[0]
    symbol = str(genesis["symbol"])
    name = str(genesis["name"])
    service_scope = str(genesis.get("service_scope", "api-compute"))
    billing_unit = str(genesis.get("billing_unit", "request"))
    consumption_model = str(genesis.get("consumption_model", "burn-on-use"))
    intended_use = str(genesis.get("intended_use", "machine-api-credit"))

    source_catalog_dir = output_path / "source_machine_catalog_workspace"
    source_stack_dir = output_path / "source_publication_stack"
    source_network_dir = output_path / "source_publication_network"
    registry_workspace_dir = output_path / "machine_profile_registry_workspace"

    bootstrap_machine_credit_demo_catalog_workspace(
        symbol=symbol,
        name=name,
        bundle_scheme=bundle_scheme,
        output_dir=source_catalog_dir,
        release_key_id=release_key_id,
        service_scope=service_scope,
        billing_unit=billing_unit,
        consumption_model=consumption_model,
        intended_use=intended_use,
        release_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Release",
        },
    )
    publish_machine_publication_stack_workspace(
        [source_catalog_dir],
        output_dir=source_stack_dir,
        signature_scheme=bundle_scheme,
        key_id=release_catalog_key_id,
        release_catalog_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Release Catalog",
        },
    )
    publish_machine_publication_network_workspace(
        [source_stack_dir],
        output_dir=source_network_dir,
        signature_scheme=bundle_scheme,
        key_id=release_catalog_index_key_id,
        release_catalog_index_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Release Catalog Index",
        },
    )

    workspace = bootstrap_machine_credit_publication_registry_workspace(
        symbol=symbol,
        name=name,
        bundle_scheme=bundle_scheme,
        output_dir=registry_workspace_dir,
        release_catalog_index_dir=source_network_dir / "release_catalog_index",
        release_key_id=release_key_id,
        publication_descriptor_index_key_id=publication_descriptor_index_key_id,
        publication_metadata_key_id=publication_metadata_key_id,
        publication_metadata_catalog_key_id=publication_metadata_catalog_key_id,
        publication_registry_key_id=publication_registry_key_id,
        service_scope=service_scope,
        billing_unit=billing_unit,
        consumption_model=consumption_model,
        intended_use=intended_use,
        publication_network_dir=source_network_dir,
        release_catalog_key_id=release_catalog_key_id,
        release_catalog_index_key_id=release_catalog_index_key_id,
        release_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Release",
        },
        descriptor_index_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Descriptor Index",
        },
        publication_metadata_catalog_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Metadata Catalog",
        },
        publication_registry_metadata={
            "channel": "machine",
            "label": "Machine Profile Smoke Registry",
        },
    )

    demo_catalog_summary = summarize_demo_catalog_workspace(source_catalog_dir)
    demo_catalog_lint = lint_demo_catalog_workspace(source_catalog_dir)
    network_summary = summarize_publication_network_workspace(source_network_dir)
    network_lint = lint_publication_network_workspace(source_network_dir)
    registry_catalog_dir = Path(workspace["summary"]["source_machine_publication_catalog_workspace_dir"]).resolve()
    catalog_summary = summarize_publication_catalog_workspace(registry_catalog_dir)
    catalog_lint = lint_publication_catalog_workspace(registry_catalog_dir)
    registry_summary = summarize_publication_registry_workspace(registry_workspace_dir)
    registry_lint = lint_publication_registry_workspace(registry_workspace_dir)

    report: dict[str, Any] = {
        "events_json": str(Path(events_json).resolve()),
        "bundle_scheme": bundle_scheme,
        "ledger_replay": {
            "event_count": len(loaded_events),
            "symbol": replayed.symbol,
            "profile": replayed.profile,
            "profile_mode": replayed.profile_mode,
            "service_scope": replayed.genesis_metadata.get("service_scope"),
            "billing_unit": replayed.genesis_metadata.get("billing_unit"),
            "consumption_model": replayed.genesis_metadata.get("consumption_model"),
            "supply": replayed.supply,
            "balances": dict(sorted(replayed.balances.items())),
            "state_hash": replayed.state_hash(),
        },
        "demo_catalog_workspace": _compact_demo_catalog_summary(demo_catalog_summary, source_catalog_dir),
        "demo_catalog_workspace_lint": _compact_lint_report(demo_catalog_lint),
        "publication_catalog_workspace": _compact_catalog_summary(catalog_summary, registry_catalog_dir),
        "publication_catalog_workspace_lint": _compact_lint_report(catalog_lint),
        "publication_network_workspace": _compact_network_summary(network_summary, source_network_dir),
        "publication_network_workspace_lint": _compact_lint_report(network_lint),
        "publication_registry_workspace": _compact_registry_summary(registry_summary, registry_workspace_dir),
        "publication_registry_workspace_lint": _compact_lint_report(registry_lint),
    }
    report["ok"] = all(
        [
            report["ledger_replay"]["profile"] == "SATROOT-MACHINE-1",
            report["ledger_replay"]["profile_mode"] == "prepaid-credit",
            report["demo_catalog_workspace_lint"]["ok"] is True,
            report["publication_catalog_workspace_lint"]["ok"] is True,
            report["publication_network_workspace_lint"]["ok"] is True,
            report["publication_registry_workspace_lint"]["ok"] is True,
        ]
    )
    report_path = output_path / "machine_profile_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay the checked-in machine-credit ledger example and generate a full "
            "SATROOT-MACHINE-1 publication registry workspace smoke report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_machine_profile_smoke_run",
        help="Directory where the generated machine publication registry workspace and report will be written.",
    )
    parser.add_argument(
        "--events-json",
        default=str(DEFAULT_EVENTS_JSON),
        help="Machine example events JSON to replay before publication generation.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_machine_profile_smoke(
        args.output_dir,
        events_json=args.events_json,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
