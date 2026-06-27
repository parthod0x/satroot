# Changelog

## Unreleased

- Hardens the SATROOT-1 replay engine with root ID, profile, and account-name validation.
- Adds optional `event_id` and `state_hash` verification during replay.
- Adds an explicit profile compatibility registry in `protocol/satroot1.profile-registry.json`.
- Makes the replay engine load supported profile rules from the registry instead of a hardcoded table.
- Enforces stable reference-only profile guardrails plus non-empty profile metadata fields during replay.
- Enforces compact machine/object profile metadata and singleton object-supply guardrails during replay.
- Adds profile-aware genesis scaffolding helpers and an `init-genesis` CLI command.
- Adds a one-shot `bootstrap-genesis-bundle` workflow for scaffolded signed starter bundles.
- Adds a one-shot `bootstrap-release-publication` workflow for release signing material plus published release directories.
- Adds event scaffolding helpers and an `init-event` CLI command for non-genesis records.
- Adds an `append-event` CLI workflow plus helper for extending existing ledgers with signed events.
- Adds a `consume-machine-credit` lifecycle helper for burn-on-use `SATROOT-MACHINE-1` ledgers.
- Adds an `archive-singleton-object` lifecycle helper for receipt, identity, and license ledgers.
- Adds a canonical signing payload function and a pluggable signature verifier interface.
- Adds a concrete built-in `hmac-sha256` reference verifier for shared-secret event authentication.
- Adds optional `ed25519` signing and verification helpers behind the `crypto` extra.
- Formalizes `signature_scheme` and `signature_key_id` in the schema and engine validation rules.
- Adds signing helpers for single events and full ledgers in the reference implementation.
- Exposes a `satroot1` CLI entry point for replay, `sign-event`, and `sign-ledger` workflows.
- Preserves genesis/profile metadata in replay snapshots while keeping state-hash commitments stable.
- Adds first-class `rotate-authority` events for explicit mint-authority handoff.
- Extends CLI replay so HMAC- and Ed25519-signed ledgers can be verified from the command line.
- Adds `satroot1 validate` plus optional `validation` extras for JSON Schema checks against SATROOT-1 records.
- Adds `annotate-ledger` helpers and CLI support for deterministic `event_id` and `state_hash` attachment.
- Adds Ed25519 public-key derivation helpers and CLI support for producing verifier key maps from private key maps.
- Adds Ed25519 private-key generation helpers and CLI support for bootstrapping SATROOT signer key maps.
- Adds signer-map derivation helpers and CLI support for extracting `signer -> key_id` mappings from ledgers.
- Adds a one-shot Ed25519 workflow bootstrap command that emits signer maps plus private/public key material from a ledger.
- Adds HMAC shared-secret generation helpers and a one-shot HMAC workflow bootstrap command for controlled environments.
- Adds a one-shot signed-ledger bundle command for HMAC and Ed25519 workflows.
- Adds signed bundle manifests describing emitted files and final committed state.
- Adds signed bundle verification helpers and CLI support.
- Adds a dedicated signed bundle manifest schema plus CLI validation support, including per-file bundle hashes.
- Extends signed bundle manifests with full final replay snapshots and verifies them during bundle validation.
- Adds verifier-only Ed25519 bundle export with explicit manifest scope metadata.
- Adds a manifest-only `bundle-summary` CLI path for fast bundle inspection without replay.
- Adds a non-replay `bundle-lint` CLI path for structural bundle checks and layout drift detection.
- Adds deterministic bundle-index exports plus bundle-index schema validation support.
- Extends bundle indexes with optional release metadata for channel, label, and published-at packaging context.
- Adds signed release-manifest exports plus release-manifest verification and schema validation support.
- Adds release-key bootstrap helpers plus file-based release-manifest signing inputs.
- Adds a one-shot `publish-release` workflow for writing bundle indexes plus signed release manifests together.
- Adds the first `SATROOT-STABLE-1` reference-only profile draft.
- Adds `USDROOT1` stable-value example genesis and event ledgers.
- Adds the first `SATROOT-MACHINE-1` prepaid-credit profile draft.
- Adds `APICREDIT1` machine-credit example genesis and event ledgers.
- Adds the first `SATROOT-RECEIPT-1` single-receipt profile draft.
- Adds `RECEIPT1` receipt-object example genesis and event ledgers.
- Adds the first `SATROOT-IDENTITY-1` single-identity profile draft.
- Adds `IDENTITY1` identity-object example genesis and event ledgers.
- Adds the first `SATROOT-LICENSE-1` single-license profile draft.
- Adds `LICENSE1` license-object example genesis and event ledgers.
- Extends the schema to describe optional stable-profile metadata.
- Generalizes profile metadata so non-stable profiles can define their own modes.
- Adds replay tests for the `USDROOT1`, `APICREDIT1`, `RECEIPT1`, `IDENTITY1`, and `LICENSE1` demo ledgers plus new validation, registry, and signature-verifier checks.

## v0.1.0 - 2026-06-19

Genesis draft of SATROOT-1.

- Defines one native satoshi UTXO as a root witness, authority handle, and namespace anchor.
- Defines semantic supply above the root satoshi without subdividing the satoshi.
- Frames SATROOT-1 as the base kernel of the broader SATROOT project.
- Adds FLOOR1 demo token with 1,000,000,000 semantic units.
- Adds JSON schema, Python replay engine, examples, and tests.
- Explicitly excludes stablecoin, security token, exchange-listing, or legal-rights claims from the base protocol.
