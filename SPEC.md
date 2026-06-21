# SATROOT-1 v0.1 Specification

Status: Draft v0.1
Date: 2026-06-19
License: Apache-2.0

## 1. Purpose

SATROOT-1 defines a minimal token primitive in which a single native satoshi UTXO acts as the root witness and authority handle for an arbitrary higher-layer token ledger.

It is designed to make one idea precise:

> There is no smaller Bitcoin unit below one satoshi, but there can be unbounded protocol-defined semantic state above one satoshi.

Within the broader SATROOT project, this base primitive should also be understood as a root-bound namespace kernel. The root satoshi does not merely anchor one token balance. It anchors a deterministic protocol namespace under which semantic objects can later exist.

## 2. Core concepts

### 2.1 Root satoshi

A **root satoshi** is a UTXO with native value exactly `1 satoshi`.

The root satoshi is not divided. It is used as a carrier, anchor, authority witness, or namespace handle.

### 2.2 Root ID

The **root_id** is the outpoint of the root satoshi:

```text
<genesis_txid>:<vout>
```

This root_id identifies the token universe.

### 2.3 Semantic supply

The token supply is not native Bitcoin supply. It is semantic supply defined by protocol records.

A SATROOT-1 token can have:

- fixed supply,
- capped minting,
- uncapped minting,
- authority-controlled minting,
- no further minting after genesis.

### 2.4 Root-bound namespace

The deeper SATROOT model is:

```text
1 satoshi -> 1 root namespace -> many semantic objects
```

In `SATROOT-1`, that namespace is used only for a token ledger. Future profiles may use the same root structure for receipts, credits, licenses, identities, or machine-readable rights.

### 2.5 Event ledger

Token balances are computed by replaying signed SATROOT-1 events:

- `genesis`
- `mint`
- `transfer`
- `burn`
- `rotate-authority`
- `freeze` optional in future versions
- `delegate` optional in future versions

Every non-genesis event must reference:

- `root_id`
- `prev_event_id`
- `sequence`
- `action`
- action-specific fields such as `from`, `to`, and `amount`
- `signer`
- `signature`

When present, `signature_scheme` and `signature_key_id` describe how the signature should be interpreted.

The canonical signing payload is the canonical JSON form of the event excluding:

- `signature`
- `event_id`
- `state_hash`

This keeps the signed content stable while allowing transport metadata and post-application state commitments to be attached separately.

The payload may still include fields such as `signature_scheme` or `signature_key_id` when those fields are part of the verification model in use.

Known profiles and their required genesis metadata are listed in `protocol/satroot1.profile-registry.json`. Strict SATROOT-1 replay engines should treat that registry as the compatibility source of truth and reject unknown profiles until explicitly supported.

## 3. Boundary rule

A SATROOT-1 event MUST NOT claim that tokens are sub-satoshis.

Correct:

```text
1 root satoshi anchors 1,000,000,000 FLOOR1 units.
```

Incorrect:

```text
1 satoshi is divided into 1,000,000,000 smaller satoshis.
```

## 4. Recommended on-chain envelope

The minimal payload may be placed in an unspendable data output, while the root satoshi remains in a spendable 1-satoshi output.

Recommended envelope:

```text
OP_FALSE OP_RETURN "SATROOT1" <content-type> <payload-bytes>
```

Recommended content type:

```text
application/satroot1+json
```

For larger systems, the payload may be replaced by a content hash and an external availability pointer.

## 5. Genesis record

A genesis record defines the token universe.

Required fields:

```json
{
  "protocol": "SATROOT-1",
  "version": "0.1",
  "action": "genesis",
  "root_id": "<txid>:<vout>",
  "symbol": "FLOOR1",
  "name": "One Satoshi Floor Token",
  "decimals": 0,
  "max_supply": "1000000000",
  "mint_authority": "issuer_pubkey_or_script_hash",
  "transfer_model": "account-ledger",
  "initial_balances": {
    "issuer": "1000000000"
  },
  "rules_hash": "sha256:<hash>",
  "nonce": "<unique nonce>"
}
```

## 6. Event rules

### 6.1 Mint

A `mint` event increases semantic supply.

It is valid only if:

- signer matches mint authority,
- max supply is not exceeded,
- sequence is exactly previous sequence + 1.

### 6.2 Transfer

A `transfer` event moves semantic balance between accounts.

It is valid only if:

- sender has sufficient balance,
- amount is a positive integer string,
- signer controls sender account,
- sequence is valid.

### 6.3 Burn

A `burn` event reduces circulating semantic supply.

It is valid only if:

- burner has sufficient balance,
- amount is a positive integer string,
- signer controls burner account.

### 6.4 Rotate authority

A `rotate-authority` event changes the active mint authority for the root namespace.

It is valid only if:

- signer matches the current mint authority,
- `new_mint_authority` is a valid non-empty authority identifier,
- sequence is exactly previous sequence + 1.

This event changes control over future authority-gated actions such as `mint`. It does not move balances by itself and should not be confused with a token transfer.

### 6.5 Signature verification interface

The reference engine exposes a pluggable signature verifier interface:

```text
verifier(event, signing_payload) -> bool
```

The demo verifier accepts `signature="demo"` for test records. Production deployments should replace it with a verifier that checks a real signature scheme against the canonical signing payload.

The reference engine also includes a built-in `hmac-sha256` verifier constructor for controlled environments using shared secrets plus key identifiers. This is a concrete authenticated-event reference path, but it is not a public-key signature scheme.

An optional `ed25519` reference path is also exposed when the `cryptography` package is installed. This gives the reference engine a concrete public-key verification model without making the base package depend on extra crypto libraries by default.

The reference implementation also exposes helper functions and a small CLI for replaying ledgers plus signing single events or whole event arrays against those reference schemes.

CLI replay may be configured against the same reference verification models, so signed ledgers can be validated end to end without dropping into the Python API.

The reference implementation also exposes schema validation helpers and a CLI validation path so raw event JSON can be checked against `protocol/satroot1.schema.json` before replay.

It also exposes ledger-annotation helpers so deterministic `event_id` and `state_hash` commitments can be attached to an already valid ledger without changing the signed payload model.

For Ed25519 workflows, the reference implementation also exposes public-key derivation helpers so replay-ready verifier key maps can be produced from private-key maps without custom glue code.

It also exposes private-key generation helpers for reference and test workflows, allowing SATROOT-specific key maps to be bootstrapped directly from the CLI before deriving public verifier material.

For multi-signer ledgers, the reference implementation also exposes signer-map bootstrapping helpers so `signer -> key_id` mappings can be derived from event history before generating or assigning concrete verifier material.

For convenience workflows, those pieces can also be composed into a one-shot Ed25519 bootstrap path that emits signer maps plus private/public key material for a ledger without additional glue code.

The same pattern is exposed for controlled shared-secret deployments, where signer maps and HMAC verifier material can be bootstrapped directly from a ledger for reference and test workflows.

Those workflow pieces can also be composed into a one-shot signed-ledger bundle path, allowing a ledger plus verifier material and signed/annotated artifacts to be emitted together for reference or testing.

Signed bundle workflows may also emit a machine-readable manifest describing the chosen scheme, generated files, verifier-material scope, per-file hashes, record count, full final replay snapshot, and final committed SATROOT state hash so downstream tooling can inspect bundles without replaying them first.

For `ed25519` workflows, the reference CLI may emit either a `private-and-public` bundle for local workflow portability or a `public-only` verifier bundle that omits private keys while preserving end-to-end replay verification.

The reference implementation also exposes bundle-verification helpers so a signed bundle directory can be checked against its manifest and verifier material before any consumer accepts it.

The signed bundle manifest format is also described by its own JSON Schema so bundle producers and consumers can validate the exported metadata contract independently of replay.

When replay is unnecessary, the reference CLI may also expose manifest-only inspection helpers that summarize bundle metadata and the embedded final replay snapshot directly from `bundle_manifest.json`.

The reference engine currently recognizes these signature metadata rules:

- `demo`: `signature` must be `demo` and `signature_key_id` must be absent.
- `hmac-sha256`: `signature_key_id` is required and the signature must use the `hmac-sha256:` prefix.
- `ed25519`: `signature_key_id` is required and the signature must use the `ed25519:` prefix.

## 7. State commitment

Each event SHOULD include a `state_hash` after application:

```text
sha256(canonical_json({balances, supply, sequence, prev_event_id}))
```

This lets lightweight clients check that independent indexers agree on the same state.

An event MAY also carry an `event_id`. If present, it MUST equal the canonical event hash calculated from the record content excluding the `event_id` and `state_hash` fields. This avoids a circular dependency between event identity and post-application state commitment.

The reference implementation may expose richer replay snapshots for developer tooling, including preserved genesis/profile metadata, but the state commitment hash should remain derived from a stable deterministic subset of protocol state.

## 8. Minimal validity conditions

A SATROOT-1 indexer MUST reject a ledger if:

1. more than one genesis exists for the same root_id,
2. sequence numbers skip or repeat,
3. a transfer spends unavailable balance,
4. a mint exceeds max supply,
5. an event uses a different root_id,
6. an authority rotation is attempted by a non-authority signer,
7. a required signature check fails,
8. canonical JSON hashing does not match the stated event ID,
9. a stated `state_hash` does not match replayed state,
10. an unknown profile or invalid profile mode is used.

## 9. Claim discipline

SATROOT-1 can truthfully say:

- one satoshi anchors the token ledger,
- token units are protocol-defined semantic units,
- token supply can be arbitrarily large if the protocol permits it,
- balances are computed by replaying protocol events.

SATROOT-1 should not say:

- Bitcoin itself has been subdivided below one satoshi,
- semantic units are native Bitcoin units,
- the token has legal/economic rights unless separately documented,
- wallets or exchanges will recognize it without integration.

## 10. Stable-value boundary

Stable-value, fiat-reference, or stablecoin-like designs MUST be implemented as separate profiles. The SATROOT-1 base primitive does not create a stablecoin, redemption right, reserve claim, bank deposit, e-money token, or investment instrument.

A future `SATROOT-STABLE-1` profile may define reference-only accounting units such as `USDROOT1`, but the base protocol remains only a one-satoshi-root semantic ledger primitive.

## 11. Namespace expansion boundary

Future SATROOT work may define additional object classes under the same root model, but those profiles must not retroactively change the minimal meaning of `SATROOT-1`.

`SATROOT-1` remains:

- one root satoshi,
- one semantic token ledger,
- deterministic replay,
- strict boundaries around claims.

## 12. First demo token

Demo name: One Satoshi Floor Token
Symbol: FLOOR1
Root supply: 1,000,000,000 units
Root satoshi: one UTXO
Decimals: 0
Meaning: proof-of-concept semantic units anchored to one satoshi
