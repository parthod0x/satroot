# SATROOT

**SATROOT** is a one-satoshi-rooted semantic asset protocol.

Its base primitive, **SATROOT-1**, treats one native BSV satoshi UTXO as the irreducible accounting floor and uses that UTXO as a root witness, authority handle, and namespace anchor for deterministic protocol state.

The core rule is simple:

> The satoshi is not subdivided. The satoshi anchors a protocol-defined state space.

## Project thesis

SATROOT starts from one idea:

> A satoshi is the floor of value; it is not the ceiling of meaning.

That means one satoshi can anchor a replayable semantic ledger without pretending to create sub-satoshis. Token units, credits, receipts, rights, and other objects live as protocol-defined state above the native chain unit.

## What this repo delivers

This repository currently ships the `SATROOT-1` genesis implementation:

- `SPEC.md` - human-readable v0.1 specification.
- `BOUNDARIES.md` - claim discipline, non-goals, and legal boundary language.
- `ROADMAP.md` - project scope, deliverables, and planned protocol profiles.
- `protocol/satroot1.schema.json` - JSON schema for genesis and event records.
- `protocol/satroot1.profile-registry.json` - explicit compatibility registry for supported profiles.
- `src/satroot1.py` - reference parser, deterministic replay engine, and signing utility CLI.
- `examples/` - the `FLOOR1` demo token ledger.
- `tests/test_satroot1.py` - validation tests for valid and invalid event flows.
- `profiles/stable/SATROOT-STABLE-1.md` - reference-only stable-value profile draft.
- `profiles/machine/SATROOT-MACHINE-1.md` - prepaid machine-credit profile draft.
- `profiles/receipt/SATROOT-RECEIPT-1.md` - receipt and invoice object profile draft.
- `profiles/identity/SATROOT-IDENTITY-1.md` - identity and authority object profile draft.
- `profiles/license/SATROOT-LICENSE-1.md` - license and usage-right object profile draft.

## SATROOT-1 in one sentence

`SATROOT-1` turns one satoshi into a root-bound namespace for deterministic semantic token state.

The v0.1 kernel defines:

- a `root_id` bound to a one-satoshi UTXO,
- a genesis record,
- `mint`, `transfer`, `burn`, and `rotate-authority` events,
- strict sequencing with `prev_event_id`,
- deterministic replay and balance computation,
- a supply invariant,
- explicit root authority rotation for mint-control handoff,
- registry-backed profile compatibility checks,
- a canonical signing payload model,
- a built-in `hmac-sha256` reference verifier path for shared-secret environments,
- an optional `ed25519` verifier path behind the `crypto` extra,
- explicit `signature_scheme` and `signature_key_id` protocol metadata,
- optional `event_id` and `state_hash` verification,
- reference helpers for signing a single event or a whole ledger,
- a `satroot1` CLI entry point for replay and signing workflows,
- verifier-aware CLI replay for `demo`, `hmac-sha256`, and `ed25519` ledgers,
- schema-aware CLI validation for raw SATROOT-1 JSON files,
- commitment-aware CLI annotation for adding deterministic `event_id` and `state_hash` fields,
- Ed25519 private-key generation helpers for bootstrapping SATROOT signing workflows,
- Ed25519 key-derivation helpers for producing replay-ready public key maps from private key maps,
- replay snapshots that preserve profile/genesis metadata for higher-layer namespace use cases.

## Current demo

`FLOOR1` is the proof token in this repo.

It demonstrates:

- one root satoshi,
- `1,000,000,000` semantic units,
- deterministic balance updates through signed protocol events,
- no claim that the satoshi itself has been subdivided.

## Intended use

SATROOT-1 is meant for prototypes, timestamped proof-of-concept work, and machine-native ledgers where balances are semantic protocol state anchored to a satoshi rather than native chain assets.

## Non-goals

SATROOT-1 does not claim to be:

- a new blockchain,
- a BSV consensus change,
- a sub-satoshi mechanism,
- a stablecoin by default,
- a redemption or reserve framework,
- a security token framework,
- an exchange-listing or universal wallet standard.

## Future direction

The base protocol stays intentionally small. Expansion belongs in separate profiles.

This repo now includes the first stable-value profile draft:

- `SATROOT-STABLE-1` for reference-value accounting units,
- `examples/genesis_usdroot1.json` for a `USDROOT1` genesis record,
- `examples/events_usdroot1.json` for a runnable reference-only ledger flow.

This repo also now includes the first machine-credit profile draft:

- `SATROOT-MACHINE-1` for prepaid machine-native service credits,
- `examples/genesis_apicredit1.json` for an `APICREDIT1` genesis record,
- `examples/events_apicredit1.json` for a runnable machine-credit ledger flow.

This repo also now includes the first receipt-object profile draft:

- `SATROOT-RECEIPT-1` for invoice and receipt state objects,
- `examples/genesis_receipt1.json` for a `RECEIPT1` genesis record,
- `examples/events_receipt1.json` for a runnable receipt lifecycle ledger flow.

This repo also now includes the first identity-object profile draft:

- `SATROOT-IDENTITY-1` for identity and authority state objects,
- `examples/genesis_identity1.json` for an `IDENTITY1` genesis record,
- `examples/events_identity1.json` for a runnable identity lifecycle ledger flow.

This repo also now includes the first license-object profile draft:

- `SATROOT-LICENSE-1` for license and usage-right state objects,
- `examples/genesis_license1.json` for a `LICENSE1` genesis record,
- `examples/events_license1.json` for a runnable license lifecycle ledger flow.

Future profile work can extend that pattern for:

- additional authority object profiles,
- additional rights profiles.

## Run tests

```bash
python -m pytest
```

Expected result:

```text
48 passed
```

## Signing utilities

Install the package in editable mode to expose the `satroot1` command:

```bash
pip install -e .
```

Install the optional crypto path when you want Ed25519 support:

```bash
pip install -e .[crypto]
```

Install the optional schema-validation path when you want `satroot1 validate`:

```bash
pip install -e .[validation]
```

Install both optional paths together:

```bash
pip install -e .[crypto,validation]
```

Replay a ledger:

```bash
satroot1 replay examples/events_floor1.json
```

Replay an HMAC-signed ledger with verifier material:

```bash
satroot1 replay signed_events.json --scheme hmac-sha256 --secrets-json secrets.json
```

Validate a raw SATROOT event file against the protocol schema:

```bash
satroot1 validate examples/events_floor1.json
```

Annotate a ledger with deterministic event commitments:

```bash
satroot1 annotate-ledger examples/events_floor1.json --output annotated_events.json
```

Sign a full demo ledger with the built-in demo signature mode:

```bash
satroot1 sign-ledger examples/events_floor1.json --scheme demo
```

Sign a ledger with shared-secret HMAC verification metadata:

```bash
satroot1 sign-ledger examples/events_floor1.json --scheme hmac-sha256 --signer-key-map-json signer_keys.json --secrets-json secrets.json --include-state-hash --output signed_events.json
```

Replay an Ed25519-signed ledger with public keys:

```bash
satroot1 replay signed_events.json --scheme ed25519 --public-keys-json public_keys.json
```

Generate an Ed25519 private-key map for SATROOT key IDs:

```bash
satroot1 generate-ed25519-private-keys --key-id issuer-key --key-id alice-key --output private_keys.json
```

Derive an Ed25519 public-key map from SATROOT private keys:

```bash
satroot1 derive-ed25519-public-keys private_keys.json --output public_keys.json
```

Annotate a signed HMAC ledger without changing its signed payload:

```bash
satroot1 annotate-ledger signed_events.json --scheme hmac-sha256 --secrets-json secrets.json --output annotated_signed_events.json
```

Sign a single event record:

```bash
satroot1 sign-event event.json --scheme hmac-sha256 --key-id issuer-key --secret issuer-secret
```

The legacy direct script flow still works:

```bash
python src/satroot1.py examples/events_floor1.json
```

## Run the demo ledgers

```bash
satroot1 replay examples/events_floor1.json
```

Reference-only stable profile demo:

```bash
satroot1 replay examples/events_usdroot1.json
```

Machine-credit profile demo:

```bash
satroot1 replay examples/events_apicredit1.json
```

Receipt profile demo:

```bash
satroot1 replay examples/events_receipt1.json
```

Identity profile demo:

```bash
satroot1 replay examples/events_identity1.json
```

License profile demo:

```bash
satroot1 replay examples/events_license1.json
```

## Important demo note

The example `root_id` values in `examples/` are placeholders:

```text
0000000000000000000000000000000000000000000000000000000000000000:0
```

Replace it only when intentionally anchoring to a real one-satoshi UTXO.
