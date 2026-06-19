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

Known profiles and their required genesis metadata are listed in `protocol/satroot1.profile-registry.json`. Unknown profiles should be rejected by strict SATROOT-1 replay engines until explicitly supported.

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

## 7. State commitment

Each event SHOULD include a `state_hash` after application:

```text
sha256(canonical_json({balances, supply, sequence, prev_event_id}))
```

This lets lightweight clients check that independent indexers agree on the same state.

An event MAY also carry an `event_id`. If present, it MUST equal the canonical event hash calculated from the record content excluding the `event_id` and `state_hash` fields. This avoids a circular dependency between event identity and post-application state commitment.

## 8. Minimal validity conditions

A SATROOT-1 indexer MUST reject a ledger if:

1. more than one genesis exists for the same root_id,
2. sequence numbers skip or repeat,
3. a transfer spends unavailable balance,
4. a mint exceeds max supply,
5. an event uses a different root_id,
6. a required signature check fails,
7. canonical JSON hashing does not match the stated event ID,
8. a stated `state_hash` does not match replayed state,
9. an unknown profile or invalid profile mode is used.

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
