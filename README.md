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
- `protocol/satroot1.release-catalog.schema.json` - JSON schema for multi-release catalogs.
- `protocol/satroot1.release-catalog-manifest.schema.json` - JSON schema for signed multi-release catalog manifests.
- `protocol/satroot1.release-catalog-index.schema.json` - JSON schema for multi-catalog release index exports.
- `protocol/satroot1.release-catalog-index-manifest.schema.json` - JSON schema for signed multi-catalog release index manifests.
- `protocol/satroot1.demo-catalog-summary.schema.json` - JSON schema for demo catalog workspace summaries.
- `protocol/satroot1.publication-stack-summary.schema.json` - JSON schema for publication-stack workspace summaries.
- `protocol/satroot1.publication-network-summary.schema.json` - JSON schema for publication-network workspace summaries.
- `protocol/satroot1.profile-registry.json` - explicit compatibility registry for supported profiles.
- `src/satroot1.py` - reference parser, deterministic replay engine, and signing utility CLI.
- `examples/` - the `FLOOR1` demo token ledger.
- `examples/catalog_presets/` - reusable SATROOT demo catalog scenario presets.
- `examples/release_catalog_presets/` - reusable SATROOT release-catalog publication presets.
- `examples/release_catalog_index_presets/` - reusable SATROOT release-catalog-index publication presets.
- `examples/network_presets/` - reusable SATROOT publication-network presets.
- `examples/stack_presets/` - reusable SATROOT end-to-end publication-stack presets.
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
- a one-shot SATROOT-MACHINE-1 machine-credit demo bootstrap for runnable machine-profile artifact generation,
- a one-shot SATROOT-MACHINE-1 signed demo-bundle bootstrap for release-ready machine-profile artifacts,
- a one-shot SATROOT-MACHINE-1 demo-release bootstrap for bundle plus release publication generation,
- profile-aware lifecycle helpers for singleton receipt, identity, and license transfer, archival, and retirement flows,
- a one-shot singleton receipt/identity/license demo bootstrap for runnable object-profile lifecycle artifacts,
- a one-shot singleton receipt/identity/license signed demo-bundle bootstrap for verifiable object-profile artifacts,
- a one-shot singleton receipt/identity/license demo-release bootstrap for bundle plus release publication generation,
- a one-shot SATROOT-STABLE-1 reference-demo bootstrap for runnable stable-profile artifact generation,
- a one-shot SATROOT-STABLE-1 signed demo-bundle bootstrap for release-ready stable-profile artifacts,
- a one-shot SATROOT-STABLE-1 demo-release bootstrap for bundle plus release publication generation,
- a one-shot multi-profile demo catalog workspace bootstrap for bundles plus signed catalog release generation,
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
- release-level inspection via `release-summary` when signature verification is unnecessary,
- structural release linting via `release-lint` for bundle-index and manifest drift,
- deterministic bundle-index generation for release catalogs spanning multiple bundles,
- discovery-based bundle catalog packaging from parent artifact directories,
- optional release metadata on bundle indexes for channel, label, and published-at packaging context,
- signed release-manifest generation for authenticating distributable bundle-index publications,
- release-key bootstrap helpers for HMAC and Ed25519 publication signing workflows,
- one-shot `publish-release` orchestration for ready-to-verify release directories,
- deterministic release-catalog generation for aggregating multiple signed release publications,
- catalog-level inspection via `release-catalog-summary` when signature verification is unnecessary,
- structural release-catalog linting via `release-catalog-lint` for catalog and nested release drift,
- signed release-catalog-manifest generation for authenticating multi-release catalogs,
- one-shot `publish-release-catalog` orchestration for ready-to-verify release-catalog directories,
- deterministic release-catalog-index generation for aggregating multiple signed release-catalog publications,
- index-level inspection via `release-catalog-index-summary` when signature verification is unnecessary,
- structural release-catalog-index linting via `release-catalog-index-lint` for index and nested catalog drift,
- signed release-catalog-index-manifest generation for authenticating multi-catalog release indexes,
- one-shot `publish-release-catalog-index` orchestration for ready-to-verify release-catalog-index directories,
- one-shot `bootstrap-genesis-bundle` scaffolding for signed starter bundles from profile-aware genesis defaults,
- one-shot `bootstrap-release-publication` orchestration for release material plus signed publication outputs,
- one-shot `bootstrap-release-catalog-publication` orchestration for release-catalog material plus signed publication outputs,
- one-shot `bootstrap-release-catalog-index-publication` orchestration for release-catalog-index material plus signed publication outputs,
- demo-catalog inspection via `demo-catalog-summary` and structural linting via `demo-catalog-lint`,
- one-shot `bootstrap-publication-stack` orchestration for preset-driven bundles, releases, and release-catalog outputs in one workspace,
- `publish-publication-stack` for consolidating existing demo catalog workspaces into one signed release-catalog stack,
- publication-stack inspection via `publication-stack-summary` and structural linting via `publication-stack-lint`,
- one-shot `bootstrap-publication-network` orchestration for preset-driven stacks plus a top-level release-catalog-index output in one workspace,
- `publish-publication-network` for consolidating existing publication stack workspaces into one signed release-catalog-index network,
- publication-network inspection via `publication-network-summary` and structural linting via `publication-network-lint`,
- `inventory-artifacts` for scanning a directory tree and summarizing discovered SATROOT artifacts across bundle, release, catalog, index, and workspace layers,
- preset export commands for deriving reusable demo-catalog, publication-stack, and publication-network presets back from generated workspaces,
- `render-publication-report` for turning detected SATROOT artifacts or workspaces into human-readable markdown reports,
- `export-publication-descriptor` for emitting normalized JSON descriptors from detected SATROOT artifacts or workspaces,
- demo-catalog, publication-stack, and publication-network summary schema validation for exported workspace summaries,
- signed bundle verification against manifest and verifier material,
- bundle-manifest, bundle-index, release-manifest, release-catalog, release-catalog-manifest, release-catalog-index, release-catalog-index-manifest, demo-catalog-summary, publication-stack-summary, and publication-network-summary schema validation for exported signed artifacts,
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
- `examples/events_apicredit1.json` for a runnable machine-credit ledger flow,
- `satroot1 bootstrap-machine-demo` for generating new machine-credit demo ledgers on demand,
- `satroot1 bootstrap-machine-demo-bundle` for generating signed machine-credit demo bundles directly from profile parameters,
- `satroot1 bootstrap-machine-demo-release` for generating signed machine-credit demo bundles plus release directories in one step.

This repo also now includes the first receipt-object profile draft:

- `SATROOT-RECEIPT-1` for invoice and receipt state objects,
- `examples/genesis_receipt1.json` for a `RECEIPT1` genesis record,
- `examples/events_receipt1.json` for a runnable receipt lifecycle ledger flow,
- `satroot1 bootstrap-singleton-demo --profile SATROOT-RECEIPT-1` for generating new receipt/identity/license singleton demo ledgers on demand,
- `satroot1 bootstrap-singleton-demo-bundle --profile SATROOT-RECEIPT-1` for generating signed receipt/identity/license demo bundles on demand,
- `satroot1 bootstrap-singleton-demo-release --profile SATROOT-RECEIPT-1` for generating signed receipt/identity/license demo bundles plus release directories in one step.

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
241 passed
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

Generate a runnable SATROOT-MACHINE-1 machine-credit demo ledger:

```bash
satroot1 bootstrap-machine-demo --symbol APIDEMO2 --name "Machine CLI Demo" --service-scope inference-api --billing-unit token --output-dir machine_demo
```

Generate a runnable receipt, identity, or license singleton demo ledger:

```bash
satroot1 bootstrap-singleton-demo --profile SATROOT-IDENTITY-1 --symbol IDDEMO2 --name "Identity CLI Demo" --next-holder controller_v2 --no-archive --no-retire --output-dir singleton_identity
```

Generate a signed receipt, identity, or license singleton demo bundle:

```bash
satroot1 bootstrap-singleton-demo-bundle --profile SATROOT-RECEIPT-1 --symbol RECBUNDLE2 --name "Receipt Bundle CLI" --scheme hmac-sha256 --output-dir singleton_bundle
```

Generate a signed receipt, identity, or license singleton demo bundle plus release directory:

```bash
satroot1 bootstrap-singleton-demo-release --profile SATROOT-LICENSE-1 --symbol LICRELCLI1 --name "License Release CLI" --scheme hmac-sha256 --release-key-id release-key --channel stable --label "SATROOT License Release" --published-at 2026-06-28T12:00:00Z --output-dir singleton_release
```

Generate a signed SATROOT-STABLE-1 reference-only demo bundle:

```bash
satroot1 bootstrap-stable-demo-bundle --symbol USDBUNDLE2 --name "Stable Bundle CLI" --scheme hmac-sha256 --reference-unit CHF --output-dir stable_bundle
```

For Ed25519 stable bundles, you can also emit a verifier-only variant that excludes `private_keys.json`:

```bash
satroot1 bootstrap-stable-demo-bundle --symbol USDEDCLI1 --name "Stable Bundle Ed25519" --scheme ed25519 --reference-unit AUD --output-dir stable_bundle_ed25519 --verifier-only
```

Generate a signed SATROOT-STABLE-1 demo bundle plus release directory:

```bash
satroot1 bootstrap-stable-demo-release --symbol USDRELCLI1 --name "Stable Release CLI" --scheme hmac-sha256 --release-key-id release-key --reference-unit JPY --channel stable --label "SATROOT Stable Release" --published-at 2026-06-27T12:00:00Z --output-dir stable_release
```

Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle:

```bash
satroot1 bootstrap-machine-demo-bundle --symbol APIBUNDLE2 --name "Machine Bundle CLI" --scheme hmac-sha256 --service-scope batch-jobs --output-dir machine_bundle
```

Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle plus release directory:

```bash
satroot1 bootstrap-machine-demo-release --symbol APIRELCLI1 --name "Machine Release CLI" --scheme hmac-sha256 --release-key-id release-key --service-scope render-farm --channel stable --label "SATROOT Machine Release" --published-at 2026-06-28T06:00:00Z --output-dir machine_release
```

Generate a full multi-profile demo catalog workspace with `bundles/`, `release/`, and a root `summary.json` in one step:

```bash
satroot1 bootstrap-demo-catalog --scheme hmac-sha256 --release-key-id release-key --output-dir catalog_workspace --channel stable --label "SATROOT Demo Catalog" --published-at 2026-06-28T22:00:00Z
```

That workspace bootstrap can also be narrowed to selected profiles with per-profile symbol and name overrides:

```bash
satroot1 bootstrap-demo-catalog --scheme hmac-sha256 --release-key-id release-key --output-dir catalog_workspace_subset --profile SATROOT-MACHINE-1 --profile SATROOT-IDENTITY-1 --symbol-override SATROOT-MACHINE-1=APISET2 --name-override "SATROOT-IDENTITY-1=SATROOT Identity Subset" --channel stable --label "SATROOT Subset Catalog" --published-at 2026-06-28T22:30:00Z
```

Per-profile metadata can also be overridden inside the catalog bootstrap with `PROFILE:field=value` entries:

```bash
satroot1 bootstrap-demo-catalog --scheme hmac-sha256 --release-key-id release-key --output-dir catalog_workspace_fields --profile SATROOT-STABLE-1 --profile SATROOT-MACHINE-1 --profile-field-override SATROOT-STABLE-1:reference_unit=EUR --profile-field-override SATROOT-STABLE-1:intended_use=treasury-ledger --profile-field-override SATROOT-MACHINE-1:service_scope=batch-inference --profile-field-override SATROOT-MACHINE-1:billing_unit=job --profile-field-override SATROOT-MACHINE-1:intended_use=compute-credit --channel stable --label "SATROOT Field Override Catalog" --published-at 2026-06-28T23:00:00Z
```

Per-profile structural demo parameters can be overridden too, so the catalog can generate different ledger shapes and singleton lifecycles from one command:

```bash
satroot1 bootstrap-demo-catalog --scheme hmac-sha256 --release-key-id release-key --output-dir catalog_workspace_structure --profile SATROOT-STABLE-1 --profile SATROOT-MACHINE-1 --profile SATROOT-IDENTITY-1 --profile-structure-override SATROOT-STABLE-1:merchant_account=merchant_beta --profile-structure-override SATROOT-STABLE-1:service_account=settlement_node --profile-structure-override SATROOT-STABLE-1:merchant_burn_amount=0 --profile-structure-override SATROOT-MACHINE-1:tenant_account=tenant_b --profile-structure-override SATROOT-MACHINE-1:worker_account=worker_beta --profile-structure-override SATROOT-MACHINE-1:worker_burn_amount=0 --profile-structure-override SATROOT-IDENTITY-1:holder_account=controller_a --profile-structure-override SATROOT-IDENTITY-1:next_holder=none --profile-structure-override SATROOT-IDENTITY-1:retire=false --channel stable --label "SATROOT Structure Override Catalog" --published-at 2026-06-29T00:00:00Z
```

For repeatable scenario generation, `bootstrap-demo-catalog` can also load a checked-in preset file and still accept CLI overrides on top:

```bash
satroot1 bootstrap-demo-catalog --scheme hmac-sha256 --release-key-id release-key --output-dir catalog_workspace_preset --preset-json examples/catalog_presets/ai_compute_catalog.json --label "SATROOT AI Compute Catalog Override"
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

Read a release publication summary without signature verification:

```bash
satroot1 release-summary stable_release
```

Lint release structure and referenced bundle manifests without signature verification:

```bash
satroot1 release-lint stable_release
```

Build a bundle index catalog from one or more bundle directories:

```bash
satroot1 build-bundle-index signed_hmac_bundle --output bundle_index.json
```

Or discover bundle directories recursively under a parent artifacts folder:

```bash
satroot1 build-bundle-index --discover-under generated_artifacts --output bundle_index.json
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

That same release flow can also discover multiple bundle directories under a parent workspace:

```bash
satroot1 publish-release --discover-under generated_artifacts --output-dir catalog_release --channel stable --label "SATROOT Multi Bundle Demo" --published-at 2026-06-28T18:00:00Z --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

Bootstrap release signing material and publish a ready-to-verify release directory in one step:

```bash
satroot1 bootstrap-release-publication starter_bundle --output-dir release_bootstrap --channel stable --label "SATROOT Starter Release" --published-at 2026-06-26T12:00:00Z --scheme hmac-sha256 --key-id release-key
```

For catalog-style packaging, you can point that bootstrap flow at a parent directory and let it discover nested bundles automatically:

```bash
satroot1 bootstrap-release-publication --discover-under generated_artifacts --output-dir catalog_bootstrap --channel stable --label "SATROOT Catalog Release" --published-at 2026-06-28T19:00:00Z --scheme hmac-sha256 --key-id release-key
```

Build a higher-level release catalog from multiple signed release directories:

```bash
satroot1 build-release-catalog stable_release machine_release --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --output release_catalog.json
```

Publish a signed release catalog directory in one step:

```bash
satroot1 publish-release-catalog stable_release machine_release --output-dir release_catalog_pub --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --scheme hmac-sha256 --key-id catalog-key --secrets-json release_hmac/release_secrets.json
```

Or bootstrap fresh signing material for that release catalog publication:

```bash
satroot1 bootstrap-release-catalog-publication stable_release machine_release --output-dir release_catalog_bootstrap --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --scheme hmac-sha256 --key-id catalog-key
```

For repeatable multi-release packaging, the release-catalog commands can also load a checked-in preset file and still accept CLI overrides on top:

```bash
satroot1 bootstrap-release-catalog-publication --preset-json examples/release_catalog_presets/ai_compute_release_stack.json --output-dir release_catalog_bootstrap --label "SATROOT AI Compute Release Stack Override" --scheme hmac-sha256 --key-id catalog-key
```

For a higher-level network of signed release catalogs, you can build and publish a release-catalog index the same way:

```bash
satroot1 build-release-catalog-index release_catalog_bootstrap another_release_catalog --channel network --label "SATROOT Catalog Network" --published-at 2026-07-02T05:00:00Z --output release_catalog_index.json
satroot1 bootstrap-release-catalog-index-publication --preset-json examples/release_catalog_index_presets/ai_compute_catalog_network.json --output-dir release_catalog_index_bootstrap --label "SATROOT AI Compute Catalog Network Override" --scheme hmac-sha256 --key-id index-key
```

For a single end-to-end workspace, `bootstrap-publication-stack` can take multiple demo-catalog presets plus an optional release-catalog preset and emit catalog workspaces and a top-level release catalog in one shot:

```bash
satroot1 bootstrap-publication-stack --catalog-preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-preset-json examples/release_catalog_presets/ai_compute_release_stack.json --release-catalog-key-id catalog-key --output-dir publication_stack --label "SATROOT Stack Override"
```

If you want the whole stack described in one checked-in file, `bootstrap-publication-stack` also accepts a dedicated stack preset:

```bash
satroot1 bootstrap-publication-stack --stack-preset-json examples/stack_presets/ai_compute_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir publication_stack --label "SATROOT Stack Override"
```

To generate multiple stack workspaces and a top-level signed release-catalog index in one pass, use `bootstrap-publication-network` with one or more stack presets:

```bash
satroot1 bootstrap-publication-network --stack-preset-json examples/stack_presets/ai_compute_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-preset-json examples/release_catalog_index_presets/ai_compute_catalog_network.json --release-catalog-index-key-id index-key --output-dir publication_network --label "SATROOT Network Override"
```

If you want the whole network described in one checked-in file, `bootstrap-publication-network` also accepts a dedicated network preset:

```bash
satroot1 bootstrap-publication-network --network-preset-json examples/network_presets/ai_compute_publication_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir publication_network --label "SATROOT Network Override"
```

If you already have generated demo catalog workspaces and just want to consolidate them into one signed publication stack, use `publish-publication-stack`:

```bash
satroot1 publish-publication-stack generated_catalogs/stable_workspace generated_catalogs/machine_workspace --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir publication_stack_from_existing --label "Published Existing Stack"
```

If you already have generated publication stack workspaces and want a top-level signed network without regenerating the nested stacks, use `publish-publication-network`:

```bash
satroot1 publish-publication-network generated_stacks/stack_alpha generated_stacks/stack_beta --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir publication_network_from_existing --label "Published Existing Network"
```

To scan a generated tree and see which SATROOT bundles, releases, catalogs, indexes, and workspaces are present, use `inventory-artifacts`:

```bash
satroot1 inventory-artifacts publication_network
```

If you only want to report artifacts rooted directly at the given path and skip nested directories, add `--non-recursive`:

```bash
satroot1 inventory-artifacts publication_network --non-recursive
```

To derive a reusable preset back from a generated demo catalog workspace:

```bash
satroot1 export-demo-catalog-preset catalog_workspace --output exported_catalog.json
```

To derive a publication stack preset and also emit nested demo catalog preset files alongside it:

```bash
satroot1 export-publication-stack-preset publication_stack --catalog-preset-dir exported_catalog_presets --output exported_stack.json
```

To derive a publication network preset and recursively emit nested stack and catalog preset files:

```bash
satroot1 export-publication-network-preset publication_network --stack-preset-dir exported_stack_presets --catalog-preset-dir exported_catalog_presets --output exported_network.json
```

To render a human-readable markdown report for a generated SATROOT artifact or workspace:

```bash
satroot1 render-publication-report publication_network
```

The report renderer auto-detects bundle, release, release-catalog, release-catalog-index, demo-catalog, publication-stack, and publication-network inputs, and it can also write to a file:

```bash
satroot1 render-publication-report stable_release --output stable_release_report.md
```

For a normalized machine-readable export of the same detected artifact metadata, use `export-publication-descriptor`:

```bash
satroot1 export-publication-descriptor publication_network --output publication_network_descriptor.json
```

Inspect a release catalog publication without signature verification:

```bash
satroot1 release-catalog-summary release_catalog_bootstrap
```

Lint a release catalog publication and all referenced release directories:

```bash
satroot1 release-catalog-lint release_catalog_bootstrap
```

Inspect a release-catalog index publication without signature verification:

```bash
satroot1 release-catalog-index-summary release_catalog_index_bootstrap
```

Lint a release-catalog index publication and all referenced release-catalog directories:

```bash
satroot1 release-catalog-index-lint release_catalog_index_bootstrap
```

Inspect a demo catalog workspace without signature verification:

```bash
satroot1 demo-catalog-summary catalog_workspace
```

Lint a demo catalog workspace, its nested release, and all referenced bundle directories:

```bash
satroot1 demo-catalog-lint catalog_workspace
```

Inspect a publication stack workspace without signature verification:

```bash
satroot1 publication-stack-summary publication_stack
```

Lint a publication stack workspace, its nested release catalog, and all referenced catalog workspaces:

```bash
satroot1 publication-stack-lint publication_stack
```

Inspect a publication network workspace without signature verification:

```bash
satroot1 publication-network-summary publication_network
```

Lint a publication network workspace, its nested release-catalog index, and all referenced stack summaries:

```bash
satroot1 publication-network-lint publication_network
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

Validate a release catalog, release-catalog index, publication workspace summaries, and their signed manifests directly against the SATROOT schemas:

```bash
satroot1 validate-release-catalog release_catalog.json
satroot1 validate-release-catalog-manifest release_catalog_manifest.json
satroot1 validate-release-catalog-index release_catalog_index.json
satroot1 validate-release-catalog-index-manifest release_catalog_index_manifest.json
satroot1 validate-demo-catalog-summary catalog_workspace/summary.json
satroot1 validate-publication-stack-summary publication_stack/summary.json
satroot1 validate-publication-network-summary publication_network/summary.json
```

Verify a signed release manifest against its bundle index:

```bash
satroot1 verify-release-manifest release_manifest.json --secrets-json release_secrets.json
```

Verify a signed release catalog manifest against its release catalog:

```bash
satroot1 verify-release-catalog-manifest release_catalog_manifest.json --secrets-json release_catalog_secrets.json
```

Verify a signed release-catalog index manifest against its release-catalog index:

```bash
satroot1 verify-release-catalog-index-manifest release_catalog_index_manifest.json --secrets-json release_catalog_index_secrets.json
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
