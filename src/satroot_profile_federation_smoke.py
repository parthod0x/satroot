from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from satroot1 import (
    bootstrap_demo_catalog_workspace_collection,
    bootstrap_publication_catalog_workspace_collection,
    bootstrap_publication_network_collection,
    bootstrap_publication_registry_workspace_collection,
    bootstrap_publication_stack_collection,
    lint_demo_catalog_workspace_collection,
    lint_publication_catalog_workspace,
    lint_publication_catalog_workspace_collection,
    lint_publication_network_collection,
    lint_publication_network_workspace,
    lint_publication_registry_workspace,
    lint_publication_registry_workspace_collection,
    lint_publication_stack_collection,
    lint_publication_stack_workspace,
    publish_publication_network_workspace,
    publish_publication_registry_workspace,
    publish_publication_stack_workspace,
    summarize_demo_catalog_workspace_collection,
    summarize_publication_catalog_workspace,
    summarize_publication_catalog_workspace_collection,
    summarize_publication_network_collection,
    summarize_publication_network_workspace,
    summarize_publication_registry_workspace,
    summarize_publication_registry_workspace_collection,
    summarize_publication_stack_collection,
    summarize_publication_stack_workspace,
    write_publication_catalog_workspace,
)
from satroot_profile_matrix_smoke import run_profile_matrix_smoke


PROFILE_ORDER = ("stable", "machine", "receipt", "identity", "license")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_compact_network_stack_workspace_dir(profile_report: Mapping[str, Any]) -> Path:
    compact_network = profile_report["publication_network_workspace"]
    network_workspace_dir = Path(str(compact_network["workspace_dir"])).resolve()
    workspace_names = compact_network.get("workspace_names")
    if not isinstance(workspace_names, list) or len(workspace_names) != 1:
        raise ValueError("profile federation smoke expected exactly one source publication stack workspace")
    workspace_name = workspace_names[0]
    if not isinstance(workspace_name, str) or not workspace_name.strip():
        raise ValueError("profile federation smoke source publication stack workspace name must be non-empty")

    stack_workspace_dir = (network_workspace_dir / "stack_workspaces" / workspace_name).resolve()
    if not stack_workspace_dir.is_dir():
        raise ValueError(
            "profile federation smoke could not resolve source publication stack workspace "
            f"at {stack_workspace_dir}"
        )
    return stack_workspace_dir


def run_profile_federation_smoke(
    output_dir: str | Path,
    *,
    bundle_scheme: str = "hmac-sha256",
    release_catalog_key_id: str = "release-catalog-key",
    release_catalog_index_key_id: str = "release-catalog-index-key",
) -> dict[str, Any]:
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    matrix_report = run_profile_matrix_smoke(output_path / "profile_matrix_source", bundle_scheme=bundle_scheme)
    profile_reports = matrix_report["profile_reports"]

    demo_catalog_dirs = [
        Path(str(profile_reports[name]["demo_catalog_workspace"]["workspace_dir"])).resolve()
        for name in PROFILE_ORDER
    ]
    publication_stack_dirs = [
        _resolve_compact_network_stack_workspace_dir(profile_reports[name])
        for name in PROFILE_ORDER
    ]
    publication_network_dirs = [
        Path(str(profile_reports[name]["publication_network_workspace"]["workspace_dir"])).resolve()
        for name in PROFILE_ORDER
    ]
    publication_catalog_workspace_dirs = [
        Path(str(profile_reports[name]["publication_catalog_workspace"]["workspace_dir"])).resolve()
        for name in PROFILE_ORDER
    ]
    publication_registry_workspace_dirs = [
        Path(str(profile_reports[name]["publication_registry_workspace"]["workspace_dir"])).resolve()
        for name in PROFILE_ORDER
    ]

    demo_catalog_collection_dir = output_path / "demo_catalog_workspace_collection"
    bootstrap_demo_catalog_workspace_collection(
        demo_catalog_dirs,
        output_dir=demo_catalog_collection_dir,
    )
    demo_catalog_collection_summary = summarize_demo_catalog_workspace_collection(demo_catalog_collection_dir)
    demo_catalog_collection_lint = lint_demo_catalog_workspace_collection(demo_catalog_collection_dir)

    federated_stack_dir = output_path / "federated_publication_stack"
    publish_publication_stack_workspace(
        demo_catalog_dirs,
        output_dir=federated_stack_dir,
        signature_scheme=bundle_scheme,
        key_id=release_catalog_key_id,
        catalog_workspace_collection_dir=demo_catalog_collection_dir,
        release_catalog_metadata={
            "channel": "federation",
            "label": "Released Profile Federation Release Catalog",
        },
    )
    federated_stack_summary = summarize_publication_stack_workspace(federated_stack_dir)
    federated_stack_lint = lint_publication_stack_workspace(federated_stack_dir)

    publication_stack_collection_dir = output_path / "publication_stack_collection"
    bootstrap_publication_stack_collection(
        publication_stack_dirs,
        output_dir=publication_stack_collection_dir,
    )
    publication_stack_collection_summary = summarize_publication_stack_collection(
        publication_stack_collection_dir
    )
    publication_stack_collection_lint = lint_publication_stack_collection(
        publication_stack_collection_dir
    )

    federated_network_dir = output_path / "federated_publication_network"
    publish_publication_network_workspace(
        [federated_stack_dir],
        output_dir=federated_network_dir,
        signature_scheme=bundle_scheme,
        key_id=release_catalog_index_key_id,
        publication_stack_collection_dir=publication_stack_collection_dir,
        release_catalog_index_metadata={
            "channel": "federation",
            "label": "Released Profile Federation Release Catalog Index",
        },
    )
    federated_network_summary = summarize_publication_network_workspace(federated_network_dir)
    federated_network_lint = lint_publication_network_workspace(federated_network_dir)

    federated_catalog_workspace_dir = output_path / "federated_publication_catalog_workspace"
    write_publication_catalog_workspace(
        artifact_paths=[],
        discover_under=demo_catalog_dirs,
        recursive=True,
        output_dir=federated_catalog_workspace_dir,
        signature_scheme=bundle_scheme,
        publication_descriptor_index_key_id="publication-descriptor-index-key",
        publication_metadata_key_id="publication-metadata-key",
        publication_metadata_catalog_key_id="publication-metadata-catalog-key",
    )
    federated_catalog_workspace_summary = summarize_publication_catalog_workspace(
        federated_catalog_workspace_dir
    )
    federated_catalog_workspace_lint = lint_publication_catalog_workspace(
        federated_catalog_workspace_dir
    )
    federated_catalog_workspace_collection_dir = (
        output_path / "federated_publication_catalog_workspace_collection"
    )
    bootstrap_publication_catalog_workspace_collection(
        [federated_catalog_workspace_dir],
        output_dir=federated_catalog_workspace_collection_dir,
    )
    federated_catalog_workspace_collection_summary = summarize_publication_catalog_workspace_collection(
        federated_catalog_workspace_collection_dir
    )
    federated_catalog_workspace_collection_lint = lint_publication_catalog_workspace_collection(
        federated_catalog_workspace_collection_dir
    )

    federated_registry_workspace_dir = output_path / "federated_publication_registry_workspace"
    publish_publication_registry_workspace(
        publication_catalog_workspace_dir=federated_catalog_workspace_dir,
        release_catalog_index_dir=federated_network_dir / "release_catalog_index",
        publication_network_dir=federated_network_dir,
        output_dir=federated_registry_workspace_dir,
        signature_scheme=bundle_scheme,
        key_id="publication-registry-key",
        publication_registry_metadata={
            "channel": "federation",
            "label": "Released Profile Federation Publication Registry",
        },
    )
    federated_registry_workspace_summary = summarize_publication_registry_workspace(
        federated_registry_workspace_dir
    )
    federated_registry_workspace_lint = lint_publication_registry_workspace(
        federated_registry_workspace_dir
    )
    federated_registry_workspace_collection_dir = (
        output_path / "federated_publication_registry_workspace_collection"
    )
    bootstrap_publication_registry_workspace_collection(
        [federated_registry_workspace_dir],
        output_dir=federated_registry_workspace_collection_dir,
    )
    federated_registry_workspace_collection_summary = summarize_publication_registry_workspace_collection(
        federated_registry_workspace_collection_dir
    )
    federated_registry_workspace_collection_lint = lint_publication_registry_workspace_collection(
        federated_registry_workspace_collection_dir
    )

    publication_network_collection_dir = output_path / "publication_network_collection"
    bootstrap_publication_network_collection(
        publication_network_dirs,
        output_dir=publication_network_collection_dir,
    )
    publication_network_collection_summary = summarize_publication_network_collection(
        publication_network_collection_dir
    )
    publication_network_collection_lint = lint_publication_network_collection(
        publication_network_collection_dir
    )

    publication_catalog_workspace_collection_dir = output_path / "publication_catalog_workspace_collection"
    bootstrap_publication_catalog_workspace_collection(
        publication_catalog_workspace_dirs,
        output_dir=publication_catalog_workspace_collection_dir,
    )
    publication_catalog_workspace_collection_summary = summarize_publication_catalog_workspace_collection(
        publication_catalog_workspace_collection_dir
    )
    publication_catalog_workspace_collection_lint = lint_publication_catalog_workspace_collection(
        publication_catalog_workspace_collection_dir
    )

    publication_registry_workspace_collection_dir = output_path / "publication_registry_workspace_collection"
    bootstrap_publication_registry_workspace_collection(
        publication_registry_workspace_dirs,
        output_dir=publication_registry_workspace_collection_dir,
    )
    publication_registry_workspace_collection_summary = summarize_publication_registry_workspace_collection(
        publication_registry_workspace_collection_dir
    )
    publication_registry_workspace_collection_lint = lint_publication_registry_workspace_collection(
        publication_registry_workspace_collection_dir
    )

    report: dict[str, Any] = {
        "bundle_scheme": bundle_scheme,
        "profile_matrix": {
            "ok": matrix_report["ok"],
            "profile_count": matrix_report["profile_count"],
            "profiles": matrix_report["profiles"],
            "report_path": matrix_report["report_path"],
        },
        "demo_catalog_workspace_collection": demo_catalog_collection_summary,
        "demo_catalog_workspace_collection_lint": demo_catalog_collection_lint,
        "publication_stack_workspace": federated_stack_summary,
        "publication_stack_workspace_lint": federated_stack_lint,
        "publication_stack_collection": publication_stack_collection_summary,
        "publication_stack_collection_lint": publication_stack_collection_lint,
        "publication_network_workspace": federated_network_summary,
        "publication_network_workspace_lint": federated_network_lint,
        "publication_catalog_workspace": federated_catalog_workspace_summary,
        "publication_catalog_workspace_lint": federated_catalog_workspace_lint,
        "federated_publication_catalog_workspace_collection": federated_catalog_workspace_collection_summary,
        "federated_publication_catalog_workspace_collection_lint": federated_catalog_workspace_collection_lint,
        "publication_registry_workspace": federated_registry_workspace_summary,
        "publication_registry_workspace_lint": federated_registry_workspace_lint,
        "federated_publication_registry_workspace_collection": federated_registry_workspace_collection_summary,
        "federated_publication_registry_workspace_collection_lint": federated_registry_workspace_collection_lint,
        "publication_network_collection": publication_network_collection_summary,
        "publication_network_collection_lint": publication_network_collection_lint,
        "publication_catalog_workspace_collection": publication_catalog_workspace_collection_summary,
        "publication_catalog_workspace_collection_lint": publication_catalog_workspace_collection_lint,
        "publication_registry_workspace_collection": publication_registry_workspace_collection_summary,
        "publication_registry_workspace_collection_lint": publication_registry_workspace_collection_lint,
    }
    report["ok"] = all(
        [
            report["profile_matrix"]["ok"] is True,
            report["demo_catalog_workspace_collection_lint"]["ok"] is True,
            report["publication_stack_workspace_lint"]["ok"] is True,
            report["publication_stack_collection_lint"]["ok"] is True,
            report["publication_network_workspace_lint"]["ok"] is True,
            report["publication_catalog_workspace_lint"]["ok"] is True,
            report["federated_publication_catalog_workspace_collection_lint"]["ok"] is True,
            report["publication_registry_workspace_lint"]["ok"] is True,
            report["federated_publication_registry_workspace_collection_lint"]["ok"] is True,
            report["publication_network_collection_lint"]["ok"] is True,
            report["publication_catalog_workspace_collection_lint"]["ok"] is True,
            report["publication_registry_workspace_collection_lint"]["ok"] is True,
        ]
    )

    report_path = output_path / "profile_federation_smoke_report.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the released profile matrix smoke flow, then prove mixed-profile "
            "publication federation via shared stack/network outputs and explicit collections."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_profile_federation_smoke_run",
        help="Directory where the generated federation workspaces and report will be written.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signature scheme for generated bundle and publication artifacts.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_profile_federation_smoke(
        args.output_dir,
        bundle_scheme=args.bundle_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
