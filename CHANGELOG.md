# Changelog

## Unreleased

- Adds the first `SATROOT-STABLE-1` reference-only profile draft.
- Adds `USDROOT1` stable-value example genesis and event ledgers.
- Adds the first `SATROOT-MACHINE-1` prepaid-credit profile draft.
- Adds `APICREDIT1` machine-credit example genesis and event ledgers.
- Adds the first `SATROOT-RECEIPT-1` single-receipt profile draft.
- Adds `RECEIPT1` receipt-object example genesis and event ledgers.
- Adds the first `SATROOT-IDENTITY-1` single-identity profile draft.
- Adds `IDENTITY1` identity-object example genesis and event ledgers.
- Extends the schema to describe optional stable-profile metadata.
- Generalizes profile metadata so non-stable profiles can define their own modes.
- Adds replay tests for the `USDROOT1`, `APICREDIT1`, `RECEIPT1`, and `IDENTITY1` demo ledgers.

## v0.1.0 - 2026-06-19

Genesis draft of SATROOT-1.

- Defines one native satoshi UTXO as a root witness, authority handle, and namespace anchor.
- Defines semantic supply above the root satoshi without subdividing the satoshi.
- Frames SATROOT-1 as the base kernel of the broader SATROOT project.
- Adds FLOOR1 demo token with 1,000,000,000 semantic units.
- Adds JSON schema, Python replay engine, examples, and tests.
- Explicitly excludes stablecoin, security token, exchange-listing, or legal-rights claims from the base protocol.
