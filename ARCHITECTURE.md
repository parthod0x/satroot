# SATROOT Architecture

## One-line model

SATROOT is a BSV-anchored overlay protocol that turns one native satoshi into a root-bound namespace for deterministic semantic state.

## Core thesis

The base SATROOT claim is narrow and deliberate:

```text
1 satoshi -> 1 root-bound namespace -> unbounded protocol-defined state
```

That means:

- the satoshi remains one satoshi,
- the chain still enforces the native monetary floor,
- SATROOT events define higher-layer balances, rights, and objects above that floor,
- replay engines compute state deterministically from signed protocol records.

The guiding phrase is:

> A satoshi is the floor of value; it is not the ceiling of meaning.

## Layered architecture

### Layer 1: BSV anchor layer

BSV provides:

- the native satoshi,
- the root UTXO that SATROOT binds to,
- publication and timestamping,
- transaction ordering and custody,
- the witness layer for proving that protocol state was emitted.

BSV does not provide SATROOT balances, rights, or token semantics natively. Those remain overlay state.

### Layer 2: SATROOT kernel

`SATROOT-1` is the minimal kernel.

It defines:

- a `root_id` bound to a one-satoshi outpoint,
- a genesis record,
- signed lifecycle events,
- strict replay order,
- supply and balance invariants,
- authority rotation,
- deterministic validation rules.

This layer proves the primitive:

one native satoshi can anchor a replayable semantic ledger without creating sub-satoshis.

### Layer 3: Profile system

Profiles extend the same root-bound namespace model without changing the base primitive.

Current repo profiles include:

- `SATROOT-STABLE-1` for reference-only stable-value accounting,
- `SATROOT-MACHINE-1` for prepaid machine-credit balances,
- `SATROOT-RECEIPT-1` for invoice and receipt objects,
- `SATROOT-IDENTITY-1` for identity and authority objects,
- `SATROOT-LICENSE-1` for license and usage-right objects.

The base kernel stays small; profiles carry domain-specific semantics.

## Root lifecycle rules

The root satoshi is an anchor and authority handle, not a magical autonomous asset.

Important discipline:

- root satoshi movement is not automatically token movement,
- token movement occurs through valid SATROOT events,
- replay engines follow the SATROOT event chain,
- future on-chain settlement conventions can bind root movement more tightly, but the protocol state model must remain explicit.

In practical terms, the SATROOT ledger follows the valid signed event sequence, not arbitrary interpretation of UTXO activity.

## Deterministic state model

The replay engine should always be able to answer:

- what is the current authority state,
- what balances exist,
- what total supply is outstanding,
- whether any event violated protocol rules.

The key invariant is:

```text
total minted - total burned = sum(all balances)
```

Determinism depends on:

- strict sequencing,
- canonical event references,
- signer verification,
- replay halting on invalid events,
- machine-readable schemas and summaries.

## Deliverable framing

### v0.1 Genesis

The first deliverable is the base proof artifact:

- `SATROOT-1` kernel,
- `FLOOR1` example ledger,
- schemas,
- replay engine,
- signing helpers,
- bundle/release/catalog/index/publication tooling,
- tests,
- boundaries and release metadata.

What v0.1 proves:

one native satoshi can anchor deterministic semantic token state.

### v0.2 and later

Follow-on work should stay profile-driven:

- reference-value stable units,
- machine-credit networks,
- receipt and invoice flows,
- identity and license objects,
- richer publication and packaging workflows,
- future bridge layers for regulated or redeemable systems if ever needed.

## Full functionality envelope

At full maturity, SATROOT is not only a token protocol.

It is a satoshi-rooted semantic asset and rights layer capable of expressing:

- token balances,
- credits,
- receipts,
- invoices,
- licenses,
- identities,
- machine service rights,
- authority transitions,
- signed publication stacks and registries.

The common structure underneath all of them is the same:

one satoshi anchors a deterministic namespace, and signed SATROOT events describe the valid state transitions inside that namespace.

## Non-goals

SATROOT is not, by default:

- a new blockchain,
- a native BSV consensus change,
- a sub-satoshi protocol,
- a stablecoin issuer,
- a reserve or redemption system,
- a wallet standard,
- an exchange integration standard,
- a legal-rights framework by default.

Those may become profile or integration concerns later, but they should not be smuggled into the base kernel.
