# SATROOT Roadmap

## Project position

SATROOT is a BSV-anchored overlay protocol for deterministic semantic assets.

The base idea is:

`1 satoshi -> 1 root-bound namespace -> unbounded protocol-defined state`

The project should remain disciplined about this separation:

- BSV anchors the root satoshi and provides ordering, publication, and custody.
- SATROOT defines semantic balances, rights, and validity rules above that root.

## Current deliverable

`v0.1` is the genesis proof artifact for `SATROOT-1`.

It proves that one native satoshi can anchor an arbitrary semantic ledger without claiming subdivision below one satoshi.

Current scope:

- root-bound namespace via `root_id`
- token genesis
- `mint`, `transfer`, and `burn`
- sequence enforcement
- deterministic replay
- supply invariants
- example token `FLOOR1`

## Near-term build order

### v0.1 Genesis

Goal: freeze the primitive.

- Publish `SATROOT-1` as the minimal kernel.
- Keep boundary language strict.
- Keep implementation small and auditable.

### v0.2 Stable profile

Goal: add reference-value accounting without changing the base primitive.

- Add `SATROOT-STABLE-1` as a profile only.
- Include `USDROOT1` or `INRROOT1` example records.
- Keep claims reference-only unless a later legal/compliance layer exists.

Current status:

- `SATROOT-STABLE-1` draft exists in this repo.
- `USDROOT1` reference-only examples are included as the first profile implementation artifact.

### v0.3 Namespace expansion

Goal: show that the root is more than a token anchor.

- Define receipt and invoice objects.
- Define machine-credit balances.
- Define rights, license, or identity records.

## Core architectural rule

SATROOT does not merely mint tokens from one satoshi.

It turns one satoshi into a root-bound namespace for deterministic semantic state.

That namespace may later support:

- tokens,
- credits,
- receipts,
- licenses,
- identities,
- machine-readable rights,
- event streams.

## Non-goals for the base protocol

The `SATROOT-1` kernel should not absorb:

- stablecoin reserve logic,
- redemption systems,
- exchange integration assumptions,
- wallet interoperability claims,
- legal-rights claims by default,
- production signature standards before the data model is settled.
