# SATROOT Architecture

## One-line model

SATROOT is a deterministic ledger protocol with optional, interchangeable commitment backends (RFC 3161 or BSV) that turns one native satoshi into a root-bound namespace for deterministic semantic state.

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
- the witness layer for proving that protocol state was emitted — exercised by the released envelope build and verify lanes.

BSV does not provide SATROOT balances, rights, or token semantics natively. Those remain overlay state.

#### Anchoring loop

The released anchoring loop demonstrates Layer 1 against the real chain while keeping the repository itself offline and deterministic: the anchored demo lane binds a `root_id`, the anchored publication lane publishes that namespace with ed25519 end to end, the on-chain envelope lane builds the SPEC section 4 commitment script, and the envelope verification lane re-verifies a broadcast envelope from raw transaction bytes. Every intentional run against a real outpoint is recorded in `ANCHORS.md`, the only place in the repository where a real outpoint or transaction id may appear.

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
- `SATROOT-LICENSE-1` for license and usage-right objects,
- `SATROOT-EVENT-1` for append-only event-stream head objects.

The base kernel stays small; profiles carry domain-specific semantics.

## Root lifecycle rules

The root satoshi is an anchor and authority handle, not a magical autonomous asset.

Important discipline:

- root satoshi movement is not automatically token movement,
- token movement occurs through valid SATROOT events,
- replay engines follow the SATROOT event chain,
- the released SPEC section 4 commitment convention already binds namespace state on-chain; tighter root-movement settlement conventions remain future work, and the protocol state model must remain explicit.

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

### Delivered (v0.1 through v0.9)

The released line covers:

- the `SATROOT-1` kernel, schemas, replay engine, and signing helpers,
- the `FLOOR1` example ledger plus six registered profiles with full demo-catalog-matrix lanes: reference-value stable units, machine credits, receipts, identities, licenses, and event-stream heads,
- bundle/release/catalog/index/publication tooling up through mixed-profile federation and collection-backed registry round trips,
- the anchored loop: anchored demo namespace, anchored publication, on-chain envelope builder, and offline envelope verifier, with real runs recorded in `ANCHORS.md`,
- the eight-surface operator proof, the local release gate, tests, boundaries, and release metadata.

What the released line proves: one native satoshi — including one real testnet satoshi — can anchor deterministic semantic token state that publishes, commits on-chain, and verifies offline.

### Follow-on

Remaining follow-on work stays profile-driven:

- additional object classes beyond the six registered profiles,
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
