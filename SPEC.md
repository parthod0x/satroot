# SATROOT-1 Specification

Status: v1 draft freeze candidate
Date: 2026-08-19
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

In `SATROOT-1`, that namespace is used only for a token ledger. Released profiles already use the same root structure for receipts, credits, licenses, identities, and machine-readable rights.

### 2.5 Event ledger

Token balances are computed by replaying signed SATROOT-1 events:

- `genesis`
- `mint`
- `transfer`
- `burn`
- `rotate-authority`
- `freeze`
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

When a profile draft defines explicit safe-mode guardrails, replay engines may also enforce those genesis metadata constraints directly. For example, a `SATROOT-STABLE-1` `reference-only` genesis may require `redemption=none` and `reserve_model=none` so the ledger cannot accidentally claim redeemability or reserves while still presenting itself as reference-only.

Likewise, machine and single-object profiles may enforce compact identifier formatting for fields such as `service_scope`, `document_type`, `identity_type`, `license_type`, and related usage metadata, while `single-receipt`, `single-identity`, and `single-license` modes may require a zero-decimal, one-unit genesis so the ledger unambiguously anchors one object.

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

A deterministic offline builder and an offline raw-transaction verifier for this envelope are released with the reference implementation; one broadcast envelope carrying a real anchored-namespace state commitment is recorded in `ANCHORS.md`.

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

### 6.5 Freeze / unfreeze account

A `freeze` event changes whether a named account is balance-locked.

It is valid only if:

- signer matches the current mint authority,
- `account` is a valid non-empty account identifier,
- `frozen` is a boolean,
- sequence is exactly previous sequence + 1.

When an account is frozen, balance-affecting lifecycle actions must reject that account as a sender, burner, mint recipient, or transfer recipient until a later `freeze` event sets `frozen=false` for the same account.

This event changes account transferability state. It does not mint, burn, or transfer balances by itself.

### 6.6 Signature verification interface

The reference engine exposes a pluggable signature verifier interface:

```text
verifier(event, signing_payload) -> bool
```

The demo verifier accepts `signature="demo"` for test records. Production deployments should replace it with one of the shipped real schemes (`hmac-sha256`, `ed25519`) or an equivalent verifier over the canonical signing payload.

The reference engine also includes a built-in `hmac-sha256` verifier constructor for controlled environments using shared secrets plus key identifiers. This is a concrete authenticated-event reference path, but it is not a public-key signature scheme.

An `ed25519` path is available when the `cryptography` package is installed; it is the public-key scheme used end to end by the released anchored lanes, without making the base package depend on extra crypto libraries by default.

The reference implementation also exposes helper functions and a small CLI for replaying ledgers plus signing single events or whole event arrays against those reference schemes.

CLI replay may be configured against the same reference verification models, so signed ledgers can be validated end to end without dropping into the Python API.

The reference implementation also exposes schema validation helpers and a CLI validation path so raw event JSON can be checked against `protocol/satroot1.schema.json` before replay.

It also exposes ledger-annotation helpers so deterministic `event_id` and `state_hash` commitments can be attached to an already valid ledger without changing the signed payload model.

For Ed25519 workflows, the reference implementation also exposes public-key derivation helpers so replay-ready verifier key maps can be produced from private-key maps without custom glue code.

It also exposes private-key generation helpers for reference and test workflows, allowing SATROOT-specific key maps to be bootstrapped directly from the CLI before deriving public verifier material.

For multi-signer ledgers, the reference implementation also exposes signer-map bootstrapping helpers so `signer -> key_id` mappings can be derived from event history before generating or assigning concrete verifier material.

For convenience workflows, those pieces can also be composed into a one-shot Ed25519 bootstrap path that emits signer maps plus private/public key material for a ledger without additional glue code.

The same pattern is exposed for controlled shared-secret deployments, where signer maps and HMAC verifier material can be bootstrapped directly from a ledger for reference and test workflows.

The reference CLI may also expose profile-aware genesis scaffolding so valid base or profiled `genesis` objects can be emitted with safe defaults before downstream replay, signing, or bundling steps.

The reference CLI may also expose event scaffolding helpers so valid non-genesis `mint`, `transfer`, `burn`, `freeze`, or `rotate-authority` records can be derived from an existing ledger tip or from explicit `root_id`, `sequence`, and `prev_event_id` inputs.

Those helpers may also be composed into append workflows so an existing ledger can be replayed, a next event scaffolded or supplied, and that new event signed and appended in one step without manual JSON surgery.

For profile-specific ergonomics, the reference CLI may also expose lifecycle helpers that map draft profile semantics to ordinary SATROOT events. For example, a `SATROOT-MACHINE-1` ledger with `consumption_model=burn-on-use` may support a helper that appends the corresponding `burn` event without forcing the operator to restate the generic lifecycle mapping each time.

Likewise, singleton receipt, identity, or license profiles may support transfer helpers that detect the current active holder and append the corresponding one-unit reassignment without restating the generic SATROOT event details each time. Those same profiles may also support archival helpers that move the active unit into an archive account and retirement helpers that burn an already archived singleton object once the archived holder is ready to retire it.

The reference CLI may also expose singleton demo bootstrap paths that scaffold runnable receipt, identity, or license lifecycle ledgers from profile-aware defaults so object-style SATROOT workflows can be generated without hand-authoring each lifecycle record.

Those singleton demo paths may also be composed directly into signed bundle workflows so object-style profiles can emit verifier material, annotated replay artifacts, and bundle manifests without a separately prepared intermediate ledger file.

Those singleton bundle workflows may also be composed one step further into release bootstraps so receipt, identity, or license profile artifacts can emit both signed bundles and signed release directories through the same bundle-index and release-manifest verification path used elsewhere in SATROOT.

For reference-only stable ledgers, the reference CLI may also expose a demo bootstrap path that scaffolds a runnable `SATROOT-STABLE-1` issuance, distribution, and optional burn flow into reusable JSON artifacts without introducing redemption or reserve semantics.

That same stable bootstrap may also be composed directly into a signed bundle path so a reference-only stable ledger can be emitted together with signer material, annotated replay artifacts, and a verifiable bundle manifest without requiring a separate handwritten intermediate ledger file.

That signed stable bundle path may also be composed one step further into a release bootstrap that writes both the stable bundle and a signed release directory together, preserving the reference-only stable semantics while exposing the same bundle-index and release-manifest verification flow used elsewhere in SATROOT.

That scaffolding may also be composed into a one-shot starter-bundle workflow that emits a scaffolded `genesis.json`, a one-record signed ledger bundle, and verifier material in a single directory for reference or testing.

Those workflow pieces can also be composed into a one-shot signed-ledger bundle path, allowing a ledger plus verifier material and signed/annotated artifacts to be emitted together for reference or testing.

Signed bundle workflows may also emit a machine-readable manifest describing the chosen scheme, generated files, verifier-material scope, per-file hashes, record count, full final replay snapshot, and final committed SATROOT state hash so downstream tooling can inspect bundles without replaying them first.

For release distribution workflows, the reference CLI may also expose a publication bootstrap helper that generates release signing material and writes `bundle_index.json` plus `release_manifest.json` into a ready-to-verify release directory in one step.

For `ed25519` workflows, the reference CLI may emit either a `private-and-public` bundle for local workflow portability or a `public-only` verifier bundle that omits private keys while preserving end-to-end replay verification.

The reference implementation also exposes bundle-verification helpers so a signed bundle directory can be checked against its manifest and verifier material before any consumer accepts it.

The signed bundle manifest format is also described by its own JSON Schema so bundle producers and consumers can validate the exported metadata contract independently of replay.

When replay is unnecessary, the reference CLI may also expose manifest-only inspection helpers that summarize bundle metadata and the embedded final replay snapshot directly from `bundle_manifest.json`.

The reference CLI may also expose non-replay lint helpers that check declared bundle files, hash coverage, and directory-layout drift before a consumer decides whether full cryptographic replay verification is worth running.

For multi-bundle releases, the reference implementation may also emit deterministic bundle-index catalogs that point at one or more `bundle_manifest.json` artifacts, record each manifest hash, and summarize the final committed state for downstream release tooling.

Those bundle indexes may also carry optional release metadata such as channel, human label, and published-at timestamp so the same artifact can serve as a lightweight SATROOT distribution manifest.

For authenticated publication workflows, the reference implementation may also emit a signed release manifest that binds a `bundle_index.json` path and hash to explicit release-signature metadata, allowing downstream consumers to verify the publication artifact separately from bundle replay itself.

The reference CLI may also expose release-key bootstrap helpers so publication signing material can be generated and reused as files rather than injected only through one-off inline secret or private-key parameters.

The reference CLI may also expose a one-shot publication helper that writes `bundle_index.json` and `release_manifest.json` together into a release directory while preserving relative bundle paths for downstream verification.

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
- balances are computed by replaying protocol events,
- one real one-satoshi testnet outpoint has been bound as a namespace `root_id` with an ed25519-verified lifecycle,
- a section 4 state commitment for that namespace has been broadcast on-chain and re-verified offline from raw transaction bytes.

SATROOT-1 should not say:

- Bitcoin itself has been subdivided below one satoshi,
- semantic units are native Bitcoin units,
- the token has legal/economic rights unless separately documented,
- wallets or exchanges will recognize it without integration.

## 10. Stable-value boundary

Stable-value, fiat-reference, or stablecoin-like designs MUST be implemented as separate profiles. The SATROOT-1 base primitive does not create a stablecoin, redemption right, reserve claim, bank deposit, e-money token, or investment instrument.

The released `SATROOT-STABLE-1` profile defines reference-only accounting units such as `USDROOT1`, but the base protocol remains only a one-satoshi-root semantic ledger primitive.

## 11. Namespace expansion boundary

Further SATROOT work may define additional object classes beyond the five released profiles under the same root model, but those profiles must not retroactively change the minimal meaning of `SATROOT-1`.

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
