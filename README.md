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
- `protocol/satroot1.bundle-manifest.schema.json` - JSON schema for signed bundle manifests.
- `protocol/satroot1.bundle-index.schema.json` - JSON schema for bundle index catalogs.
- `protocol/satroot1.release-manifest.schema.json` - JSON schema for signed release manifests.
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
- runtime guardrails for stable reference-only profile metadata,
- runtime guardrails for machine and singleton-object profile metadata,
- a canonical signing payload model,
- a built-in `hmac-sha256` reference verifier path for shared-secret environments,
- an optional `ed25519` verifier path behind the `crypto` extra,
- explicit `signature_scheme` and `signature_key_id` protocol metadata,
- optional `event_id` and `state_hash` verification,
- reference helpers for signing a single event or a whole ledger,
- profile-aware genesis scaffolding for base and draft SATROOT profiles,
- event scaffolding for valid non-genesis SATROOT records from an existing ledger or explicit references,
- append-and-sign event workflows for extending existing demo or signed ledgers,
- profile-aware lifecycle helpers for common machine-credit consumption flows,
- profile-aware lifecycle helpers for singleton receipt, identity, and license transfer, archival, and retirement flows,
- a one-shot SATROOT-STABLE-1 reference-demo bootstrap for runnable stable-profile artifact generation,
- a one-shot SATROOT-STABLE-1 signed demo-bundle bootstrap for release-ready stable-profile artifacts,
- a one-shot SATROOT-STABLE-1 demo-release bootstrap for bundle plus release publication generation,
- a `satroot1` CLI entry point for replay and signing workflows,
- verifier-aware CLI replay for `demo`, `hmac-sha256`, and `ed25519` ledgers,
- schema-aware CLI validation for raw SATROOT-1 JSON files,
- commitment-aware CLI annotation for adding deterministic `event_id` and `state_hash` fields,
- signer-map bootstrapping helpers for deriving `signer -> key_id` mappings from ledgers,
- HMAC secret generation helpers for controlled shared-secret workflows,
- Ed25519 private-key generation helpers for bootstrapping SATROOT signing workflows,
- one-shot HMAC workflow bootstrapping for signer maps plus shared-secret material,
- Ed25519 key-derivation helpers for producing replay-ready public key maps from private key maps,
- one-shot Ed25519 workflow bootstrapping for signer maps plus private/public key material,
- one-shot signed-ledger bundle generation for HMAC and Ed25519 workflows,
- machine-readable signed bundle manifests describing artifacts, verifier-material scope, per-file hashes, and the full final replay snapshot,
- manifest-only bundle inspection via `bundle-summary` when replay is unnecessary,
- structural bundle linting via `bundle-lint` for missing files and manifest layout drift,
- deterministic bundle-index generation for release catalogs spanning multiple bundles,
- optional release metadata on bundle indexes for channel, label, and published-at packaging context,
- signed release-manifest generation for authenticating distributable bundle-index publications,
- release-key bootstrap helpers for HMAC and Ed25519 publication signing workflows,
- one-shot `publish-release` orchestration for ready-to-verify release directories,
- one-shot `bootstrap-genesis-bundle` scaffolding for signed starter bundles from profile-aware genesis defaults,
- one-shot `bootstrap-release-publication` orchestration for release material plus signed publication outputs,
- signed bundle verification against manifest and verifier material,
- bundle-manifest, bundle-index, and release-manifest schema validation for exported signed artifacts,
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
- `examples/events_usdroot1.json` for a runnable reference-only ledger flow,
- `satroot1 bootstrap-stable-demo` for generating new reference-only demo ledgers on demand,
- `satroot1 bootstrap-stable-demo-bundle` for generating signed stable demo bundles directly from profile parameters,
- `satroot1 bootstrap-stable-demo-release` for generating signed stable demo bundles plus release directories in one step.

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
156 passed
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

Build a signer-to-key map directly from a ledger:

```bash
satroot1 init-signer-key-map examples/events_floor1.json --output signer_keys.json
```

Scaffold a profile-aware genesis record with valid defaults:

```bash
satroot1 init-genesis --symbol USDCLI1 --name "SATROOT CLI Dollar" --profile SATROOT-STABLE-1 --profile-field reference_unit=EUR --profile-field intended_use=cli-reference-ledger --output genesis.json
```

Scaffold the next event directly from an existing ledger:

```bash
satroot1 init-event --action transfer --events-json examples/events_floor1.json --signer bob --from bob --to issuer --amount 1000 --output next_event.json
```

Append and sign the next event directly onto an existing ledger:

```bash
satroot1 append-event signed_events.json --action transfer --signer bob --from bob --to issuer --amount 1000 --scheme hmac-sha256 --signer-key-map-json signer_key_map.json --secrets-json secrets.json --include-state-hash --output appended_events.json
```

Generate a runnable SATROOT-STABLE-1 reference-only demo ledger:

```bash
satroot1 bootstrap-stable-demo --symbol USDCLI2 --name "Stable CLI Demo" --reference-unit EUR --output-dir stable_demo
```

Generate a signed SATROOT-STABLE-1 reference-only demo bundle:

```bash
satroot1 bootstrap-stable-demo-bundle --symbol USDBUNDLE2 --name "Stable Bundle CLI" --scheme hmac-sha256 --reference-unit CHF --output-dir stable_bundle
```

Generate a signed SATROOT-STABLE-1 demo bundle plus release directory:

```bash
satroot1 bootstrap-stable-demo-release --symbol USDRELCLI1 --name "Stable Release CLI" --scheme hmac-sha256 --release-key-id release-key --reference-unit JPY --channel stable --label "SATROOT Stable Release" --published-at 2026-06-27T12:00:00Z --output-dir stable_release
```

Consume burn-on-use machine credit from a `SATROOT-MACHINE-1` ledger:

```bash
satroot1 consume-machine-credit signed_machine_events.json --signer worker_node --amount 1000 --scheme hmac-sha256 --signer-key-map-json signer_key_map.json --secrets-json secrets.json --include-state-hash --output consumed_machine_events.json
```

Archive a singleton receipt, identity, or license object into an archive account:

```bash
satroot1 archive-singleton-object signed_receipt_events.json --signer buyer --scheme hmac-sha256 --signer-key-map-json signer_key_map.json --secrets-json secrets.json --include-state-hash --output archived_receipt_events.json
```

Transfer a singleton receipt, identity, or license object to its next active holder:

```bash
satroot1 transfer-singleton-object signed_identity_events.json --signer node_alpha --to rotated_controller --scheme hmac-sha256 --signer-key-map-json signer_key_map.json --secrets-json secrets.json --include-state-hash --output transferred_identity_events.json
```

Retire an already archived singleton receipt, identity, or license object:

```bash
satroot1 retire-singleton-object archived_receipt_events.json --signer archive --scheme hmac-sha256 --signer-key-map-json signer_key_map.json --secrets-json secrets.json --include-state-hash --output retired_receipt_events.json
```

Scaffold a genesis record and emit a signed starter bundle in one step:

```bash
satroot1 bootstrap-genesis-bundle --symbol BUNDLE1 --name "SATROOT Bundle Asset" --scheme hmac-sha256 --profile SATROOT-MACHINE-1 --output-dir starter_bundle
```

Bootstrap the full Ed25519 workflow from a ledger in one step:

```bash
satroot1 bootstrap-ed25519-workflow examples/events_floor1.json --output-dir ed25519_bootstrap
```

Bootstrap the full HMAC workflow from a ledger in one step:

```bash
satroot1 bootstrap-hmac-workflow examples/events_floor1.json --output-dir hmac_bootstrap
```

Bootstrap and emit a full signed HMAC ledger bundle in one step:

```bash
satroot1 bootstrap-signed-ledger examples/events_floor1.json --scheme hmac-sha256 --output-dir signed_hmac_bundle
```

That bundle now includes `bundle_manifest.json` alongside the emitted signer/key material and ledger files, with per-file SHA-256 hashes for the exported artifacts and the full final SATROOT replay snapshot for downstream inspection.

For Ed25519 workflows, you can also emit a verifier-only bundle that excludes `private_keys.json` and records `verification_material_scope="public-only"` in the manifest:

```bash
satroot1 bootstrap-signed-ledger examples/events_floor1.json --scheme ed25519 --output-dir signed_ed25519_bundle --verifier-only
```

Verify a signed bundle directory end to end:

```bash
satroot1 verify-bundle signed_hmac_bundle
```

Read a bundle manifest summary without replaying the ledger:

```bash
satroot1 bundle-summary signed_hmac_bundle
```

Lint bundle structure without replaying the ledger:

```bash
satroot1 bundle-lint signed_hmac_bundle
```

Build a bundle index catalog from one or more bundle directories:

```bash
satroot1 build-bundle-index signed_hmac_bundle --output bundle_index.json
```

Attach lightweight release metadata to a bundle index:

```bash
satroot1 build-bundle-index signed_hmac_bundle --channel stable --label "SATROOT FLOOR1 Demo" --published-at 2026-06-22T12:00:00Z --output bundle_index.json
```

Build a signed release manifest from a bundle index:

```bash
satroot1 build-release-manifest bundle_index.json --scheme hmac-sha256 --key-id release-key --secret release-secret --output release_manifest.json
```

Bootstrap reusable HMAC release-signing material:

```bash
satroot1 bootstrap-release-hmac --key-id release-key --output-dir release_hmac
```

Build a release manifest from generated HMAC release material:

```bash
satroot1 build-release-manifest bundle_index.json --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json --output release_manifest.json
```

Publish a release directory with both `bundle_index.json` and `release_manifest.json` in one step:

```bash
satroot1 publish-release signed_hmac_bundle --output-dir stable_release --channel stable --label "SATROOT FLOOR1 Demo" --published-at 2026-06-26T12:00:00Z --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

Bootstrap release signing material and publish a ready-to-verify release directory in one step:

```bash
satroot1 bootstrap-release-publication starter_bundle --output-dir release_bootstrap --channel stable --label "SATROOT Starter Release" --published-at 2026-06-26T12:00:00Z --scheme hmac-sha256 --key-id release-key
```

Validate a bundle manifest directly against the SATROOT manifest schema:

```bash
satroot1 validate-bundle-manifest signed_hmac_bundle/bundle_manifest.json
```

Validate a bundle index directly against the SATROOT bundle-index schema:

```bash
satroot1 validate-bundle-index bundle_index.json
```

Validate a signed release manifest directly against the SATROOT release-manifest schema:

```bash
satroot1 validate-release-manifest release_manifest.json
```

Verify a signed release manifest against its bundle index:

```bash
satroot1 verify-release-manifest release_manifest.json --secrets-json release_secrets.json
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

Generate HMAC shared secrets for SATROOT key IDs:

```bash
satroot1 generate-hmac-secrets --key-id issuer-key --key-id alice-key --output secrets.json
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
