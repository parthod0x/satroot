from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from satroot_singleton_demo_release_smoke_support import (
    run_singleton_demo_release_catalog_index_smoke,
)


from satroot1 import examples_root as _examples_root

EXAMPLES_ROOT = _examples_root()
PROFILE = "SATROOT-IDENTITY-1"
DEFAULT_BASE_PRESET_JSON = EXAMPLES_ROOT / "catalog_presets" / "identity_authority_catalog.json"
VARIANTS = [
    (
        "identity_index_alpha.json",
        "IDIDX01",
        "Identity Index Alpha",
        {
            "identity_type": "service-identity",
            "subject_id": "ops-index-alpha",
            "controller_entity": "operations-alpha",
            "authority_scope": "admin-alpha",
            "intended_use": "identity-index-alpha",
        },
        {
            "holder_account": "identity_index_holder_alpha",
            "next_holder": "identity_index_next_alpha",
            "retire": False,
        },
        {
            "channel": "alpha",
            "label": "Identity Index Alpha Release",
            "published_at": "2026-08-16T00:00:00Z",
        },
    ),
    (
        "identity_index_beta.json",
        "IDIDX02",
        "Identity Index Beta",
        {
            "identity_type": "service-identity",
            "subject_id": "ops-index-beta",
            "controller_entity": "operations-beta",
            "authority_scope": "admin-beta",
            "intended_use": "identity-index-beta",
        },
        {
            "holder_account": "identity_index_holder_beta",
            "next_holder": "identity_index_next_beta",
            "retire": False,
        },
        {
            "channel": "beta",
            "label": "Identity Index Beta Release",
            "published_at": "2026-08-17T00:00:00Z",
        },
    ),
]


def run_identity_demo_release_catalog_index_smoke(
    output_dir: str | Path,
    *,
    base_preset_json: str | Path = DEFAULT_BASE_PRESET_JSON,
    bundle_scheme: str = "hmac-sha256",
    catalog_signature_scheme: str | None = None,
    index_signature_scheme: str | None = None,
) -> dict[str, object]:
    return run_singleton_demo_release_catalog_index_smoke(
        output_dir,
        profile=PROFILE,
        base_preset_json=base_preset_json,
        variants=VARIANTS,
        bundle_scheme=bundle_scheme,
        catalog_signature_scheme=catalog_signature_scheme,
        index_signature_scheme=index_signature_scheme,
        catalog_metadata={
            "channel": "identity",
            "label": "Identity Demo Release Catalog Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
        index_metadata={
            "channel": "identity",
            "label": "Identity Demo Release Catalog Index Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the identity singleton demo release-catalog index publication convenience flow "
            "from staged presets and emit a compact verification report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_identity_demo_release_catalog_index_smoke_run",
        help="Directory where the generated release collection, catalog publication, index publication, and report will be written.",
    )
    parser.add_argument(
        "--base-preset-json",
        default=str(DEFAULT_BASE_PRESET_JSON),
        help="Checked-in identity demo catalog preset used as the source template for staged smoke variants.",
    )
    parser.add_argument(
        "--bundle-scheme",
        default="hmac-sha256",
        help="Signing scheme for generated bundle, release, catalog, and index artifacts.",
    )
    parser.add_argument(
        "--catalog-signature-scheme",
        default=None,
        help="Optional release-catalog publication signing override; defaults to --bundle-scheme.",
    )
    parser.add_argument(
        "--index-signature-scheme",
        default=None,
        help="Optional release-catalog-index publication signing override; defaults to --bundle-scheme.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_identity_demo_release_catalog_index_smoke(
        args.output_dir,
        base_preset_json=args.base_preset_json,
        bundle_scheme=args.bundle_scheme,
        catalog_signature_scheme=args.catalog_signature_scheme,
        index_signature_scheme=args.index_signature_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
