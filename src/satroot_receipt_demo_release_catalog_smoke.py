from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from satroot_singleton_demo_release_smoke_support import (
    run_singleton_demo_release_catalog_smoke,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = "SATROOT-RECEIPT-1"
DEFAULT_BASE_PRESET_JSON = REPO_ROOT / "examples" / "catalog_presets" / "receipt_invoice_catalog.json"
VARIANTS = [
    (
        "receipt_catalog_alpha.json",
        "RECCAT01",
        "Receipt Catalog Alpha",
        {
            "document_type": "invoice-receipt",
            "reference_id": "INV-2026-CATALOG-ALPHA",
            "issuer_entity": "ops-ledger-alpha",
            "counterparty_entity": "vendor-alpha",
            "settlement_unit": "USD",
            "intended_use": "receipt-catalog-alpha",
        },
        {
            "holder_account": "receipt_catalog_holder_alpha",
            "archive_account": "receipt_catalog_archive_alpha",
            "retire": False,
        },
        {
            "channel": "alpha",
            "label": "Receipt Catalog Alpha Release",
            "published_at": "2026-08-16T00:00:00Z",
        },
    ),
    (
        "receipt_catalog_beta.json",
        "RECCAT02",
        "Receipt Catalog Beta",
        {
            "document_type": "invoice-receipt",
            "reference_id": "INV-2026-CATALOG-BETA",
            "issuer_entity": "ops-ledger-beta",
            "counterparty_entity": "vendor-beta",
            "settlement_unit": "EUR",
            "intended_use": "receipt-catalog-beta",
        },
        {
            "holder_account": "receipt_catalog_holder_beta",
            "archive_account": "receipt_catalog_archive_beta",
            "retire": False,
        },
        {
            "channel": "beta",
            "label": "Receipt Catalog Beta Release",
            "published_at": "2026-08-17T00:00:00Z",
        },
    ),
]


def run_receipt_demo_release_catalog_smoke(
    output_dir: str | Path,
    *,
    base_preset_json: str | Path = DEFAULT_BASE_PRESET_JSON,
    bundle_scheme: str = "hmac-sha256",
    signature_scheme: str | None = None,
) -> dict[str, object]:
    return run_singleton_demo_release_catalog_smoke(
        output_dir,
        profile=PROFILE,
        base_preset_json=base_preset_json,
        variants=VARIANTS,
        bundle_scheme=bundle_scheme,
        signature_scheme=signature_scheme,
        catalog_metadata={
            "channel": "receipt",
            "label": "Receipt Demo Release Catalog Smoke",
            "published_at": "2026-08-18T00:00:00Z",
        },
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the receipt singleton demo release-catalog publication convenience flow "
            "from staged presets and emit a compact verification report."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=".tmp_receipt_demo_release_catalog_smoke_run",
        help="Directory where the generated release collection, catalog publication, and report will be written.",
    )
    parser.add_argument(
        "--base-preset-json",
        default=str(DEFAULT_BASE_PRESET_JSON),
        help="Checked-in receipt demo catalog preset used as the source template for staged smoke variants.",
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
    report = run_receipt_demo_release_catalog_smoke(
        args.output_dir,
        base_preset_json=args.base_preset_json,
        bundle_scheme=args.bundle_scheme,
        signature_scheme=args.signature_scheme,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
