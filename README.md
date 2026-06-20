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
- `src/satroot1.py` - reference parser and deterministic replay engine.
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
- `mint`, `transfer`, and `burn` events,
- strict sequencing with `prev_event_id`,
- deterministic replay and balance computation,
- a supply invariant,
- registry-backed profile compatibility checks,
- a canonical signing payload model,
- optional `event_id` and `state_hash` verification.

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
19 passed
```

## Run the demo ledger

```bash
python src/satroot1.py examples/events_floor1.json
```

Reference-only stable profile demo:

```bash
python src/satroot1.py examples/events_usdroot1.json
```

Machine-credit profile demo:

```bash
python src/satroot1.py examples/events_apicredit1.json
```

Receipt profile demo:

```bash
python src/satroot1.py examples/events_receipt1.json
```

Identity profile demo:

```bash
python src/satroot1.py examples/events_identity1.json
```

License profile demo:

```bash
python src/satroot1.py examples/events_license1.json
```

## Important demo note

The example `root_id` values in `examples/` are placeholders:

```text
0000000000000000000000000000000000000000000000000000000000000000:0
```

Replace it only when intentionally anchoring to a real one-satoshi UTXO.
