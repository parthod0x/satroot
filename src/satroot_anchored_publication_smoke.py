from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from satroot1 import (
    SatRootError,
    bootstrap_singleton_demo_publication_registry_workspace_from_presets,
    ed25519_available,
    lint_publication_registry_workspace,
    summarize_publication_registry_workspace,
    validate_root_id,
)
from satroot_anchored_demo_smoke import PLACEHOLDER_ROOT_ID


from satroot1 import examples_root as _examples_root

EXAMPLES_ROOT = _examples_root()
PROFILE = "SATROOT-IDENTITY-1"
BUNDLE_SCHEME = "ed25519"
DEFAULT_PRESET_JSON = EXAMPLES_ROOT / "catalog_presets" / "identity_authority_catalog.json"


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def run_anchored_publication_smoke(
    output_dir: str | Path,
    *,
    root_id: str = PLACEHOLDER_ROOT_ID,
    preset_json: str | Path = DEFAULT_PRESET_JSON,
) -> dict[str, Any]:
    if not ed25519_available():
        raise SatRootError(
            "cryptography package is required for the anchored publication smoke lane; "
            "install the [crypto] extra"
        )
    validate_root_id(root_id)

    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    resolved_preset = Path(preset_json).resolve()

    bootstrap_singleton_demo_publication_registry_workspace_from_presets(
        [resolved_preset],
        profile=PROFILE,
        bundle_scheme=BUNDLE_SCHEME,
        root_id=root_id,
        output_dir=output_path,
        release_key_id="release-key",
        release_catalog_key_id="release-catalog-key",
        release_catalog_index_key_id="release-catalog-index-key",
        publication_descriptor_index_key_id="publication-descriptor-index-key",
        publication_metadata_key_id="publication-metadata-key",
        publication_metadata_catalog_key_id="publication-metadata-catalog-key",
        publication_registry_key_id="publication-registry-key",
        release_metadata_overrides={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Release",
        },
        release_catalog_metadata={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Release Catalog",
        },
        release_catalog_index_metadata={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Release Catalog Index",
        },
        descriptor_index_metadata={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Descriptor Index",
        },
        publication_metadata_catalog_metadata={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Metadata Catalog",
        },
        publication_registry_metadata={
            "channel": "anchored",
            "label": "Anchored Publication Smoke Registry",
        },
    )

    registry_summary = summarize_publication_registry_workspace(output_path)
    registry_lint = lint_publication_registry_workspace(output_path)

    genesis_paths = sorted(output_path.rglob("bundles/*/genesis.json"))
    genesis_root_ids = sorted(
        {
            json.loads(path.read_text(encoding="utf-8")).get("root_id")
            for path in genesis_paths
        }
    )
    registry_manifest_path = Path(str(registry_summary["publication_registry_manifest_path"])).resolve()
    metadata_catalog_manifest_path = Path(
        str(registry_summary["publication_metadata_catalog_manifest_path"])
    ).resolve()

    checks = {
        "registry_workspace_lint_ok": registry_lint.get("ok") is True,
        "bundles_generated": len(genesis_paths) > 0,
        "root_id_bound_in_every_bundle": genesis_root_ids == [root_id],
        "registry_manifest_present": registry_manifest_path.is_file(),
    }

    report: dict[str, Any] = {
        "lane": "anchored-publication",
        "profile": PROFILE,
        "bundle_scheme": BUNDLE_SCHEME,
        "root_id": root_id,
        "root_is_placeholder": root_id == PLACEHOLDER_ROOT_ID,
        "preset_json": str(resolved_preset),
        "bundle_genesis_count": len(genesis_paths),
        "artifact_count": registry_summary.get("artifact_count"),
        "publication_registry_dir": registry_summary.get("publication_registry_dir"),
        "checks": checks,
        "artifact_hashes": {
            "publication_registry_manifest": _sha256_file(registry_manifest_path),
            "publication_metadata_catalog_manifest": _sha256_file(metadata_catalog_manifest_path),
        },
    }
    report["ok"] = all(checks.values())

    report_path = output_path / "anchored_publication_smoke_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report["report_path"] = str(report_path)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish the anchored identity demo namespace through the full "
            "publication ladder — signed bundle, release, catalog, and registry "
            "workspace — with ed25519 signing end to end, and verify the root "
            "binding in every generated bundle."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_anchored_publication_smoke_run",
        help="Directory where the generated publication registry workspace and report will be written.",
    )
    parser.add_argument(
        "--root-id",
        default=PLACEHOLDER_ROOT_ID,
        help=(
            "Namespace root_id as <txid>:<vout>. Defaults to the demo placeholder; "
            "pass a real one-satoshi outpoint only when intentionally anchoring."
        ),
    )
    parser.add_argument(
        "--preset-json",
        default=str(DEFAULT_PRESET_JSON),
        help="Identity demo catalog preset used to generate the publication registry workspace.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_anchored_publication_smoke(
        args.output_dir,
        root_id=args.root_id,
        preset_json=args.preset_json,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
