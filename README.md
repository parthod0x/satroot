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

This repository ships the `SATROOT-1` kernel, six registered profiles, the publication ladder, and the anchored proof loop:

- `SPEC.md` - human-readable protocol specification.
- `ARCHITECTURE.md` - top-level model, layer boundaries, and deliverable framing.
- `BOUNDARIES.md` - claim discipline, non-goals, and legal boundary language.
- `ROADMAP.md` - project scope, deliverables, and released plus planned protocol profiles.
- `ANCHORS.md` - the only checked-in record of real on-chain outpoints and transaction ids.
- `KEY_MANAGEMENT.md` - operational guidance for composing the frozen signature schemes: custody separation, verifier-only distribution, and rotation.
- `CHANGELOG.md`, `RELEASE_CHECKLIST.md`, `CITATION.cff` - release history, pre-tag gates, and citation metadata.
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
- `protocol/satroot1.publication-descriptor-index.schema.json` - JSON schema for publication descriptor indexes.
- `protocol/satroot1.publication-descriptor-index-manifest.schema.json` - JSON schema for signed publication descriptor index manifests.
- `protocol/satroot1.publication-metadata-manifest.schema.json` - JSON schema for signed publication metadata bundles.
- `protocol/satroot1.publication-metadata-catalog.schema.json` - JSON schema for multi-bundle publication metadata catalogs.
- `protocol/satroot1.publication-metadata-catalog-manifest.schema.json` - JSON schema for signed publication metadata catalog manifests.
- `protocol/satroot1.publication-registry.schema.json` - JSON schema for top-level publication registries.
- `protocol/satroot1.publication-registry-manifest.schema.json` - JSON schema for signed publication registry manifests.
- `protocol/satroot1.profile-registry.json` - explicit compatibility registry for supported profiles.
- `src/satroot1.py` - reference parser, deterministic replay engine, and signing utility CLI.
- `src/satroot_*_smoke.py` and `scripts/run_*.py` - the packaged smoke-lane modules and repo-local entrypoints, from per-profile lanes up through the operator proof, release gate, and the four anchored lanes.
- `examples/` - six runnable demo ledgers (`FLOOR1`, `USDROOT1`, `APICREDIT1`, `RECEIPT1`, `IDENTITY1`, `LICENSE1`) and the reusable preset trees.
- `examples/README.md` - guide to the reusable example preset trees, including collection-backed companions.
- `examples/catalog_presets/` - reusable SATROOT demo catalog scenario presets.
- `examples/bundle_index_presets/` - reusable SATROOT bundle-index presets.
- `examples/release_catalog_presets/` - reusable SATROOT release-catalog publication presets.
- `examples/release_catalog_index_presets/` - reusable SATROOT release-catalog-index publication presets.
- `examples/publication_descriptor_index_presets/` - reusable SATROOT publication-descriptor-index presets.
- `examples/publication_metadata_catalog_presets/` - reusable SATROOT publication-metadata-catalog presets.
- `examples/publication_catalog_workspace_presets/` - reusable SATROOT publication-catalog-workspace presets.
- `examples/registry_presets/` - reusable SATROOT publication-registry presets.
- `examples/registry_workspace_presets/` - reusable SATROOT publication-registry-workspace presets.
- `examples/network_presets/` - reusable SATROOT publication-network presets.
- `examples/stack_presets/` - reusable SATROOT end-to-end publication-stack presets.
- `tests/` - test modules covering the kernel plus every packaged smoke lane.
- `profiles/stable/SATROOT-STABLE-1.md` - reference-only stable-value profile draft.
- `profiles/machine/SATROOT-MACHINE-1.md` - prepaid machine-credit profile draft.
- `profiles/receipt/SATROOT-RECEIPT-1.md` - receipt and invoice object profile draft.
- `profiles/identity/SATROOT-IDENTITY-1.md` - identity and authority object profile draft.
- `profiles/license/SATROOT-LICENSE-1.md` - license and usage-right object profile draft.
- `profiles/event/SATROOT-EVENT-1.md` - event-stream head object profile draft.

## SATROOT-1 in one sentence

`SATROOT-1` turns one satoshi into a root-bound namespace for deterministic semantic token state.

For the higher-level framing of how BSV, the SATROOT kernel, and the profile system fit together, see `ARCHITECTURE.md`.

The `SATROOT-1` kernel defines:

- a `root_id` bound to a one-satoshi UTXO,
- a genesis record,
- `mint`, `transfer`, `burn`, `freeze`, and `rotate-authority` events,
- strict sequencing with `prev_event_id`,
- deterministic replay and balance computation,
- a supply invariant,
- explicit root authority rotation for mint-control handoff,
- explicit freeze / unfreeze controls for account-level balance locks,
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
- a one-shot SATROOT-MACHINE-1 demo-catalog bootstrap for workspace-ready machine-profile release lanes,
- a one-shot SATROOT-MACHINE-1 publication-catalog-workspace bootstrap for machine-profile descriptor and metadata publication lanes,
- a one-shot SATROOT-MACHINE-1 publication-registry-workspace bootstrap for machine-profile descriptor, metadata, and registry publication lanes,
- profile-aware lifecycle helpers for singleton receipt, identity, and license transfer, archival, and retirement flows,
- a one-shot singleton receipt/identity/license demo bootstrap for runnable object-profile lifecycle artifacts,
- a one-shot singleton receipt/identity/license signed demo-bundle bootstrap for verifiable object-profile artifacts,
- a one-shot singleton receipt/identity/license demo-release bootstrap for bundle plus release publication generation,
- a one-shot SATROOT-STABLE-1 reference-demo bootstrap for runnable stable-profile artifact generation,
- a one-shot SATROOT-STABLE-1 signed demo-bundle bootstrap for release-ready stable-profile artifacts,
- a one-shot SATROOT-STABLE-1 demo-release bootstrap for bundle plus release publication generation,
- a one-shot multi-profile demo catalog workspace bootstrap for bundles plus signed catalog release generation,
- repeated-preset multi-profile demo release collection bootstraps for packaging mixed generated releases into reusable release collections,
- repeated-preset multi-profile demo release catalog publication bootstraps for turning mixed generated releases into signed release catalogs in one step,
- repeated-preset multi-profile demo release catalog index publication bootstraps for turning mixed generated releases into signed release-catalog index publications in one step,
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
- unsigned multi-bundle inspection via `bundle-index-summary` before release signing,
- structural bundle-index linting via `bundle-index-lint` for nested bundle manifest drift,
- release-level inspection via `release-summary` when signature verification is unnecessary,
- structural release linting via `release-lint` for bundle-index and manifest drift,
- deterministic bundle-index generation for release catalogs spanning multiple bundles,
- discovery-based bundle catalog packaging from parent artifact directories,
- optional release metadata on bundle indexes for channel, label, and published-at packaging context,
- signed release-manifest generation for authenticating distributable bundle-index publications,
- release-key bootstrap helpers for HMAC and Ed25519 publication signing workflows,
- one-shot `publish-release` orchestration for ready-to-verify release directories,
- preset export commands for deriving reusable bundle-index presets back from generated signed release inputs,
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
- preset export commands for deriving reusable release-catalog and release-catalog-index presets back from generated signed artifact layers,
- one-shot `bootstrap-genesis-bundle` scaffolding for signed starter bundles from profile-aware genesis defaults,
- one-shot `bootstrap-release-publication` orchestration for release material plus signed publication outputs,
- one-shot `bootstrap-release-catalog-publication` orchestration for release-catalog material plus signed publication outputs,
- one-shot `bootstrap-release-catalog-index-publication` orchestration for release-catalog-index material plus signed publication outputs,
- demo-catalog inspection via `demo-catalog-summary` and structural linting via `demo-catalog-lint`,
- one-shot `bootstrap-publication-stack` orchestration for preset-driven bundles, releases, and release-catalog outputs in one workspace,
- `publish-publication-stack` for consolidating existing demo catalog workspaces into one signed release-catalog stack,
- `publish-machine-publication-stack` for consolidating existing SATROOT-MACHINE-1 demo catalog workspaces into one machine-only signed release-catalog stack,
- publication-stack inspection via `publication-stack-summary` and structural linting via `publication-stack-lint`,
- `bootstrap-publication-stack-collection` for copying existing publication stack workspaces into reusable higher-level collections,
- one-shot `bootstrap-publication-network` orchestration for preset-driven stacks plus a top-level release-catalog-index output in one workspace,
- `publish-publication-network` for consolidating existing publication stack workspaces into one signed release-catalog-index network,
- `publish-machine-publication-network` for consolidating existing SATROOT-MACHINE-1 publication stack workspaces into one machine-only signed release-catalog-index network,
- publication-network inspection via `publication-network-summary` and structural linting via `publication-network-lint`,
- one-shot `bootstrap-publication-catalog-workspace` orchestration for generating reusable descriptor-index and metadata-catalog lanes from arbitrary SATROOT artifacts,
- `publish-publication-catalog-workspace` for consolidating an existing publication descriptor index plus publication metadata catalog into one reusable publication-catalog workspace,
- publication-catalog-workspace inspection via `publication-catalog-workspace-summary` and structural linting via `publication-catalog-workspace-lint`,
- one-shot `bootstrap-publication-registry-workspace` orchestration for copying a release-catalog-index publication, generating descriptor and metadata publication lanes, and emitting a top-level signed registry workspace,
- `publish-publication-registry-workspace` for consolidating an existing publication-catalog workspace plus release-catalog-index source into one signed publication-registry workspace,
- publication-registry-workspace inspection via `publication-registry-workspace-summary` and structural linting via `publication-registry-workspace-lint`,
- publication-registry inspection via `publication-registry-summary` and structural linting via `publication-registry-lint`,
- `inventory-artifacts` for scanning a directory tree and summarizing discovered SATROOT artifacts across bundle, release, catalog, index, registry, and workspace layers,
- preset export commands for deriving reusable demo-catalog, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace presets back from generated workspaces,
- `render-publication-report` for turning detected SATROOT artifacts or workspaces into human-readable markdown reports,
- `export-publication-descriptor` for emitting normalized JSON descriptors from detected SATROOT artifacts or workspaces,
- `build-publication-descriptor-index` for aggregating many detected SATROOT descriptors into one machine-readable registry,
- signed publication-descriptor-index-manifest generation for authenticating descriptor registries,
- `build-machine-publication-descriptor-index` and `build-stable-publication-descriptor-index` for enforcing machine-only or stable-only validation before descriptor-index generation,
- `build-machine-publication-descriptor-index-manifest` and `build-stable-publication-descriptor-index-manifest` for signing only machine-validated or stable-validated descriptor indexes,
- `publish-publication-descriptor-index`, `publish-machine-publication-descriptor-index`, and `publish-stable-publication-descriptor-index` for writing signed descriptor-index publication directories from existing signer material,
- one-shot `bootstrap-publication-descriptor-index-publication` orchestration for descriptor indexes plus signing material,
- publication-descriptor-index inspection via `publication-descriptor-index-summary` and structural linting via `publication-descriptor-index-lint`,
- preset export commands for deriving reusable publication-descriptor-index presets back from generated descriptor index publications,
- signed publication-metadata-manifest generation for authenticating one artifact's rendered report plus normalized descriptor,
- `build-machine-publication-metadata-manifest` for signing only machine-validated publication report and descriptor pairs,
- `build-stable-publication-metadata-manifest` for signing only stable-validated publication report and descriptor pairs,
- `publish-publication-metadata-bundle`, `publish-machine-publication-metadata-bundle`, and `publish-stable-publication-metadata-bundle` for writing signed publication metadata bundles from existing signer material,
- publication-metadata-bundle inspection via `publication-metadata-bundle-summary` and structural linting via `publication-metadata-bundle-lint`,
- `bootstrap-machine-publication-metadata-bundle` for generating machine-only publication metadata bundles with SATROOT-MACHINE-1 artifact validation before signing,
- `bootstrap-stable-publication-metadata-bundle` for generating stable-only publication metadata bundles with SATROOT-STABLE-1 artifact validation before signing,
- `build-publication-metadata-catalog` for aggregating many publication metadata bundles into one machine-readable registry,
- `build-machine-publication-metadata-catalog` and `build-stable-publication-metadata-catalog` for enforcing machine-only or stable-only validation before catalog generation,
- signed publication-metadata-catalog-manifest generation for authenticating publication metadata catalogs,
- `build-machine-publication-metadata-catalog-manifest` and `build-stable-publication-metadata-catalog-manifest` for signing only machine-validated or stable-validated publication metadata catalogs,
- `publish-publication-metadata-catalog`, `publish-machine-publication-metadata-catalog`, and `publish-stable-publication-metadata-catalog` for writing signed metadata-catalog publication directories from existing signer material,
- one-shot `bootstrap-publication-metadata-catalog-publication` orchestration for metadata catalogs plus signing material,
- publication-metadata-catalog inspection via `publication-metadata-catalog-summary` and structural linting via `publication-metadata-catalog-lint`,
- preset export commands for deriving reusable publication-metadata-catalog presets back from generated metadata catalog publications,
- `build-publication-registry` for binding descriptor, metadata, and release-catalog-index publications into one top-level signed namespace artifact,
- `build-machine-publication-registry` and `build-stable-publication-registry` for enforcing machine-only or stable-only validation before registry generation,
- signed publication-registry-manifest generation for authenticating top-level publication registries,
- `build-machine-publication-registry-manifest` and `build-stable-publication-registry-manifest` for signing only machine-validated or stable-validated publication registries,
- `publish-publication-registry`, `publish-machine-publication-registry`, and `publish-stable-publication-registry` for writing signed registry publication directories from existing signer material,
- one-shot `bootstrap-publication-registry-publication` orchestration for registry publications plus signing material,
- preset export commands for deriving reusable publication-registry presets back from generated registry publications,
- demo-catalog, publication-stack, and publication-network summary schema validation for exported workspace summaries,
- signed bundle verification against manifest and verifier material,
- bundle-manifest, bundle-index, release-manifest, release-catalog, release-catalog-manifest, release-catalog-index, release-catalog-index-manifest, publication-descriptor-index, publication-descriptor-index-manifest, publication-metadata-manifest, publication-metadata-catalog, publication-metadata-catalog-manifest, publication-registry, publication-registry-manifest, demo-catalog-summary, publication-stack-summary, and publication-network-summary schema validation for exported signed artifacts,
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
- `satroot1 bootstrap-stable-demo` for generating new reference-only demo ledgers on demand, with optional stable-only preset defaults,
- `satroot1 bootstrap-stable-demo-bundle` for generating signed stable demo bundles directly from profile parameters or a stable-only preset,
- `satroot1 bootstrap-stable-demo-release` for generating signed stable demo bundles plus release directories in one step, with optional stable-only preset defaults,
- `satroot1 bootstrap-stable-demo-release-collection` for generating multiple stable-only demo release workspaces from repeated stable presets and packaging them into one reusable release collection,
- `satroot1 bootstrap-stable-demo-release-catalog-publication` for generating multiple stable-only demo release workspaces from repeated stable presets, snapshotting them into a release collection, and bootstrapping a signed stable release catalog publication in one step,
- `satroot1 bootstrap-stable-demo-release-catalog-index-publication` for generating multiple stable-only demo release workspaces from repeated stable presets, bootstrapping a stable release catalog publication, and then bootstrapping a signed stable release catalog index publication in one step,
- `satroot1 bootstrap-stable-demo-catalog` for generating a reusable single-stable demo catalog workspace that can feed the broader catalog and publication flows, with optional stable-only preset support,
- `satroot1 bootstrap-demo-publication-stack` for generating one or more mixed-profile demo catalog workspaces from repeated generic presets and publishing them as a signed release-catalog stack in one step,
- `satroot1 bootstrap-demo-publication-network` for generating one or more mixed-profile demo catalog workspaces from repeated generic presets, bootstrapping a publication stack, and then publishing that stack as a signed release-catalog index in one step,
- `satroot1 bootstrap-demo-publication-catalog-workspace` for generating multiple mixed-profile demo catalog workspaces from repeated generic presets and deriving shared descriptor-index and metadata publication lanes in one reusable publication catalog workspace,
- `satroot1 bootstrap-demo-publication-registry-workspace` for generating multiple mixed-profile demo catalog workspaces from repeated generic presets, deriving shared publication lanes, and binding them to a generated publication network in one signed registry workspace,
- `satroot1 bootstrap-stable-demo-publication-stack` for generating multiple stable-only demo catalog workspaces from repeated stable presets and publishing them as a signed release-catalog stack in one step,
- `satroot1 bootstrap-stable-demo-publication-network` for generating multiple stable-only demo catalog workspaces from repeated stable presets, bootstrapping a stable publication stack, and then publishing that stack as a signed release-catalog index in one step,
- `satroot1 bootstrap-stable-demo-publication-catalog-workspace` for generating multiple stable-only demo catalog workspaces from repeated stable presets and deriving shared descriptor-index and metadata publication lanes in one reusable publication catalog workspace,
- `satroot1 bootstrap-stable-demo-publication-registry-workspace` for generating multiple stable-only demo catalog workspaces from repeated stable presets, deriving shared publication lanes, and binding them to a generated stable publication network in one signed registry workspace,
- `satroot1 bootstrap-stable-publication-stack` for generating one or more stable-only demo catalog workspaces and publishing them as a release-catalog stack,
- `satroot1 bootstrap-stable-publication-network` for generating one or more stable-only publication stacks and publishing them as a release-catalog index,
- `satroot1 bootstrap-stable-publication-catalog-workspace` for generating a stable demo catalog workspace plus descriptor-index and metadata publication lanes in one step, with optional nested demo-catalog and publication-catalog-workspace presets,
- `satroot1 publish-stable-publication-catalog-workspace` for re-wrapping existing stable descriptor and metadata lanes back into a stable-validated publication catalog workspace,
- `satroot1 export-stable-publication-catalog-workspace-preset` for exporting that stable publication catalog workspace shape back into a validated reusable preset,
- `satroot1 bootstrap-stable-publication-registry-workspace` for generating a stable publication catalog workspace and binding it to a stable release-catalog-index source in one signed registry workspace, with optional nested demo-catalog, publication-catalog-workspace, and publication-registry-workspace presets, including frozen `release_collection_dir`-backed nested catalog presets where `--release-key-id` is only needed when a nested publication-network preset is being generated,
- `satroot1 publish-stable-publication-registry-workspace` for binding an existing stable publication catalog workspace to a stable release-catalog-index source while preserving stable provenance,
- `satroot1 export-stable-publication-registry-workspace-preset` for exporting that stable publication registry workspace shape back into a validated reusable preset,
- `satroot1 export-stable-publication-descriptor-index-preset`, `satroot1 export-stable-publication-metadata-catalog-preset`, and `satroot1 export-stable-publication-registry-preset` for exporting stable component publications back into validated reusable presets.
- checked-in example presets now cover generic, machine-only, and stable-only component publication layers across `examples/bundle_index_presets/`, `examples/release_catalog_presets/`, `examples/release_catalog_index_presets/`, `examples/publication_descriptor_index_presets/`, `examples/publication_metadata_catalog_presets/`, `examples/publication_catalog_workspace_presets/`, `examples/registry_workspace_presets/`, and `examples/registry_presets/`.
- `examples/bundle_index_presets/`, `examples/release_catalog_presets/`, and `examples/release_catalog_index_presets/` now also include collection-backed companion presets for frozen generated bundle, release, and release-catalog sets.
- `examples/stack_presets/`, `examples/network_presets/`, `examples/publication_metadata_catalog_presets/`, `examples/publication_catalog_workspace_presets/`, `examples/registry_workspace_presets/`, and `examples/registry_presets/` now also include collection-backed companion presets for frozen demo-catalog, publication-stack, publication-network, publication-metadata-bundle, publication-catalog-workspace, and publication-registry inputs.
- `examples/README.md` maps the generic, machine, stable, and collection-backed preset trees if you want one entry point into the full example set.

If you want the shortest path into the checked-in reusable SATROOT preset tree, start here:

- Generic lower release layers:
  `examples/catalog_presets/ai_compute_catalog.json`
  `examples/bundle_index_presets/ai_compute_bundle_index.json`
  `examples/release_catalog_presets/ai_compute_release_stack.json`
  `examples/release_catalog_index_presets/ai_compute_catalog_network.json`
- Generic publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog.json`
  `examples/publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace.json`
  `examples/stack_presets/ai_compute_publication_stack.json`
  `examples/network_presets/ai_compute_publication_network.json`
  `examples/registry_workspace_presets/ai_compute_publication_registry_workspace.json`
- Generic collection-backed lower release layers:
  `examples/catalog_presets/ai_compute_catalog_collection_backed.json`
  `examples/bundle_index_presets/ai_compute_bundle_index_collection_backed.json`
  `examples/release_catalog_presets/ai_compute_release_stack_collection_backed.json`
  `examples/release_catalog_index_presets/ai_compute_catalog_network_collection_backed.json`
- Generic collection-backed publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog_collection_backed.json`
  `examples/publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace_collection_backed.json`
  `examples/stack_presets/ai_compute_publication_stack_collection_backed.json`
  `examples/network_presets/ai_compute_publication_network_collection_backed.json`
  `examples/registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json`
  `examples/registry_workspace_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- Machine lower release layers:
  `examples/catalog_presets/machine_compute_catalog.json`
  `examples/bundle_index_presets/machine_compute_bundle_index.json`
  `examples/release_catalog_presets/machine_compute_release_stack.json`
  `examples/release_catalog_index_presets/machine_compute_catalog_network.json`
- Machine publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog.json`
  `examples/publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace.json`
  `examples/stack_presets/machine_compute_publication_stack.json`
  `examples/network_presets/machine_compute_publication_network.json`
  `examples/registry_workspace_presets/machine_compute_publication_registry_workspace.json`
- Machine collection-backed lower release layers:
  `examples/catalog_presets/machine_compute_catalog_collection_backed.json`
  `examples/bundle_index_presets/machine_compute_bundle_index_collection_backed.json`
  `examples/release_catalog_presets/machine_compute_release_stack_collection_backed.json`
  `examples/release_catalog_index_presets/machine_compute_catalog_network_collection_backed.json`
- Machine collection-backed publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/machine_compute_publication_metadata_catalog_collection_backed.json`
  `examples/publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace_collection_backed.json`
  `examples/stack_presets/machine_compute_publication_stack_collection_backed.json`
  `examples/network_presets/machine_compute_publication_network_collection_backed.json`
  `examples/registry_workspace_presets/machine_compute_publication_registry_workspace_collection_backed.json`
  `examples/registry_workspace_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`
- Stable lower release layers:
  `examples/catalog_presets/stable_reference_catalog.json`
  `examples/bundle_index_presets/stable_reference_bundle_index.json`
  `examples/release_catalog_presets/stable_reference_release_stack.json`
  `examples/release_catalog_index_presets/stable_reference_catalog_network.json`
- Stable publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog.json`
  `examples/publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace.json`
  `examples/stack_presets/stable_reference_publication_stack.json`
  `examples/network_presets/stable_reference_publication_network.json`
  `examples/registry_workspace_presets/stable_reference_publication_registry_workspace.json`
- Stable collection-backed lower release layers:
  `examples/catalog_presets/stable_reference_catalog_collection_backed.json`
  `examples/bundle_index_presets/stable_reference_bundle_index_collection_backed.json`
  `examples/release_catalog_presets/stable_reference_release_stack_collection_backed.json`
  `examples/release_catalog_index_presets/stable_reference_catalog_network_collection_backed.json`
- Stable collection-backed publication metadata/catalog/stack/network/registry-workspace:
  `examples/publication_metadata_catalog_presets/stable_reference_publication_metadata_catalog_collection_backed.json`
  `examples/publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace_collection_backed.json`
  `examples/stack_presets/stable_reference_publication_stack_collection_backed.json`
  `examples/network_presets/stable_reference_publication_network_collection_backed.json`
  `examples/registry_workspace_presets/stable_reference_publication_registry_workspace_collection_backed.json`
  `examples/registry_workspace_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`
- Collection-backed top-level registry publications:
  `examples/registry_presets/ai_compute_publication_registry_collection_backed.json`
  `examples/registry_presets/machine_compute_publication_registry_collection_backed.json`
  `examples/registry_presets/stable_reference_publication_registry_collection_backed.json`
- Frozen-release self-contained top-level registry publications:
  `examples/registry_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json`
  `examples/registry_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json`
  `examples/registry_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json`
- Workspace-backed top-level registry publications:
  `examples/registry_presets/ai_compute_publication_registry_workspace_backed.json`
  `examples/registry_presets/machine_compute_publication_registry_workspace_backed.json`
  `examples/registry_presets/stable_reference_publication_registry_workspace_backed.json`

This repo also now includes the first machine-credit profile draft:

- `SATROOT-MACHINE-1` for prepaid machine-native service credits,
- `examples/genesis_apicredit1.json` for an `APICREDIT1` genesis record,
- `examples/events_apicredit1.json` for a runnable machine-credit ledger flow,
- `satroot1 bootstrap-machine-demo` for generating new machine-credit demo ledgers on demand, with optional machine-only preset defaults,
- `satroot1 bootstrap-machine-demo-bundle` for generating signed machine-credit demo bundles directly from profile parameters or a machine-only preset,
- `satroot1 bootstrap-machine-demo-release` for generating signed machine-credit demo bundles plus release directories in one step, with optional machine-only preset defaults,
- `satroot1 bootstrap-machine-demo-release-collection` for generating multiple machine-only demo release workspaces from repeated machine presets and packaging them into one reusable release collection,
- `satroot1 bootstrap-machine-demo-release-catalog-publication` for generating multiple machine-only demo release workspaces from repeated machine presets, snapshotting them into a release collection, and bootstrapping a signed machine release catalog publication in one step,
- `satroot1 bootstrap-machine-demo-release-catalog-index-publication` for generating multiple machine-only demo release workspaces from repeated machine presets, bootstrapping a machine release catalog publication, and then bootstrapping a signed machine release catalog index publication in one step,
- `satroot1 bootstrap-machine-demo-catalog` for generating a reusable single-machine demo catalog workspace that can feed the stack, network, and publication flows, now with optional generic demo-catalog preset support,
- `satroot1 bootstrap-machine-demo-publication-stack` for generating multiple machine-only demo catalog workspaces from repeated machine presets and publishing them as a signed release-catalog stack in one step,
- `satroot1 bootstrap-machine-demo-publication-network` for generating multiple machine-only demo catalog workspaces from repeated machine presets, bootstrapping a machine publication stack, and then publishing that stack as a signed release-catalog index in one step,
- `satroot1 bootstrap-machine-demo-publication-catalog-workspace` for generating multiple machine-only demo catalog workspaces from repeated machine presets and deriving shared descriptor-index and metadata publication lanes in one reusable publication catalog workspace,
- `satroot1 bootstrap-machine-demo-publication-registry-workspace` for generating multiple machine-only demo catalog workspaces from repeated machine presets, deriving shared publication lanes, and binding them to a generated machine publication network in one signed registry workspace,
- `satroot1 bootstrap-machine-publication-stack` for generating one or more machine-only demo catalog workspaces and publishing them as a release-catalog stack,
- `satroot1 publish-machine-publication-stack` for consolidating existing machine-only demo catalog workspaces into the same SATROOT-MACHINE-1 publication stack shape,
- `satroot1 bootstrap-machine-publication-network` for generating one or more machine-only publication stacks and publishing them as a release-catalog index,
- `satroot1 publish-machine-publication-network` for consolidating existing machine-only publication stack workspaces into the same SATROOT-MACHINE-1 publication network shape,
- `satroot1 bootstrap-machine-publication-catalog-workspace` for generating a machine demo catalog workspace plus descriptor-index and metadata publication lanes in one step, now with optional nested demo-catalog and publication-catalog-workspace presets,
- `satroot1 publish-machine-publication-catalog-workspace` for re-wrapping existing publication descriptor and metadata lanes back into a machine-validated publication catalog workspace,
- `satroot1 export-machine-publication-catalog-workspace-preset` for exporting that machine publication catalog workspace shape back into a validated reusable preset,
- `satroot1 bootstrap-machine-publication-registry-workspace` for generating a machine publication catalog workspace and binding it to a release-catalog-index source in one signed registry workspace, now with optional nested demo-catalog, publication-catalog-workspace, and publication-registry-workspace presets, including frozen `release_collection_dir`-backed nested catalog presets where `--release-key-id` is only needed when a nested publication-network preset is being generated,
- `satroot1 publish-machine-publication-registry-workspace` for binding an existing machine publication catalog workspace to a release-catalog-index source while preserving machine provenance,
- `satroot1 export-machine-publication-registry-workspace-preset` for exporting that machine publication registry workspace shape back into a validated reusable preset.

This repo also now includes the first receipt-object profile draft:

- `SATROOT-RECEIPT-1` for invoice and receipt state objects,
- `examples/genesis_receipt1.json` for a `RECEIPT1` genesis record,
- `examples/events_receipt1.json` for a runnable receipt lifecycle ledger flow,
- `satroot1 bootstrap-singleton-demo --profile SATROOT-RECEIPT-1` for generating new receipt/identity/license singleton demo ledgers on demand,
- `satroot1 bootstrap-singleton-demo-bundle --profile SATROOT-RECEIPT-1` for generating signed receipt/identity/license demo bundles on demand,
- `satroot1 bootstrap-singleton-demo-release --profile SATROOT-RECEIPT-1` for generating signed receipt/identity/license demo bundles plus release directories in one step,
- `satroot1 bootstrap-singleton-demo-bundle-index --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license demo bundles from presets and packaging them into a reusable bundle index,
- `satroot1 bootstrap-singleton-demo-release-collection --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license demo releases from presets and packaging them into a reusable release collection,
- `satroot1 bootstrap-singleton-demo-release-catalog-publication --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license demo releases from presets and bootstrapping a signed release catalog publication in one step,
- `satroot1 bootstrap-singleton-demo-release-catalog-index-publication --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license demo releases from presets and bootstrapping a signed release-catalog index publication in one step,
- `satroot1 bootstrap-singleton-demo-publication-stack --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license singleton demo catalog workspaces from presets and publishing them as a signed release-catalog stack in one step,
- `satroot1 bootstrap-singleton-demo-publication-network --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license singleton demo catalog workspaces from presets, bootstrapping a singleton publication stack, and then publishing that stack as a signed release-catalog index in one step,
- `satroot1 bootstrap-singleton-demo-publication-catalog-workspace --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license singleton demo catalog workspaces from presets and deriving shared descriptor and metadata publication lanes in one reusable publication catalog workspace,
- `satroot1 bootstrap-singleton-demo-publication-registry-workspace --profile SATROOT-RECEIPT-1` for generating repeated receipt/identity/license singleton demo catalog workspaces from presets, deriving shared publication lanes, and binding them to a generated singleton publication network in one signed registry workspace.

This repo also now includes the first identity-object profile draft:

- `SATROOT-IDENTITY-1` for identity and authority state objects,
- `examples/genesis_identity1.json` for an `IDENTITY1` genesis record,
- `examples/events_identity1.json` for a runnable identity lifecycle ledger flow.

This repo also now includes the first license-object profile draft:

- `SATROOT-LICENSE-1` for license and usage-right state objects,
- `examples/genesis_license1.json` for a `LICENSE1` genesis record,
- `examples/events_license1.json` for a runnable license lifecycle ledger flow.

The sixth registered profile extends the singleton family to event streams:

- `SATROOT-EVENT-1` for append-only event-stream head objects with deterministic publisher handoff,
- `examples/genesis_event1.json` for an `EVENT1` genesis record,
- `examples/events_event1.json` for a runnable stream-custody handoff ledger flow,
- `python scripts/run_event_profile_smoke.py` (or `python -m satroot_event_profile_smoke` / `satroot-event-profile-smoke`) for its dedicated verification lane.

The event lane is a full member of the demo catalog matrix, the profile-matrix smoke, and the federation surface, alongside the five original profiles.

Further profile work can extend that pattern beyond the six registered profiles for:

- additional authority object profiles,
- additional rights profiles.

## Run tests

For a quick local smoke run:

```bash
python -m pytest
```

For the full suite, prefer the chunked helper:

```bash
python scripts/run_pytest_chunked.py
```

For a stable-profile end-to-end smoke pass that replays the checked-in `USDROOT1` example and generates a full `SATROOT-STABLE-1` publication registry workspace:

```bash
python scripts/run_stable_profile_smoke.py
```

By default that writes into `.tmp_stable_profile_smoke_run/` so the generated workspace stays clearly disposable.

For the matching machine-credit lane, there is now an end-to-end smoke pass that replays `APICREDIT1` and generates a full `SATROOT-MACHINE-1` publication registry workspace:

```bash
python scripts/run_machine_profile_smoke.py
```

That one writes into `.tmp_machine_profile_smoke_run/` by default.

For the lower operator layer above individual bundles, there are now stable and machine bundle-index smoke passes that stage two checked-in presets, generate reusable signed bundle collections, and build one bundle index above each lane:

```bash
python scripts/run_machine_demo_bundle_index_smoke.py
python scripts/run_stable_demo_bundle_index_smoke.py
```

Those write into `.tmp_machine_demo_bundle_index_smoke_run/` and `.tmp_stable_demo_bundle_index_smoke_run/` by default.

For the higher-level machine release-catalog operator lane, there is also a smoke pass that stages two machine-only catalog presets from the checked-in compute example, generates a signed multi-release collection, and bootstraps a signed machine release catalog publication:

```bash
python scripts/run_machine_demo_release_catalog_smoke.py
```

That one writes into `.tmp_machine_demo_release_catalog_smoke_run/` by default.

For the matching stable release-catalog operator lane, there is a parallel smoke pass built from the checked-in stable reference catalog preset:

```bash
python scripts/run_stable_demo_release_catalog_smoke.py
```

That one writes into `.tmp_stable_demo_release_catalog_smoke_run/` by default.

For the release-catalog index layer above those same stable and machine operator lanes, there are matching smokes that stage two checked-in presets, generate signed collections, bootstrap release catalog publications, and then bootstrap signed release catalog index publications:

```bash
python scripts/run_machine_demo_release_catalog_index_smoke.py
python scripts/run_stable_demo_release_catalog_index_smoke.py
```

Those write into `.tmp_machine_demo_release_catalog_index_smoke_run/` and `.tmp_stable_demo_release_catalog_index_smoke_run/` by default.

For the receipt-object lane, there is now a matching end-to-end smoke pass that replays `RECEIPT1` and materializes a full `SATROOT-RECEIPT-1` singleton publication registry workspace from the checked-in receipt preset:

```bash
python scripts/run_receipt_profile_smoke.py
```

That one writes into `.tmp_receipt_profile_smoke_run/` by default.

For the lower singleton operator layer above individual receipt, identity, and license bundles, there are now matching bundle-index smoke passes that stage two checked-in presets, generate reusable signed bundle collections, and build one bundle index above each lane:

```bash
python scripts/run_receipt_demo_bundle_index_smoke.py
python scripts/run_identity_demo_bundle_index_smoke.py
python scripts/run_license_demo_bundle_index_smoke.py
```

Those write into `.tmp_receipt_demo_bundle_index_smoke_run/`, `.tmp_identity_demo_bundle_index_smoke_run/`, and `.tmp_license_demo_bundle_index_smoke_run/` by default.

For the identity-object lane, there is now a matching end-to-end smoke pass that replays `IDENTITY1` and materializes a full `SATROOT-IDENTITY-1` singleton publication registry workspace from the checked-in identity preset:

```bash
python scripts/run_identity_profile_smoke.py
```

That one writes into `.tmp_identity_profile_smoke_run/` by default.

For the license-object lane, there is now a matching end-to-end smoke pass that replays `LICENSE1` and materializes a full `SATROOT-LICENSE-1` singleton publication registry workspace from the checked-in license preset:

```bash
python scripts/run_license_profile_smoke.py
```

That one writes into `.tmp_license_profile_smoke_run/` by default.

After `pip install -e .`, the packaged entrypoints are available too:

```bash
python -m satroot_test
```

or:

```bash
satroot-test
```

For the preferred local pre-tag release gate above the individual verification surfaces, use:

```bash
python -m satroot_release_gate_smoke
```

or:

```bash
satroot-release-gate-smoke
```

That one writes into `.tmp_release_gate_smoke_run/` by default and runs installed-module import smoke, the top-level operator proof, and chunked pytest together into one consolidated release-gate report.

The GitHub Actions test workflow now uses this same release-gate wrapper as its single umbrella check after installed-module import smoke: the operator proof inside the gate re-runs the ladder, federation, registry, and anchored surfaces, and chunked pytest covers every per-lane smoke test, so CI does not repeat the narrower smoke workflows as separate steps.

The preferred top-level verification for the currently released operator surface is:

```bash
python -m satroot_operator_proof_smoke
```

or:

```bash
satroot-operator-proof-smoke
```

That one writes into `.tmp_operator_proof_smoke_run/` by default and runs the stable/machine publication ladder, the singleton publication ladder, the mixed-profile federation smoke, and the collection-backed federated registry publication round trip, plus the four anchored surfaces — anchored demo, anchored publication, on-chain envelope, and envelope verification — for eight surfaces total in one consolidated proof report, with the two ed25519 surfaces skipping gracefully without the `[crypto]` extra.

If you only want the released per-profile verification surface beneath that top-level proof, use:

```bash
python -m satroot_profile_matrix_smoke
```

or:

```bash
satroot-profile-matrix-smoke
```

That one writes into `.tmp_profile_matrix_smoke_run/` by default and runs the stable, machine, receipt, identity, and license profile smoke workflows into one consolidated report.

For the matching lower singleton operator layer, there is also:

```bash
python -m satroot_singleton_demo_bundle_index_matrix_smoke
```

or:

```bash
satroot-singleton-demo-bundle-index-matrix-smoke
```

That one writes into `.tmp_singleton_demo_bundle_index_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo bundle-index smoke workflows into one consolidated report.

For the next singleton operator layer above those bundle indexes, there is also:

```bash
python -m satroot_singleton_demo_release_catalog_matrix_smoke
```

or:

```bash
satroot-singleton-demo-release-catalog-matrix-smoke
```

That one writes into `.tmp_singleton_demo_release_catalog_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo release-catalog smoke workflows into one consolidated report.

For the next singleton operator layer above those per-profile catalogs, there is also:

```bash
python -m satroot_singleton_demo_release_catalog_index_matrix_smoke
```

or:

```bash
satroot-singleton-demo-release-catalog-index-matrix-smoke
```

That one writes into `.tmp_singleton_demo_release_catalog_index_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo release-catalog-index smoke workflows into one consolidated report.

If you want the full singleton operator ladder in one pass, there is also:

```bash
python -m satroot_singleton_publication_ladder_smoke
```

or:

```bash
satroot-singleton-publication-ladder-smoke
```

That one writes into `.tmp_singleton_publication_ladder_smoke_run/` by default and runs the singleton bundle-index, release-catalog, and release-catalog-index matrix smokes together into one consolidated ladder report.

For the lowest multi-bundle operator layer above those direct profile smokes, there is also:

```bash
python -m satroot_demo_bundle_index_matrix_smoke
```

or:

```bash
satroot-demo-bundle-index-matrix-smoke
```

That one writes into `.tmp_demo_bundle_index_matrix_smoke_run/` by default and runs the stable and machine demo bundle-index smoke workflows into one consolidated report.

For the lower operator layer above single releases but beneath the profile federation proof, there is also:

```bash
python -m satroot_demo_release_catalog_matrix_smoke
```

or:

```bash
satroot-demo-release-catalog-matrix-smoke
```

That one writes into `.tmp_demo_release_catalog_matrix_smoke_run/` by default and runs the stable and machine demo release-catalog smoke workflows into one consolidated report.

For the next layer up in that same operator ladder, there is also:

```bash
python -m satroot_demo_release_catalog_index_matrix_smoke
```

or:

```bash
satroot-demo-release-catalog-index-matrix-smoke
```

That one writes into `.tmp_demo_release_catalog_index_matrix_smoke_run/` by default and runs the stable and machine demo release-catalog-index smoke workflows into one consolidated report.

If you want that full stable/machine operator ladder in one pass, there is also:

```bash
python -m satroot_publication_ladder_smoke
```

or:

```bash
satroot-publication-ladder-smoke
```

That one writes into `.tmp_publication_ladder_smoke_run/` by default and runs the stable/machine bundle-index, release-catalog, and release-catalog-index matrix smokes together into one consolidated ladder report.

For the first operator-facing federation check above those released lanes, there is also:

```bash
python -m satroot_profile_federation_smoke
```

or:

```bash
satroot-profile-federation-smoke
```

That one writes into `.tmp_profile_federation_smoke_run/` by default, reuses the released profile matrix, freezes the resulting per-profile demo-catalog, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace outputs into explicit collections, builds one shared mixed-profile publication catalog workspace plus publication registry workspace above the federated network, snapshots those mixed top-level workspaces into their own explicit collections too, and round-trips the federated catalog workspace, stack, network, and top-level registry workspace back through exported nested presets.

If you want the next higher proof layer above that federated workspace surface, there is also:

```bash
python -m satroot_federated_registry_collection_smoke
```

or:

```bash
satroot-federated-registry-collection-smoke
```

That one writes into `.tmp_federated_registry_collection_smoke_run/` by default, reruns the mixed-profile federation smoke, reuses the generated top-level `publication_registry_workspace_collection`, bootstraps a top-level publication-registry publication from that collection-backed preset, exports the generated publication back into a preset, and bootstraps the publication again to prove the collection-backed registry publication round trip.

There is also a packaged stable-profile smoke entrypoint:

```bash
python -m satroot_stable_profile_smoke
```

or:

```bash
satroot-stable-profile-smoke
```

And the machine-credit lane has the same packaged entrypoints:

```bash
python -m satroot_machine_profile_smoke
```

or:

```bash
satroot-machine-profile-smoke
```

The singleton receipt lane also has lower publication-ladder wrappers:

```bash
python scripts/run_receipt_demo_release_catalog_smoke.py
python scripts/run_receipt_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_receipt_demo_release_catalog_smoke
python -m satroot_receipt_demo_release_catalog_index_smoke
```

The singleton identity lane exposes the same local and packaged flows:

```bash
python scripts/run_identity_demo_release_catalog_smoke.py
python scripts/run_identity_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_identity_demo_release_catalog_smoke
python -m satroot_identity_demo_release_catalog_index_smoke
```

The singleton license lane exposes the same local and packaged flows:

```bash
python scripts/run_license_demo_release_catalog_smoke.py
python scripts/run_license_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_license_demo_release_catalog_smoke
python -m satroot_license_demo_release_catalog_index_smoke
```

And the stable and machine demo release-catalog operator lanes have packaged entrypoints too:

```bash
python -m satroot_stable_demo_release_catalog_smoke
python -m satroot_machine_demo_release_catalog_smoke
```

or:

```bash
satroot-stable-demo-release-catalog-smoke
satroot-machine-demo-release-catalog-smoke
```

And the matching index-layer operator lanes have packaged entrypoints too:

```bash
python -m satroot_stable_demo_release_catalog_index_smoke
python -m satroot_machine_demo_release_catalog_index_smoke
```

or:

```bash
satroot-stable-demo-release-catalog-index-smoke
satroot-machine-demo-release-catalog-index-smoke
```

The receipt lane has the same packaged entrypoints:

```bash
python -m satroot_receipt_profile_smoke
```

or:

```bash
satroot-receipt-profile-smoke
```

The identity lane has the same packaged entrypoints:

```bash
python -m satroot_identity_profile_smoke
```

or:

```bash
satroot-identity-profile-smoke
```

The license lane has the same packaged entrypoints:

```bash
python -m satroot_license_profile_smoke
```

or:

```bash
satroot-license-profile-smoke
```

The three chunked-runner forms (`scripts/run_pytest_chunked.py`, `python -m satroot_test`, `satroot-test`) collect from the full `tests/` tree by default.

You can also resume from a later point or reduce chunk size:

```bash
python scripts/run_pytest_chunked.py --chunk-size 50 --start 1001
```

or:

```bash
python -m satroot_test --chunk-size 50 --start 1001
```

or:

```bash
satroot-test --chunk-size 50 --start 1001
```

Current suite note:

```text
the tests/ tree is large enough that chunked execution is the preferred full-suite path
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

That stable demo bootstrap can also resolve its symbol, name, and profile defaults from a stable-only preset:

```bash
satroot1 bootstrap-stable-demo --preset-json examples/catalog_presets/stable_reference_catalog.json --output-dir stable_demo_preset
```

Generate a runnable SATROOT-MACHINE-1 machine-credit demo ledger:

```bash
satroot1 bootstrap-machine-demo --symbol APIDEMO2 --name "Machine CLI Demo" --service-scope inference-api --billing-unit token --output-dir machine_demo
```

That machine demo bootstrap can also resolve its symbol, name, and profile defaults from a machine-only preset:

```bash
satroot1 bootstrap-machine-demo --preset-json examples/catalog_presets/machine_compute_catalog.json --output-dir machine_demo_preset
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

If you want the reusable packaging layer just below releases for a single receipt, identity, or license profile, there is now a singleton wrapper that filters repeated demo presets down to one singleton profile, snapshots the generated bundles into a bundle collection, and writes a reusable bundle index in one step:

```bash
satroot1 bootstrap-singleton-demo-bundle-index --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --label "Receipt Bundle Index" --output-dir singleton_bundle_index
```

If you want the next packaging layer up, there is also a singleton release-collection wrapper that keeps one singleton profile from repeated presets and packages the generated releases into a reusable collection:

```bash
satroot1 bootstrap-singleton-demo-release-collection --profile SATROOT-LICENSE-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --label "License Release Collection" --output-dir singleton_release_collection
```

And if you want a signed catalog on top of those repeated singleton releases, the singleton release-catalog wrapper bootstraps the collection workspace and catalog publication together:

```bash
satroot1 bootstrap-singleton-demo-release-catalog-publication --profile SATROOT-IDENTITY-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --label "Identity Release Catalog" --output-dir singleton_release_catalog
```

And if you want the singleton lane all the way up at the top publication index layer, there is now a singleton release-catalog-index wrapper too:

```bash
satroot1 bootstrap-singleton-demo-release-catalog-index-publication --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --label "Receipt Release Catalog Index" --output-dir singleton_release_catalog_index
```

And if you want those repeated singleton presets to continue upward into the publication workspace lanes, there are now singleton publication-stack and publication-network wrappers as well:

```bash
satroot1 bootstrap-singleton-demo-publication-stack --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Receipt Publication Stack" --output-dir singleton_publication_stack
satroot1 bootstrap-singleton-demo-publication-network --profile SATROOT-IDENTITY-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Identity Publication Stack" --label "Identity Publication Network" --output-dir singleton_publication_network
```

And if you want the singleton lane to keep going through descriptor/metadata and top-level registry packaging, there are matching workspace wrappers there too:

```bash
satroot1 bootstrap-singleton-demo-publication-catalog-workspace --profile SATROOT-LICENSE-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --descriptor-index-label "License Workspace Descriptor Index" --publication-metadata-catalog-label "License Workspace Metadata Catalog" --output-dir singleton_publication_catalog_workspace
satroot1 bootstrap-singleton-demo-publication-registry-workspace --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --publication-registry-label "Receipt Publication Registry" --output-dir singleton_publication_registry_workspace
```

Once you have frozen one of those singleton release collections, the checked-in singleton registry-workspace and top-level registry presets in `examples/registry_workspace_presets/` and `examples/registry_presets/` can also be reused directly:

```bash
satroot1 bootstrap-singleton-demo-release-collection --profile SATROOT-RECEIPT-1 --preset-json examples/catalog_presets/receipt_invoice_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir examples/generated_receipt_release_collection_workspace
cp -r examples/generated_receipt_release_collection_workspace/release_collection examples/generated_receipt_release_collection
satroot1 bootstrap-demo-publication-network --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir generated_publication_network
satroot1 bootstrap-publication-network-collection generated_publication_network --output-dir generated_publication_network_collection
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir receipt_frozen_registry_workspace
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/receipt_invoice_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --key-id registry-key --output-dir receipt_frozen_registry
```

Generate a signed SATROOT-STABLE-1 reference-only demo bundle:

```bash
satroot1 bootstrap-stable-demo-bundle --symbol USDBUNDLE2 --name "Stable Bundle CLI" --scheme hmac-sha256 --reference-unit CHF --output-dir stable_bundle
```

That stable bundle bootstrap can also resolve its stable symbol, name, and profile defaults from a stable-only preset:

```bash
satroot1 bootstrap-stable-demo-bundle --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --output-dir stable_bundle_preset
```

For Ed25519 stable bundles, you can also emit a verifier-only variant that excludes `private_keys.json`:

```bash
satroot1 bootstrap-stable-demo-bundle --symbol USDEDCLI1 --name "Stable Bundle Ed25519" --scheme ed25519 --reference-unit AUD --output-dir stable_bundle_ed25519 --verifier-only
```

Generate a signed SATROOT-STABLE-1 demo bundle plus release directory:

```bash
satroot1 bootstrap-stable-demo-release --symbol USDRELCLI1 --name "Stable Release CLI" --scheme hmac-sha256 --release-key-id release-key --reference-unit JPY --channel stable --label "SATROOT Stable Release" --published-at 2026-06-27T12:00:00Z --output-dir stable_release
```

That stable release bootstrap can also inherit release metadata defaults from the same stable-only preset:

```bash
satroot1 bootstrap-stable-demo-release --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir stable_release_preset
```

If you want to generate multiple stable demo releases from one or more stable preset files and package them straight into a reusable release collection, repeat `--preset-json` for each member you want to generate:

```bash
satroot1 bootstrap-stable-demo-release-collection --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir stable_release_collection_workspace --label "SATROOT Stable Collection Override"
```

If you want the reusable packaging layer just below releases, there is also a stable wrapper that generates repeated bundles, snapshots them into a stable bundle collection, and writes a reusable bundle index in one step:

```bash
satroot1 bootstrap-stable-demo-bundle-index --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --label "Stable Demo Bundle Index" --output-dir stable_bundle_index_workspace
```

And if you want the next layer up in the same shot, there is a stable wrapper that generates those releases, snapshots the release collection, and bootstraps a signed release catalog publication:

```bash
satroot1 bootstrap-stable-demo-release-catalog-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Stable Collection Override" --label "Stable Demo Release Catalog" --output-dir stable_demo_release_catalog_publication
```

And if you want the next publication layer above that as well, there is a stable wrapper that continues on to a signed release catalog index publication:

```bash
satroot1 bootstrap-stable-demo-release-catalog-index-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Stable Demo Release Catalog" --label "Stable Demo Release Catalog Index" --output-dir stable_demo_release_catalog_index_publication
```

Generate a reusable SATROOT-STABLE-1 reference-only demo catalog workspace:

```bash
satroot1 bootstrap-stable-demo-catalog --symbol USDCATST1 --name "Stable Catalog CLI" --scheme hmac-sha256 --release-key-id release-key --reference-unit CHF --profile-field intended_use=treasury-credit --channel stable --label "SATROOT Stable Catalog" --published-at 2026-07-04T04:00:00Z --output-dir stable_catalog_workspace
```

That stable catalog bootstrap can also resolve its symbol, name, stable fields, and release metadata from a stable-only SATROOT demo-catalog preset:

```bash
satroot1 bootstrap-stable-demo-catalog --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir stable_catalog_workspace_preset --label "SATROOT Stable Catalog Override"
```

Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle:

```bash
satroot1 bootstrap-machine-demo-bundle --symbol APIBUNDLE2 --name "Machine Bundle CLI" --scheme hmac-sha256 --service-scope batch-jobs --output-dir machine_bundle
```

That bundle bootstrap can also resolve its machine symbol, name, and profile defaults from a machine-only preset:

```bash
satroot1 bootstrap-machine-demo-bundle --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --output-dir machine_bundle_preset
```

Generate a signed SATROOT-MACHINE-1 machine-credit demo bundle plus release directory:

```bash
satroot1 bootstrap-machine-demo-release --symbol APIRELCLI1 --name "Machine Release CLI" --scheme hmac-sha256 --release-key-id release-key --service-scope render-farm --channel stable --label "SATROOT Machine Release" --published-at 2026-06-28T06:00:00Z --output-dir machine_release
```

The release bootstrap can also merge machine ledger defaults and release metadata from the same machine-only preset:

```bash
satroot1 bootstrap-machine-demo-release --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir machine_release_preset --label "SATROOT Machine Release Override"
```

If you want to generate multiple machine demo releases from one or more machine preset files and package them straight into a reusable release collection, repeat `--preset-json` for each member you want to generate:

```bash
satroot1 bootstrap-machine-demo-release-collection --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir machine_release_collection_workspace --label "SATROOT Machine Collection Override"
```

If you want the reusable packaging layer just below releases, there is also a machine wrapper that generates repeated bundles, snapshots them into a machine bundle collection, and writes a reusable bundle index in one step:

```bash
satroot1 bootstrap-machine-demo-bundle-index --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --label "Machine Demo Bundle Index" --output-dir machine_bundle_index_workspace
```

And if you want the next layer up in the same shot, there is a machine wrapper that generates those releases, snapshots the release collection, and bootstraps a signed release catalog publication:

```bash
satroot1 bootstrap-machine-demo-release-catalog-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Machine Collection Override" --label "Machine Demo Release Catalog" --output-dir machine_demo_release_catalog_publication
```

And if you want the next publication layer above that as well, there is a machine wrapper that continues on to a signed release catalog index publication:

```bash
satroot1 bootstrap-machine-demo-release-catalog-index-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Machine Demo Release Catalog" --label "Machine Demo Release Catalog Index" --output-dir machine_demo_release_catalog_index_publication
```

If you want the reusable packaging layer directly at the mixed-profile bundle level, there is also a generic wrapper that generates repeated preset-based bundles, snapshots them into one bundle collection, and writes a reusable top-level bundle index:

```bash
satroot1 bootstrap-demo-bundle-index --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --label "SATROOT Demo Bundle Index" --output-dir demo_bundle_index_workspace
```

Generate a reusable SATROOT-MACHINE-1 machine-credit demo catalog workspace:

```bash
satroot1 bootstrap-machine-demo-catalog --symbol APICAT1 --name "Machine Catalog CLI" --scheme hmac-sha256 --release-key-id release-key --service-scope batch-inference --billing-unit job --profile-field intended_use=cluster-credit --channel stable --label "SATROOT Machine Catalog" --published-at 2026-07-03T04:00:00Z --output-dir machine_catalog_workspace
```

That machine catalog bootstrap can also resolve its symbol, name, machine fields, and release metadata from a machine-only SATROOT demo-catalog preset:

```bash
satroot1 bootstrap-machine-demo-catalog --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir machine_catalog_workspace_preset --label "SATROOT Machine Catalog Override"
```

If you already have multiple machine-credit release directories and want a machine-validated signed catalog without stepping up into the publication stack yet:

```bash
satroot1 bootstrap-machine-release-catalog-publication machine_release_alpha/release_manifest.json machine_release_beta/bundle_index.json --output-dir machine_release_catalog --channel machine --label "SATROOT Machine Release Catalog" --published-at 2026-07-04T03:00:00Z --scheme hmac-sha256 --key-id catalog-key
```

For the stable-only lane, there is now a matching SATROOT-STABLE-1 wrapper:

```bash
satroot1 bootstrap-stable-release-catalog-publication stable_release_alpha/release_manifest.json stable_release_beta/bundle_index.json --output-dir stable_release_catalog --channel stable --label "SATROOT Stable Release Catalog" --published-at 2026-07-15T03:00:00Z --scheme hmac-sha256 --key-id catalog-key
```

And if you already manage signing material yourself, there is a matching publish wrapper that rejects any non-machine release inputs:

```bash
satroot1 publish-machine-release-catalog machine_release_alpha machine_release_beta --output-dir machine_release_catalog --channel machine --label "SATROOT Machine Release Catalog" --published-at 2026-07-04T03:00:00Z --scheme hmac-sha256 --key-id catalog-key --secrets-json release_hmac/release_secrets.json
```

The stable-only lane now has the same publish wrapper with SATROOT-STABLE-1 validation:

```bash
satroot1 publish-stable-release-catalog stable_release_alpha stable_release_beta --output-dir stable_release_catalog --channel stable --label "SATROOT Stable Release Catalog" --published-at 2026-07-15T03:00:00Z --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret
```

If you only want the unsigned JSON catalog first, there is also a machine-validated build-only variant:

```bash
satroot1 build-machine-release-catalog machine_release_alpha machine_release_beta/release_manifest.json --channel machine --label "SATROOT Machine Release Catalog" --published-at 2026-07-04T03:00:00Z --output machine_release_catalog.json
```

```bash
satroot1 build-stable-release-catalog stable_release_alpha stable_release_beta/release_manifest.json --channel stable --label "SATROOT Stable Release Catalog" --published-at 2026-07-15T03:45:00Z --output stable_release_catalog.json
```

And if you want to sign that unsigned machine catalog separately, the manifest step has a matching machine-only guard as well:

```bash
satroot1 build-machine-release-catalog-manifest machine_release_catalog.json --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret --output machine_release_catalog_manifest.json
```

```bash
satroot1 build-stable-release-catalog-manifest stable_release_catalog.json --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret --output stable_release_catalog_manifest.json
```

To publish a higher-level machine-only index across multiple machine release catalogs, there is now a matching machine wrapper at the release-catalog-index layer:

```bash
satroot1 bootstrap-machine-release-catalog-index-publication machine_release_catalog_alpha/release_catalog.json machine_release_catalog_beta/release_catalog_manifest.json --output-dir machine_release_catalog_index --channel machine --label "SATROOT Machine Catalog Network" --published-at 2026-07-04T06:00:00Z --scheme hmac-sha256 --key-id index-key
```

The stable-only lane has the same convenience wrapper for SATROOT-STABLE-1 release catalogs:

```bash
satroot1 bootstrap-stable-release-catalog-index-publication stable_release_catalog_alpha/release_catalog.json stable_release_catalog_beta/release_catalog_manifest.json --output-dir stable_release_catalog_index --channel stable --label "SATROOT Stable Catalog Network" --published-at 2026-07-15T06:00:00Z --scheme hmac-sha256 --key-id index-key
```

And the publish variant likewise rejects any non-machine release catalog inputs:

```bash
satroot1 publish-machine-release-catalog-index machine_release_catalog_alpha machine_release_catalog_beta --output-dir machine_release_catalog_index --channel machine --label "SATROOT Machine Catalog Network" --published-at 2026-07-04T06:00:00Z --scheme hmac-sha256 --key-id index-key --secrets-json release_hmac/release_secrets.json
```

```bash
satroot1 publish-stable-release-catalog-index stable_release_catalog_alpha stable_release_catalog_beta --output-dir stable_release_catalog_index --channel stable --label "SATROOT Stable Catalog Network" --published-at 2026-07-15T06:00:00Z --scheme hmac-sha256 --key-id index-key --secret index-secret
```

There is also a matching unsigned machine-only builder for the index JSON:

```bash
satroot1 build-machine-release-catalog-index machine_release_catalog_alpha machine_release_catalog_beta/release_catalog_manifest.json --channel machine --label "SATROOT Machine Catalog Network" --published-at 2026-07-04T06:00:00Z --output machine_release_catalog_index.json
```

```bash
satroot1 build-stable-release-catalog-index stable_release_catalog_alpha stable_release_catalog_beta/release_catalog_manifest.json --channel stable --label "SATROOT Stable Catalog Network" --published-at 2026-07-15T06:45:00Z --output stable_release_catalog_index.json
```

And the top-level machine catalog index can be signed the same way with machine-only validation preserved:

```bash
satroot1 build-machine-release-catalog-index-manifest machine_release_catalog_index.json --scheme hmac-sha256 --key-id index-key --secret index-secret --output machine_release_catalog_index_manifest.json
```

```bash
satroot1 build-stable-release-catalog-index-manifest stable_release_catalog_index.json --scheme hmac-sha256 --key-id index-key --secret index-secret --output stable_release_catalog_index_manifest.json
```

Generate a reusable SATROOT-STABLE-1 publication catalog workspace directly from stable-profile inputs:

```bash
satroot1 bootstrap-stable-publication-catalog-workspace --symbol STBPUBCAT1 --name "Stable Publication Catalog CLI" --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --intended-use merchant-clearing --channel stable --label "SATROOT Stable Catalog" --descriptor-index-label "Stable Descriptor Index" --publication-metadata-catalog-label "Stable Metadata Catalog" --output-dir stable_publication_catalog_workspace
```

The same wrapper can also layer a stable-only demo-catalog preset with a generic publication-catalog-workspace preset:

```bash
satroot1 bootstrap-stable-publication-catalog-workspace --catalog-preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir stable_publication_catalog_workspace_preset --publication-metadata-catalog-label "SATROOT Stable Metadata Catalog Override"
```

Generate a reusable SATROOT-STABLE-1 publication registry workspace directly from stable-profile inputs plus a stable publication network source:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --publication-network-dir stable_publication_network --symbol STBPUBREG1 --name "Stable Publication Registry CLI" --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --intended-use merchant-clearing --channel stable --label "SATROOT Stable Catalog" --descriptor-index-label "Stable Descriptor Index" --publication-metadata-catalog-label "Stable Metadata Catalog" --publication-registry-label "Stable Publication Registry" --output-dir stable_publication_registry_workspace
```

That registry wrapper can also compose the stable catalog preset, a publication-catalog-workspace preset, and a publication-registry-workspace preset:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --catalog-preset-json examples/catalog_presets/stable_reference_catalog.json --publication-catalog-workspace-preset-json examples/publication_catalog_workspace_presets/stable_reference_publication_catalog_workspace.json --preset-json examples/registry_workspace_presets/stable_reference_publication_registry_workspace.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_preset --publication-registry-label "SATROOT Stable Registry Override"
```

If the nested stable catalog comes from a frozen one-release collection, that same command can skip `--release-key-id` unless `--publication-network-preset-json` is generating a nested network. A self-contained registry-workspace preset can now carry that nested stable catalog preset for you:

```bash
satroot1 bootstrap-stable-publication-registry-workspace --preset-json examples/registry_workspace_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_frozen_catalog
```

Generate a reusable SATROOT-MACHINE-1 publication catalog workspace directly from machine-profile inputs:

```bash
satroot1 bootstrap-machine-publication-catalog-workspace --symbol APIPUBCAT1 --name "Machine Publication Catalog CLI" --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --service-scope batch-inference --billing-unit job --profile-field intended_use=cluster-credit --channel stable --label "SATROOT Machine Catalog" --descriptor-index-label "Machine Descriptor Index" --publication-metadata-catalog-label "Machine Metadata Catalog" --output-dir machine_publication_catalog_workspace
```

The same wrapper can also layer a machine-only demo-catalog preset with a generic publication-catalog-workspace preset:

```bash
satroot1 bootstrap-machine-publication-catalog-workspace --catalog-preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir machine_publication_catalog_workspace_preset --publication-metadata-catalog-label "SATROOT Machine Metadata Catalog Override"
```

Generate a reusable SATROOT-MACHINE-1 publication registry workspace directly from machine-profile inputs plus a publication network source:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --publication-network-dir publication_network --symbol APIPUBREG1 --name "Machine Publication Registry CLI" --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --service-scope batch-inference --billing-unit job --profile-field intended_use=cluster-credit --channel stable --label "SATROOT Machine Catalog" --descriptor-index-label "Machine Descriptor Index" --publication-metadata-catalog-label "Machine Metadata Catalog" --publication-registry-label "Machine Publication Registry" --output-dir machine_publication_registry_workspace
```

That registry wrapper can also compose the machine catalog preset, a publication-catalog-workspace preset, and a publication-registry-workspace preset:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --catalog-preset-json examples/catalog_presets/machine_compute_catalog.json --publication-catalog-workspace-preset-json examples/publication_catalog_workspace_presets/machine_compute_publication_catalog_workspace.json --preset-json examples/registry_workspace_presets/machine_compute_publication_registry_workspace.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_preset --publication-registry-label "SATROOT Machine Registry Override"
```

If the nested machine catalog comes from a frozen one-release collection, that same command can skip `--release-key-id` unless `--publication-network-preset-json` is generating a nested network. A self-contained registry-workspace preset can now carry that nested machine catalog preset for you:

```bash
satroot1 bootstrap-machine-publication-registry-workspace --preset-json examples/registry_workspace_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_frozen_catalog
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

For higher-level mixed-profile release packaging, the generic lane can also generate repeated releases directly from repeated demo-catalog presets and snapshot them into one reusable release collection:

```bash
satroot1 bootstrap-demo-release-collection --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir demo_release_collection_workspace --label "SATROOT Demo Collection Override"
```

That same repeated-preset mixed-profile lane can bootstrap a signed release catalog publication in one step:

```bash
satroot1 bootstrap-demo-release-catalog-publication --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "SATROOT Demo Collection Override" --label "SATROOT Demo Release Catalog" --output-dir demo_release_catalog_publication
```

And one layer higher, it can bootstrap a signed release catalog index publication without separately invoking the collection or catalog steps:

```bash
satroot1 bootstrap-demo-release-catalog-index-publication --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/ai_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "SATROOT Demo Release Catalog" --label "SATROOT Demo Release Catalog Index" --output-dir demo_release_catalog_index_publication
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

If the source bundles should remain strictly inside the SATROOT-MACHINE-1 lane, the machine-only wrapper rejects any non-machine bundle before writing the unsigned index:

```bash
satroot1 build-machine-bundle-index machine_bundle_alpha machine_bundle_beta --channel machine --label "SATROOT Machine Bundle Index" --published-at 2026-07-14T02:00:00Z --output machine_bundle_index.json
```

The stable-only lane now has the same guard for SATROOT-STABLE-1 bundle collections:

```bash
satroot1 build-stable-bundle-index stable_bundle_alpha stable_bundle_beta --channel stable --label "SATROOT Stable Bundle Index" --published-at 2026-07-15T02:00:00Z --output stable_bundle_index.json
```

Or drive the same bundle discovery and release metadata defaults from a preset:

```bash
satroot1 build-bundle-index --preset-json examples/bundle_index_presets/ai_compute_bundle_index.json --output bundle_index.json
```

Or discover bundle directories recursively under a parent artifacts folder:

```bash
satroot1 build-bundle-index --discover-under generated_artifacts --output bundle_index.json
```

If you want to scan first and then reuse the discovered bundle set deterministically, `inventory-artifacts` output can also feed that same build step:

```bash
satroot1 inventory-artifacts generated_artifacts > artifact_inventory.json
satroot1 build-bundle-index --inventory-json artifact_inventory.json --output bundle_index.json
```

For a reusable lower-layer capture, you can also copy signed bundles into a checked-in collection and then point bundle-index or release commands at that collection directly:

```bash
satroot1 bootstrap-bundle-collection signed_hmac_bundle machine_bundle --output-dir bundle_collection
satroot1 build-bundle-index --bundle-collection-dir bundle_collection --channel stable --label "Collection Bundle Index" --output bundle_index.json
```

Attach lightweight release metadata to a bundle index:

```bash
satroot1 build-bundle-index signed_hmac_bundle --channel stable --label "SATROOT FLOOR1 Demo" --published-at 2026-06-22T12:00:00Z --output bundle_index.json
```

Inspect that unsigned bundle index before signing it into a release:

```bash
satroot1 bundle-index-summary bundle_index.json
```

Lint the unsigned bundle index and its referenced nested manifests without needing a release manifest first:

```bash
satroot1 bundle-index-lint bundle_index.json
```

Build a signed release manifest from a bundle index:

```bash
satroot1 build-release-manifest bundle_index.json --scheme hmac-sha256 --key-id release-key --secret release-secret --output release_manifest.json
```

If that unsigned bundle index should remain machine-only, the matching manifest wrapper validates every referenced nested bundle before signing:

```bash
satroot1 build-machine-release-manifest machine_bundle_index.json --scheme hmac-sha256 --key-id release-key --secret release-secret --output machine_release_manifest.json
```

The stable-only lane now has a matching manifest wrapper that rejects any non-stable nested bundle:

```bash
satroot1 build-stable-release-manifest stable_bundle_index.json --scheme hmac-sha256 --key-id release-key --secret release-secret --output stable_release_manifest.json
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

For the machine-only release lane, `publish-machine-release` and `bootstrap-machine-release-publication` give the same convenience flow while enforcing SATROOT-MACHINE-1 bundle inputs:

```bash
satroot1 publish-machine-release machine_bundle_alpha machine_bundle_beta --output-dir machine_release --channel machine --label "SATROOT Machine Release" --published-at 2026-07-14T03:00:00Z --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

Those bundle-index and release commands can also take the root directory produced by `bootstrap-machine-demo-release` or `bootstrap-stable-demo-release`; SATROOT will automatically reuse the nested `bundle/` directory.

```bash
satroot1 bootstrap-machine-release-publication machine_bundle_alpha machine_bundle_beta --output-dir machine_release_bootstrap --channel machine --label "SATROOT Machine Release" --published-at 2026-07-14T03:00:00Z --scheme hmac-sha256 --key-id release-key
```

The stable-only lane now has matching release wrappers with SATROOT-STABLE-1 bundle validation preserved:

```bash
satroot1 publish-stable-release stable_bundle_alpha stable_bundle_beta --output-dir stable_release --channel stable --label "SATROOT Stable Release" --published-at 2026-07-15T03:00:00Z --scheme hmac-sha256 --key-id release-key --secret release-secret
```

```bash
satroot1 bootstrap-stable-release-publication stable_bundle_alpha stable_bundle_beta --output-dir stable_release_bootstrap --channel stable --label "SATROOT Stable Release" --published-at 2026-07-15T03:00:00Z --scheme hmac-sha256 --key-id release-key
```

That same release flow can also discover multiple bundle directories under a parent workspace:

```bash
satroot1 publish-release --discover-under generated_artifacts --output-dir catalog_release --channel stable --label "SATROOT Multi Bundle Demo" --published-at 2026-06-28T18:00:00Z --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

Or reuse a previously saved inventory report instead of repeating the directory scan:

```bash
satroot1 publish-release --inventory-json artifact_inventory.json --output-dir catalog_release --channel stable --label "SATROOT Multi Bundle Demo" --published-at 2026-06-28T18:00:00Z --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

And that same bundle discovery plus release metadata can come from the bundle-index preset:

```bash
satroot1 publish-release --preset-json examples/bundle_index_presets/ai_compute_bundle_index.json --output-dir catalog_release --scheme hmac-sha256 --key-id release-key --secrets-json release_hmac/release_secrets.json
```

Bootstrap release signing material and publish a ready-to-verify release directory in one step:

```bash
satroot1 bootstrap-release-publication starter_bundle --output-dir release_bootstrap --channel stable --label "SATROOT Starter Release" --published-at 2026-06-26T12:00:00Z --scheme hmac-sha256 --key-id release-key
```

For catalog-style packaging, you can point that bootstrap flow at a parent directory and let it discover nested bundles automatically:

```bash
satroot1 bootstrap-release-publication --discover-under generated_artifacts --output-dir catalog_bootstrap --channel stable --label "SATROOT Catalog Release" --published-at 2026-06-28T19:00:00Z --scheme hmac-sha256 --key-id release-key
```

That bootstrap path also accepts the same bundle-index preset:

```bash
satroot1 bootstrap-release-publication --preset-json examples/bundle_index_presets/ai_compute_bundle_index.json --output-dir catalog_bootstrap --scheme hmac-sha256 --key-id release-key
```

Build a higher-level release catalog from multiple signed release directories:

```bash
satroot1 build-release-catalog stable_release machine_release --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --output release_catalog.json
```

That catalog build can also harvest the `release_dir` entries from a saved inventory report:

```bash
satroot1 build-release-catalog --inventory-json artifact_inventory.json --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --output release_catalog.json
```

For reusable multi-release packaging, you can snapshot signed releases into a release collection and point the catalog layer at that saved set:

```bash
satroot1 bootstrap-release-collection stable_release machine_release --output-dir release_collection
satroot1 build-release-catalog --release-collection-dir release_collection --channel stable --label "Collection Release Catalog" --output release_catalog.json
```

The stable and machine lanes now also have one-shot wrappers that generate multiple preset-backed demo release workspaces and then snapshot them into the same reusable release-collection shape:

```bash
satroot1 bootstrap-stable-demo-release-collection --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir stable_release_collection_workspace --label "SATROOT Stable Collection Override"
satroot1 bootstrap-machine-demo-release-collection --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --output-dir machine_release_collection_workspace --label "SATROOT Machine Collection Override"
```

If you also want to bootstrap the signed release catalog publication immediately on top of those generated release collections, there are matching one-shot wrappers for that layer too:

```bash
satroot1 bootstrap-stable-demo-release-catalog-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Stable Collection Override" --label "Stable Demo Release Catalog" --output-dir stable_demo_release_catalog_publication
satroot1 bootstrap-machine-demo-release-catalog-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --scheme hmac-sha256 --key-id catalog-key --release-label "Machine Collection Override" --label "Machine Demo Release Catalog" --output-dir machine_demo_release_catalog_publication
```

There are now matching one-shot wrappers for the next layer as well, so the same repeated demo presets can flow all the way up into a signed release catalog index publication:

```bash
satroot1 bootstrap-stable-demo-release-catalog-index-publication --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Stable Demo Release Catalog" --label "Stable Demo Release Catalog Index" --output-dir stable_demo_release_catalog_index_publication
satroot1 bootstrap-machine-demo-release-catalog-index-publication --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --bundle-scheme hmac-sha256 --release-key-id release-key --catalog-scheme hmac-sha256 --catalog-key-id catalog-key --scheme hmac-sha256 --key-id index-key --catalog-label "Machine Demo Release Catalog" --label "Machine Demo Release Catalog Index" --output-dir machine_demo_release_catalog_index_publication
```

That same repeated-preset pattern now extends through the publication stack and publication network layers too:

```bash
satroot1 bootstrap-demo-publication-stack --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "SATROOT Demo Publication Stack" --output-dir demo_publication_stack
satroot1 bootstrap-demo-publication-network --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "SATROOT Demo Publication Stack" --label "SATROOT Demo Publication Network" --output-dir demo_publication_network
satroot1 bootstrap-singleton-demo-publication-stack --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Singleton Receipt Publication Stack" --output-dir singleton_demo_publication_stack
satroot1 bootstrap-singleton-demo-publication-network --profile SATROOT-IDENTITY-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Singleton Identity Publication Stack" --label "Singleton Identity Publication Network" --output-dir singleton_demo_publication_network
satroot1 bootstrap-singleton-demo-publication-catalog-workspace --profile SATROOT-LICENSE-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --descriptor-index-label "Singleton License Workspace Descriptor Index" --publication-metadata-catalog-label "Singleton License Workspace Metadata Catalog" --output-dir singleton_demo_publication_catalog_workspace
satroot1 bootstrap-singleton-demo-publication-registry-workspace --profile SATROOT-RECEIPT-1 --preset-json singleton_alpha.json --preset-json singleton_beta.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --publication-registry-label "Singleton Receipt Publication Registry" --output-dir singleton_demo_publication_registry_workspace
satroot1 bootstrap-stable-demo-publication-stack --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Stable Demo Publication Stack" --output-dir stable_demo_publication_stack
satroot1 bootstrap-machine-demo-publication-stack --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --label "Machine Demo Publication Stack" --output-dir machine_demo_publication_stack
satroot1 bootstrap-stable-demo-publication-network --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Stable Demo Publication Stack" --label "Stable Demo Publication Network" --output-dir stable_demo_publication_network
satroot1 bootstrap-machine-demo-publication-network --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --catalog-label "Machine Demo Publication Stack" --label "Machine Demo Publication Network" --output-dir machine_demo_publication_network
```

And the same repeated demo presets can now feed directly into reusable publication catalog workspaces as well:

```bash
satroot1 bootstrap-demo-publication-catalog-workspace --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "SATROOT Demo Catalog Release Override" --descriptor-index-label "SATROOT Demo Workspace Descriptor Index" --publication-metadata-catalog-label "SATROOT Demo Workspace Metadata Catalog" --output-dir demo_publication_catalog_workspace
satroot1 bootstrap-stable-demo-publication-catalog-workspace --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "Stable Demo Catalog Release Override" --descriptor-index-label "Stable Demo Workspace Descriptor Index" --publication-metadata-catalog-label "Stable Demo Workspace Metadata Catalog" --output-dir stable_demo_publication_catalog_workspace
satroot1 bootstrap-machine-demo-publication-catalog-workspace --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --release-label "Machine Demo Catalog Release Override" --descriptor-index-label "Machine Demo Workspace Descriptor Index" --publication-metadata-catalog-label "Machine Demo Workspace Metadata Catalog" --output-dir machine_demo_publication_catalog_workspace
```

And that same repeated-preset path now reaches the registry workspace layer too:

```bash
satroot1 bootstrap-demo-publication-registry-workspace --preset-json examples/catalog_presets/ai_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "SATROOT Demo Registry Release Override" --release-catalog-label "SATROOT Demo Registry Publication Stack" --release-catalog-index-label "SATROOT Demo Registry Publication Network" --descriptor-index-label "SATROOT Demo Registry Descriptor Index" --publication-metadata-catalog-label "SATROOT Demo Registry Metadata Catalog" --publication-registry-label "SATROOT Demo Publication Registry" --output-dir demo_publication_registry_workspace
satroot1 bootstrap-stable-demo-publication-registry-workspace --preset-json examples/catalog_presets/stable_reference_catalog.json --preset-json examples/catalog_presets/stable_reference_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "Stable Demo Registry Release Override" --release-catalog-label "Stable Demo Registry Publication Stack" --release-catalog-index-label "Stable Demo Registry Publication Network" --descriptor-index-label "Stable Demo Registry Descriptor Index" --publication-metadata-catalog-label "Stable Demo Registry Metadata Catalog" --publication-registry-label "Stable Demo Publication Registry" --output-dir stable_demo_publication_registry_workspace
satroot1 bootstrap-machine-demo-publication-registry-workspace --preset-json examples/catalog_presets/machine_compute_catalog.json --preset-json examples/catalog_presets/machine_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --release-label "Machine Demo Registry Release Override" --release-catalog-label "Machine Demo Registry Publication Stack" --release-catalog-index-label "Machine Demo Registry Publication Network" --descriptor-index-label "Machine Demo Registry Descriptor Index" --publication-metadata-catalog-label "Machine Demo Registry Metadata Catalog" --publication-registry-label "Machine Demo Publication Registry" --output-dir machine_demo_publication_registry_workspace
```

Those release-catalog flows also accept the generated release files directly, so you can mix `release_manifest.json` and `bundle_index.json` inputs when that is what you already have on hand:

```bash
satroot1 bootstrap-release-catalog-publication stable_release/bundle_index.json machine_release/release_manifest.json --output-dir release_catalog_bootstrap --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --scheme hmac-sha256 --key-id catalog-key
```

Publish a signed release catalog directory in one step:

```bash
satroot1 publish-release-catalog stable_release machine_release --output-dir release_catalog_pub --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --scheme hmac-sha256 --key-id catalog-key --secrets-json release_hmac/release_secrets.json
```

Or bootstrap fresh signing material for that release catalog publication:

```bash
satroot1 bootstrap-release-catalog-publication stable_release machine_release --output-dir release_catalog_bootstrap --channel stable --label "SATROOT Release Catalog" --published-at 2026-06-30T05:00:00Z --scheme hmac-sha256 --key-id catalog-key
```

Those lower release commands also accept `--bundle-collection-dir`, so the same saved bundle set can drive both `publish-release` and `bootstrap-release-publication` without repeating discovery flags or long bundle lists.

At the next layer up, `build-release-catalog`, `publish-release-catalog`, and `bootstrap-release-catalog-publication` also accept `--release-collection-dir`, including the machine and stable wrappers, so the same saved release set can be reused without repeating release discovery or long release lists.

They also accept generated demo-catalog workspace roots, or a workspace `summary.json`, and automatically reuse the nested `release/` directory when you point them at those generated artifacts directly.

For repeatable multi-release packaging, the release-catalog commands can also load a checked-in preset file and still accept CLI overrides on top:

```bash
satroot1 bootstrap-release-catalog-publication --preset-json examples/release_catalog_presets/ai_compute_release_stack.json --output-dir release_catalog_bootstrap --label "SATROOT AI Compute Release Stack Override" --scheme hmac-sha256 --key-id catalog-key
```

For a higher-level network of signed release catalogs, you can build and publish a release-catalog index the same way:

```bash
satroot1 build-release-catalog-index release_catalog_bootstrap another_release_catalog --channel network --label "SATROOT Catalog Network" --published-at 2026-07-02T05:00:00Z --output release_catalog_index.json
satroot1 bootstrap-release-catalog-index-publication --preset-json examples/release_catalog_index_presets/ai_compute_catalog_network.json --output-dir release_catalog_index_bootstrap --label "SATROOT AI Compute Catalog Network Override" --scheme hmac-sha256 --key-id index-key
```

Saved inventory reports work at that layer too, using the discovered `release_catalog_dir` entries:

```bash
satroot1 build-release-catalog-index --inventory-json artifact_inventory.json --channel network --label "SATROOT Catalog Network" --published-at 2026-07-02T05:00:00Z --output release_catalog_index.json
```

For reusable higher-level packaging, you can also snapshot signed release catalogs into a release-catalog collection and point the index layer at that saved set:

```bash
satroot1 bootstrap-release-catalog-collection release_catalog_bootstrap another_release_catalog --output-dir release_catalog_collection
satroot1 build-release-catalog-index --release-catalog-collection-dir release_catalog_collection --channel network --label "Collection Catalog Network" --output release_catalog_index.json
```

That higher-level index lane likewise accepts either the signed catalog directory or the generated `release_catalog.json` / `release_catalog_manifest.json` files:

```bash
satroot1 bootstrap-release-catalog-index-publication release_catalog_bootstrap/release_catalog.json another_release_catalog/release_catalog_manifest.json --output-dir release_catalog_index_bootstrap --channel network --label "SATROOT Catalog Network" --published-at 2026-07-02T05:00:00Z --scheme hmac-sha256 --key-id index-key
```

Those release-catalog-index commands also accept `--release-catalog-collection-dir`, including the machine and stable wrappers, so the same saved catalog set can drive `build-release-catalog-index`, `publish-release-catalog-index`, and `bootstrap-release-catalog-index-publication` without repeating catalog discovery or long catalog lists.

They likewise accept publication-stack workspace roots, or a stack `summary.json`, and automatically reuse the nested `release_catalog/` directory.

For a single end-to-end workspace, `bootstrap-publication-stack` can take multiple demo-catalog presets plus an optional release-catalog preset and emit catalog workspaces and a top-level release catalog in one shot:

```bash
satroot1 bootstrap-publication-stack --catalog-preset-json examples/catalog_presets/ai_compute_catalog.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-preset-json examples/release_catalog_presets/ai_compute_release_stack.json --release-catalog-key-id catalog-key --output-dir publication_stack --label "SATROOT Stack Override"
```

If you want the whole stack described in one checked-in file, `bootstrap-publication-stack` also accepts a dedicated stack preset:

```bash
satroot1 bootstrap-publication-stack --stack-preset-json examples/stack_presets/ai_compute_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir publication_stack --label "SATROOT Stack Override"
```

For a machine-only lane on the same preset format, `bootstrap-machine-publication-stack` validates that every nested catalog preset resolves to `SATROOT-MACHINE-1` only:

```bash
satroot1 bootstrap-machine-publication-stack --stack-preset-json examples/stack_presets/machine_compute_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir machine_publication_stack --label "Machine Stack Override"
```

There is now a matching stable-only lane that validates every nested catalog preset resolves to `SATROOT-STABLE-1` only:

```bash
satroot1 bootstrap-stable-publication-stack --stack-preset-json examples/stack_presets/stable_reference_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir stable_publication_stack --label "Stable Stack Override"
```

That same stack preset shape can also point at a previously copied `catalog_workspace_collection_dir` when you want to reuse an already-frozen set of generated demo catalog workspaces. Exported stack presets preserve that collection reference even when they also emit nested catalog presets, so round-tripped preset trees keep provenance without making the collection itself the execution input.

There is now a checked-in collection-backed companion preset for that flow too:

```bash
satroot1 bootstrap-publication-stack --stack-preset-json examples/stack_presets/ai_compute_publication_stack_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --output-dir publication_stack_collection_backed --label "SATROOT Collection-Backed Stack Override"
```

To generate multiple stack workspaces and a top-level signed release-catalog index in one pass, use `bootstrap-publication-network` with one or more stack presets:

```bash
satroot1 bootstrap-publication-network --stack-preset-json examples/stack_presets/ai_compute_publication_stack.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-preset-json examples/release_catalog_index_presets/ai_compute_catalog_network.json --release-catalog-index-key-id index-key --output-dir publication_network --label "SATROOT Network Override"
```

If you want the whole network described in one checked-in file, `bootstrap-publication-network` also accepts a dedicated network preset:

```bash
satroot1 bootstrap-publication-network --network-preset-json examples/network_presets/ai_compute_publication_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir publication_network --label "SATROOT Network Override"
```

That same network preset shape can also point at a previously copied `publication_stack_collection_dir` when you want to reuse an already-frozen set of generated stack workspaces. Exported network presets preserve that collection reference even when they also emit nested stack presets, so round-tripped preset trees keep provenance without making the collection itself the execution input.

There is now a checked-in collection-backed companion preset for that flow too:

```bash
satroot1 bootstrap-publication-network --network-preset-json examples/network_presets/ai_compute_publication_network_collection_backed.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir publication_network_collection_backed --label "SATROOT Collection-Backed Network Override"
```

If you want to freeze already-generated publication networks for reuse one layer higher, there are matching collection commands there too:

```bash
satroot1 bootstrap-publication-network-collection publication_network_alpha publication_network_beta --output-dir publication_network_collection
```

There is also a machine-only convenience wrapper that validates every nested stack preset stays on the machine lane:

```bash
satroot1 bootstrap-machine-publication-network --network-preset-json examples/network_presets/machine_compute_publication_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir machine_publication_network --label "Machine Network Override"
```

And there is a stable-only wrapper that does the same for `SATROOT-STABLE-1` stack presets:

```bash
satroot1 bootstrap-stable-publication-network --network-preset-json examples/network_presets/stable_reference_publication_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --output-dir stable_publication_network --label "Stable Network Override"
```

If you already have generated demo catalog workspaces and just want to consolidate them into one signed publication stack, use `publish-publication-stack`:

```bash
satroot1 publish-publication-stack generated_catalogs/stable_workspace generated_catalogs/machine_workspace --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir publication_stack_from_existing --label "Published Existing Stack"
```

```bash
satroot1 publish-publication-stack --inventory-json artifact_inventory.json --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir publication_stack_from_existing --label "Inventory Published Stack"
```

```bash
satroot1 publish-publication-stack --catalog-workspace-collection-dir generated_catalog_workspace_collection --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir publication_stack_from_collection --label "Collection Published Stack"
```

That collection flag also accepts `generated_catalog_workspace_collection/summary.json` directly, and exported stack presets normalize the preserved provenance back to the collection root.

That same publish lane can now also load a stack preset that preserves source `catalog_workspace_dirs`, which makes exported stack presets reusable for both bootstrap and publish workflows:

```bash
satroot1 publish-publication-stack --preset-json exported_stack.json --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir publication_stack_from_preset --label "Published Stack From Preset"
```

A checked-in example of that publish-oriented preset shape lives at `examples/stack_presets/ai_compute_publication_stack_publish.json`.

For existing machine-only catalog workspaces, `publish-machine-publication-stack` applies the same publish flow but rejects any nested bundle set that is not purely `SATROOT-MACHINE-1`:

```bash
satroot1 publish-machine-publication-stack generated_machine_catalogs/catalog_alpha generated_machine_catalogs/catalog_beta --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir machine_publication_stack_from_existing --label "Published Machine Stack"
```

There is now a matching stable-only wrapper for existing `SATROOT-STABLE-1` catalog workspaces:

```bash
satroot1 publish-stable-publication-stack generated_stable_catalogs/catalog_alpha generated_stable_catalogs/catalog_beta --scheme hmac-sha256 --release-catalog-key-id catalog-key --output-dir stable_publication_stack_from_existing --label "Published Stable Stack"
```

If you want to freeze a reusable set of generated stack workspaces for later network assembly, use `bootstrap-publication-stack-collection`:

```bash
satroot1 bootstrap-publication-stack-collection generated_stacks/stack_alpha generated_stacks/stack_beta --output-dir publication_stack_collection
```

One layer lower, if you want to freeze a reusable set of generated demo catalog workspaces for later stack assembly, use `bootstrap-demo-catalog-workspace-collection`:

```bash
satroot1 bootstrap-demo-catalog-workspace-collection generated_catalogs/stable_workspace generated_catalogs/machine_workspace --output-dir generated_catalog_workspace_collection
```

Once you start deriving publication catalog workspaces themselves, you can freeze those higher-level descriptor-plus-metadata assemblies for later reuse with `bootstrap-publication-catalog-workspace-collection`:

```bash
satroot1 bootstrap-publication-catalog-workspace-collection generated_publication_catalogs/catalog_alpha generated_publication_catalogs/catalog_beta --output-dir publication_catalog_workspace_collection
```

At the top workspace layer, `bootstrap-publication-registry-workspace-collection` does the same for fully assembled registry workspaces when you want to preserve reusable end-to-end publication roots:

```bash
satroot1 bootstrap-publication-registry-workspace-collection generated_publication_registries/registry_alpha generated_publication_registries/registry_beta --output-dir publication_registry_workspace_collection
```

If you already have generated publication stack workspaces and want a top-level signed network without regenerating the nested stacks, use `publish-publication-network`:

```bash
satroot1 publish-publication-network generated_stacks/stack_alpha generated_stacks/stack_beta --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir publication_network_from_existing --label "Published Existing Network"
```

```bash
satroot1 publish-publication-network --inventory-json artifact_inventory.json --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir publication_network_from_existing --label "Inventory Published Network"
```

```bash
satroot1 publish-publication-network --publication-stack-collection-dir publication_stack_collection --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir publication_network_from_collection --label "Collection Published Network"
```

The `--publication-stack-collection-dir` flag likewise accepts `publication_stack_collection/summary.json`, while exported network presets continue to preserve the collection root rather than the summary file path.

And because exported network presets now preserve source `publication_stack_dirs`, the same checked-in preset can also drive a publish-only consolidation flow:

```bash
satroot1 publish-publication-network --preset-json exported_network.json --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir publication_network_from_preset --label "Published Network From Preset"
```

There is a matching checked-in example at `examples/network_presets/ai_compute_publication_network_publish.json`.

For existing machine-only stack workspaces, `publish-machine-publication-network` enforces the same SATROOT-MACHINE-1-only constraint across every nested catalog workspace:

```bash
satroot1 publish-machine-publication-network generated_machine_stacks/stack_alpha generated_machine_stacks/stack_beta --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir machine_publication_network_from_existing --label "Published Machine Network"
```

And there is now a stable-only wrapper for existing `SATROOT-STABLE-1` publication stack workspaces:

```bash
satroot1 publish-stable-publication-network generated_stable_stacks/stack_alpha generated_stable_stacks/stack_beta --scheme hmac-sha256 --release-catalog-index-key-id index-key --output-dir stable_publication_network_from_existing --label "Published Stable Network"
```

If you already have a publication descriptor index and matching publication metadata catalog publication, you can wrap them back into a reusable catalog workspace with `publish-publication-catalog-workspace`:

```bash
satroot1 publish-publication-catalog-workspace publication_descriptor_index publication_metadata_catalog --output-dir publication_catalog_workspace_from_existing
```

```bash
satroot1 publish-publication-catalog-workspace --inventory-json artifact_inventory.json --output-dir publication_catalog_workspace_from_existing
```

If those source publication directories already live in an exported publication-registry preset, the same command can load them directly:

```bash
satroot1 publish-publication-catalog-workspace --preset-json exported_registry.json --output-dir publication_catalog_workspace_from_preset
```

For a machine-only publication lane, `publish-machine-publication-catalog-workspace` looks for at least one nested demo-catalog descriptor whose `bundle_profiles` are entirely `SATROOT-MACHINE-1` and preserves that source machine workspace provenance in the published summary:

```bash
satroot1 publish-machine-publication-catalog-workspace machine_publication_descriptor_index machine_publication_metadata_catalog --output-dir machine_publication_catalog_workspace_from_existing
```

There is now a matching stable-only catalog wrapper that requires the descriptor and metadata lanes to resolve back to `SATROOT-STABLE-1` sources:

```bash
satroot1 publish-stable-publication-catalog-workspace stable_publication_descriptor_index stable_publication_metadata_catalog --output-dir stable_publication_catalog_workspace_from_existing
```

If you already have a publication catalog workspace and just want to bind it to a release-catalog-index source without regenerating the descriptor or metadata lanes, use `publish-publication-registry-workspace`:

```bash
satroot1 publish-publication-registry-workspace publication_catalog_workspace --publication-network-dir publication_network --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir publication_registry_workspace_from_existing --label "Published Existing Registry Workspace"
```

```bash
satroot1 publish-publication-registry-workspace --inventory-json artifact_inventory.json --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir publication_registry_workspace_from_existing --label "Inventory Published Registry Workspace"
```

```bash
satroot1 publish-publication-registry-workspace --publication-catalog-workspace-collection-dir publication_catalog_workspace_collection/summary.json --publication-network-collection-dir publication_network_collection/summary.json --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir publication_registry_workspace_from_collection --label "Collection Published Registry Workspace"
```

Both collection flags also accept the collection directory itself, and any later exported registry-workspace preset preserves the collection root rather than the nested `summary.json` path.

That publish wrapper can also load an exported registry-workspace preset for the source catalog workspace, optional network/index source, and publication-registry metadata defaults:

```bash
satroot1 publish-publication-registry-workspace --preset-json exported_registry_workspace.json --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir publication_registry_workspace_from_preset --label "Published Registry Workspace From Preset"
```

If that exported preset carries a nested `publication_network_preset` instead of a direct `publication_network_dir`, the publish wrapper can materialize the copied `publication_network/` for you as long as you also provide the nested release signing key ids:

```bash
satroot1 publish-publication-registry-workspace --preset-json exported_registry_workspace_with_network.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_from_nested_preset --label "Published Registry Workspace From Nested Preset"
```

If that source catalog workspace is machine-validated, `publish-machine-publication-registry-workspace` carries forward the machine publication catalog provenance as well:

```bash
satroot1 publish-machine-publication-registry-workspace machine_publication_catalog_workspace --publication-network-dir publication_network --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir machine_publication_registry_workspace_from_existing --label "Published Machine Registry Workspace"
```

And there is a stable-only companion that enforces stable catalog and release-catalog-index provenance before signing the top-level registry:

```bash
satroot1 publish-stable-publication-registry-workspace stable_publication_catalog_workspace --publication-network-dir stable_publication_network --scheme hmac-sha256 --publication-registry-key-id registry-key --output-dir stable_publication_registry_workspace_from_existing --label "Published Stable Registry Workspace"
```

To scan a generated tree and see which SATROOT bundles, releases, catalogs, indexes, registries, and workspaces are present, use `inventory-artifacts`:

```bash
satroot1 inventory-artifacts publication_network
```

If you only want to report artifacts rooted directly at the given path and skip nested directories, add `--non-recursive`:

```bash
satroot1 inventory-artifacts publication_network --non-recursive
```

Those saved inventory reports can be reused directly by `build-bundle-index`, `publish-release`, `bootstrap-release-publication`, `build-release-catalog`, `publish-release-catalog`, `bootstrap-release-catalog-publication`, `build-release-catalog-index`, `publish-release-catalog-index`, `bootstrap-release-catalog-index-publication`, `publish-publication-stack`, `publish-publication-network`, `publish-publication-catalog-workspace`, `publish-publication-registry-workspace`, `build-publication-descriptor-index`, `bootstrap-publication-descriptor-index-publication`, `build-publication-metadata-catalog`, `bootstrap-publication-metadata-catalog-publication`, `build-publication-registry`, `bootstrap-publication-registry-publication`, `bootstrap-publication-catalog-workspace`, and `bootstrap-publication-registry-workspace` via `--inventory-json`.

To derive a reusable preset back from a generated demo catalog workspace:

```bash
satroot1 export-demo-catalog-preset catalog_workspace --output exported_catalog.json
```

This export also accepts `catalog_workspace/summary.json` directly.

To derive a reusable bundle-index preset back from either a release directory or an existing `bundle_index.json`:

```bash
satroot1 export-bundle-index-preset release_bootstrap --output exported_bundle_index.json
```

That export also accepts `release_manifest.json` directly.

If that bundle index was originally built from `--bundle-collection-dir`, the exported preset now preserves that `bundle_collection_dir` reference instead of expanding back to explicit `bundle_dirs`.

To derive reusable presets back from higher-level signed catalog artifacts, either from the directory or the underlying JSON payload:

```bash
satroot1 export-release-catalog-preset publication_stack/release_catalog --output exported_release_catalog.json
satroot1 export-release-catalog-index-preset publication_network/release_catalog_index/release_catalog_index.json --output exported_release_catalog_index.json
```

The release catalog and release catalog index preset exports also accept their matching `*_manifest.json` files directly.

The machine-only release lanes have matching preset-export wrappers:

```bash
satroot1 export-machine-bundle-index-preset machine_release_bootstrap --output exported_machine_bundle_index.json
satroot1 export-machine-release-catalog-preset machine_release_catalog_alpha/release_catalog.json --output exported_machine_release_catalog.json
```

Those machine-only bundle-index exports also accept `release_manifest.json` directly, and the machine release-catalog export accepts `release_catalog_manifest.json`.

The stable-only release lanes now have matching preset-export wrappers too:

```bash
satroot1 export-stable-bundle-index-preset stable_release_bootstrap --output exported_stable_bundle_index.json
satroot1 export-stable-release-catalog-preset stable_release_catalog_alpha/release_catalog.json --output exported_stable_release_catalog.json
satroot1 export-stable-release-catalog-index-preset stable_release_catalog_index_publication --output exported_stable_release_catalog_index.json
```

The same manifest-backed shortcut works for the stable wrappers: `release_manifest.json`, `release_catalog_manifest.json`, and `release_catalog_index_manifest.json`.

The publication-registry and publication-index exports follow the same pattern, so you can point them at either the publication directory or the generated JSON payload:

```bash
satroot1 export-publication-registry-preset publication_registry_publication/publication_registry.json --output exported_registry.json
satroot1 export-publication-metadata-catalog-preset publication_metadata_catalog_publication --output exported_publication_metadata_catalog.json
satroot1 export-publication-descriptor-index-preset publication_descriptor_index_publication/publication_descriptor_index.json --output exported_publication_descriptor_index.json
```

Those publication-layer export commands also accept their matching manifest files directly: `publication_registry_manifest.json`, `publication_metadata_catalog_manifest.json`, and `publication_descriptor_index_manifest.json`.

To derive a publication stack preset and also emit nested demo catalog preset files alongside it:

```bash
satroot1 export-publication-stack-preset publication_stack --catalog-preset-dir exported_catalog_presets --output exported_stack.json
```

Every workspace-backed export command in this lane also accepts the workspace `summary.json` path instead of the workspace directory itself, so `publication_stack/summary.json` works here too.

Exported stack presets now also preserve source `catalog_workspace_dirs`, so the same preset can be fed back into `publish-publication-stack` without needing the nested demo-catalog preset files at runtime.

For a machine-only stack, there is a matching export wrapper that validates nested exported catalog presets stay on `SATROOT-MACHINE-1`:

```bash
satroot1 export-machine-publication-stack-preset machine_publication_stack --catalog-preset-dir exported_machine_catalog_presets --output exported_machine_stack.json
```

The stable-only stack lane now has the same export wrapper with `SATROOT-STABLE-1` validation:

```bash
satroot1 export-stable-publication-stack-preset stable_publication_stack --catalog-preset-dir exported_stable_catalog_presets --output exported_stable_stack.json
```

To derive a publication network preset and recursively emit nested stack and catalog preset files:

```bash
satroot1 export-publication-network-preset publication_network --stack-preset-dir exported_stack_presets --catalog-preset-dir exported_catalog_presets --output exported_network.json
```

The same export command also accepts `publication_network/summary.json` directly.

Those exported network presets also preserve source `publication_stack_dirs`, which makes them reusable for `publish-publication-network` in addition to the bootstrap lane.

And the machine-only network lane can be exported the same way while validating nested stack and catalog presets remain machine-only:

```bash
satroot1 export-machine-publication-network-preset machine_publication_network --stack-preset-dir exported_machine_stack_presets --catalog-preset-dir exported_machine_catalog_presets --output exported_machine_network.json
```

The stable-only network lane now has the same export wrapper for nested stable stack and catalog presets:

```bash
satroot1 export-stable-publication-network-preset stable_publication_network --stack-preset-dir exported_stable_stack_presets --catalog-preset-dir exported_stable_catalog_presets --output exported_stable_network.json
```

At the lower release layers, release catalog preset export can now also emit nested bundle-index presets while still preserving source `release_dirs` for publish/bootstrap reuse. When the signed catalog came from `--release-collection-dir`, the exported preset keeps that `release_collection_dir` provenance even if nested bundle-index presets are also emitted:

```bash
satroot1 export-release-catalog-preset release_catalog --bundle-index-preset-dir exported_bundle_index_presets --output exported_release_catalog.json
```

The machine-only and stable-only wrappers validate those nested bundle-index presets against `SATROOT-MACHINE-1` and `SATROOT-STABLE-1` respectively:

```bash
satroot1 export-machine-release-catalog-preset machine_release_catalog --bundle-index-preset-dir exported_machine_bundle_index_presets --output exported_machine_release_catalog.json
satroot1 export-stable-release-catalog-preset stable_release_catalog --bundle-index-preset-dir exported_stable_bundle_index_presets --output exported_stable_release_catalog.json
```

Release catalog index preset export can likewise emit nested release-catalog presets and, beneath those, nested bundle-index presets:

```bash
satroot1 export-release-catalog-index-preset release_catalog_index --release-catalog-preset-dir exported_release_catalog_presets --bundle-index-preset-dir exported_bundle_index_presets --output exported_release_catalog_index.json
```

Those top-level release catalog index presets still preserve source `release_catalog_dirs`, and collection-backed exports keep `release_catalog_collection_dir` even when nested release-catalog presets are emitted, so the nested preset tree remains an export-time convenience while the original collection provenance survives round-trip export.

To render a human-readable markdown report for a generated SATROOT artifact or workspace:

```bash
satroot1 render-publication-report publication_network
```

The report renderer auto-detects bundle, bundle-index, publication-metadata-bundle, release, release-catalog, release-catalog-index, publication-descriptor-index, publication-metadata-catalog, demo-catalog, publication-stack, publication-network, publication-catalog-workspace, publication-registry-workspace, and publication-registry inputs, and it can also write to a file:

```bash
satroot1 render-publication-report stable_release --output stable_release_report.md
```

For a normalized machine-readable export of the same detected artifact metadata, use `export-publication-descriptor`:

```bash
satroot1 export-publication-descriptor publication_network --output publication_network_descriptor.json
```

That same descriptor export path also accepts raw `bundle_index.json` inputs or directories that contain them:

```bash
satroot1 export-publication-descriptor bundle_index.json --output bundle_index_descriptor.json
```

Bootstrapped publication metadata bundles can also be inspected the same way:

```bash
satroot1 render-publication-report publication_metadata_bundle
```

To aggregate many detected artifacts into one descriptor registry, use `build-publication-descriptor-index`:

```bash
satroot1 build-publication-descriptor-index --discover-under publication_network --channel network --label "SATROOT Descriptor Index" --output publication_descriptor_index.json
```

If those discovered artifacts must stay fully inside the SATROOT-MACHINE-1 lane, the machine-only wrapper validates each nested artifact before writing the unsigned index:

```bash
satroot1 build-machine-publication-descriptor-index machine_publication_catalog_workspace machine_release_catalog_alpha --channel machine --label "Machine Descriptor Index" --published-at 2026-07-14T04:00:00Z --output machine_publication_descriptor_index.json
```

```bash
satroot1 build-stable-publication-descriptor-index stable_publication_catalog_workspace stable_release_catalog_alpha --channel stable --label "Stable Descriptor Index" --published-at 2026-07-15T04:00:00Z --output stable_publication_descriptor_index.json
```

If you already captured a deterministic artifact scan, that same descriptor-index build can replay it directly:

```bash
satroot1 build-publication-descriptor-index --inventory-json artifact_inventory.json --channel network --label "Inventory Descriptor Index" --published-at 2026-07-08T02:30:00Z --output publication_descriptor_index.json
```

To bootstrap signing material plus a ready-to-verify signed publication descriptor index:

```bash
satroot1 bootstrap-publication-descriptor-index-publication --discover-under publication_network --output-dir publication_descriptor_index_publication --channel network --label "SATROOT Descriptor Publication" --scheme hmac-sha256 --key-id descriptor-key
```

If you already have signer material and just want the signed publication directory, the publish convenience path writes the same `publication_descriptor_index.json` plus `publication_descriptor_index_manifest.json` layout without generating fresh secrets or keys:

```bash
satroot1 publish-publication-descriptor-index --discover-under publication_network --output-dir publication_descriptor_index_publication --channel network --label "SATROOT Descriptor Publication" --published-at 2026-07-09T02:00:00Z --scheme hmac-sha256 --key-id descriptor-key --secret descriptor-secret
```

That descriptor-index lane now also has matching machine-only manifest and bootstrap wrappers:

```bash
satroot1 build-machine-publication-descriptor-index-manifest machine_publication_descriptor_index.json --scheme hmac-sha256 --key-id descriptor-key --secret descriptor-secret --output machine_publication_descriptor_index_manifest.json
```

```bash
satroot1 build-stable-publication-descriptor-index-manifest stable_publication_descriptor_index.json --scheme hmac-sha256 --key-id descriptor-key --secret descriptor-secret --output stable_publication_descriptor_index_manifest.json
```

```bash
satroot1 bootstrap-machine-publication-descriptor-index-publication machine_publication_catalog_workspace --output-dir machine_publication_descriptor_index_publication --channel machine --label "Machine Descriptor Publication" --published-at 2026-07-14T04:30:00Z --scheme hmac-sha256 --key-id descriptor-key
```

```bash
satroot1 bootstrap-stable-publication-descriptor-index-publication stable_publication_catalog_workspace --output-dir stable_publication_descriptor_index_publication --channel stable --label "Stable Descriptor Publication" --published-at 2026-07-15T04:30:00Z --scheme hmac-sha256 --key-id descriptor-key
```

For repeatable descriptor-index packaging, that same command can also load a preset:

```bash
satroot1 bootstrap-publication-descriptor-index-publication --preset-json examples/publication_descriptor_index_presets/ai_compute_publication_descriptor_index.json --output-dir publication_descriptor_index_publication --label "SATROOT Descriptor Publication Override" --scheme hmac-sha256 --key-id descriptor-key
```

```bash
satroot1 bootstrap-machine-publication-descriptor-index-publication --preset-json examples/publication_descriptor_index_presets/ai_compute_publication_descriptor_index.json --output-dir machine_publication_descriptor_index_publication --label "SATROOT Machine Descriptor Publication Override" --scheme hmac-sha256 --key-id descriptor-key
```

Saved inventory reports can also drive the signed descriptor-index bootstrap directly:

```bash
satroot1 bootstrap-publication-descriptor-index-publication --inventory-json artifact_inventory.json --output-dir publication_descriptor_index_publication --channel network --label "Inventory Descriptor Publication" --published-at 2026-07-08T02:45:00Z --scheme hmac-sha256 --key-id descriptor-key
```

To bootstrap a signed publication report plus descriptor bundle for one artifact:

```bash
satroot1 bootstrap-publication-metadata-bundle publication_network --output-dir publication_metadata_bundle --scheme hmac-sha256 --key-id metadata-key
```

```bash
satroot1 publish-publication-metadata-bundle publication_network --output-dir publication_metadata_bundle --scheme hmac-sha256 --key-id metadata-key --secret metadata-secret
```

```bash
satroot1 build-publication-metadata-manifest publication_metadata_bundle/publication_report.md publication_metadata_bundle/publication_descriptor.json --scheme hmac-sha256 --key-id metadata-key --secret metadata-secret --output publication_metadata_manifest.json
```

To verify that bundle later:

```bash
satroot1 verify-publication-metadata-manifest publication_metadata_bundle/publication_metadata_manifest.json --secrets-json publication_metadata_bundle/publication_metadata_secrets.json
```

To aggregate multiple publication metadata bundles into one signed catalog:

```bash
satroot1 bootstrap-publication-metadata-catalog-publication --discover-under publication_metadata_root --output-dir publication_metadata_catalog_publication --channel network --label "SATROOT Metadata Catalog" --scheme hmac-sha256 --key-id catalog-key
```

```bash
satroot1 build-publication-metadata-catalog publication_metadata_bundle_alpha publication_metadata_bundle_beta --channel network --label "SATROOT Metadata Catalog" --published-at 2026-07-08T04:00:00Z --output publication_metadata_catalog.json
```

```bash
satroot1 build-publication-metadata-catalog --inventory-json artifact_inventory.json --channel network --label "Inventory Metadata Catalog" --published-at 2026-07-08T03:30:00Z --output publication_metadata_catalog.json
```

```bash
satroot1 build-publication-metadata-catalog-manifest publication_metadata_catalog.json --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret --output publication_metadata_catalog_manifest.json
```

```bash
satroot1 publish-publication-metadata-catalog publication_metadata_bundle_alpha publication_metadata_bundle_beta --output-dir publication_metadata_catalog_publication --channel network --label "SATROOT Metadata Catalog" --published-at 2026-07-09T04:00:00Z --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret
```

Those metadata-catalog publish commands can also take a generated `publication_catalog_workspace` or `publication_registry_workspace` root, or the matching `summary.json`, and will expand the nested `publication_metadata_bundles/` lane automatically.

They can also take `--publication-metadata-bundle-collection-dir` when the bundle set was already captured in a reusable collection summary, and exported metadata-catalog presets preserve that collection reference instead of flattening back to explicit bundle paths.

If those publication metadata bundles must stay entirely inside the SATROOT-MACHINE-1 lane, the machine-only wrappers validate each nested artifact before building, signing, or bootstrapping the catalog:

```bash
satroot1 bootstrap-machine-publication-metadata-bundle machine_publication_catalog_workspace --output-dir machine_publication_metadata_bundle --scheme hmac-sha256 --key-id metadata-key
```

```bash
satroot1 bootstrap-stable-publication-metadata-bundle stable_publication_catalog_workspace --output-dir stable_publication_metadata_bundle --scheme hmac-sha256 --key-id metadata-key
```

```bash
satroot1 build-machine-publication-metadata-manifest machine_publication_metadata_bundle/publication_report.md machine_publication_metadata_bundle/publication_descriptor.json --scheme hmac-sha256 --key-id metadata-key --secret metadata-secret --output machine_publication_metadata_manifest.json
```

```bash
satroot1 build-stable-publication-metadata-manifest stable_publication_metadata_bundle/publication_report.md stable_publication_metadata_bundle/publication_descriptor.json --scheme hmac-sha256 --key-id metadata-key --secret metadata-secret --output stable_publication_metadata_manifest.json
```

```bash
satroot1 build-machine-publication-metadata-catalog machine_publication_metadata_workspace machine_publication_metadata_catalog --channel machine --label "Machine Metadata Catalog" --published-at 2026-07-14T05:00:00Z --output machine_publication_metadata_catalog.json
```

```bash
satroot1 build-stable-publication-metadata-catalog stable_publication_metadata_workspace stable_publication_metadata_catalog --channel stable --label "Stable Metadata Catalog" --published-at 2026-07-15T05:00:00Z --output stable_publication_metadata_catalog.json
```

```bash
satroot1 build-machine-publication-metadata-catalog-manifest machine_publication_metadata_catalog.json --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret --output machine_publication_metadata_catalog_manifest.json
```

```bash
satroot1 build-stable-publication-metadata-catalog-manifest stable_publication_metadata_catalog.json --scheme hmac-sha256 --key-id catalog-key --secret catalog-secret --output stable_publication_metadata_catalog_manifest.json
```

```bash
satroot1 bootstrap-machine-publication-metadata-catalog-publication machine_publication_metadata_workspace machine_publication_metadata_catalog --output-dir machine_publication_metadata_catalog_publication --channel machine --label "Machine Metadata Catalog Publication" --published-at 2026-07-14T05:30:00Z --scheme hmac-sha256 --key-id catalog-key
```

```bash
satroot1 bootstrap-stable-publication-metadata-catalog-publication stable_publication_metadata_workspace stable_publication_metadata_catalog --output-dir stable_publication_metadata_catalog_publication --channel stable --label "Stable Metadata Catalog Publication" --published-at 2026-07-15T05:30:00Z --scheme hmac-sha256 --key-id catalog-key
```

For repeatable metadata-catalog packaging, that same command can also load a preset:

```bash
satroot1 bootstrap-publication-metadata-catalog-publication --preset-json examples/publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog.json --output-dir publication_metadata_catalog_publication --label "SATROOT Metadata Catalog Override" --scheme hmac-sha256 --key-id catalog-key
```

```bash
satroot1 bootstrap-machine-publication-metadata-catalog-publication --preset-json examples/publication_metadata_catalog_presets/ai_compute_publication_metadata_catalog.json --output-dir machine_publication_metadata_catalog_publication --label "SATROOT Machine Metadata Catalog Override" --scheme hmac-sha256 --key-id catalog-key
```

If the publication metadata bundle set was already captured by `inventory-artifacts`, the signed bootstrap can consume that saved inventory directly:

```bash
satroot1 bootstrap-publication-metadata-catalog-publication --inventory-json artifact_inventory.json --output-dir publication_metadata_catalog_publication --channel network --label "Inventory Metadata Catalog Publication" --published-at 2026-07-08T04:15:00Z --scheme hmac-sha256 --key-id catalog-key
```

To verify that catalog later:

```bash
satroot1 verify-publication-metadata-catalog-manifest publication_metadata_catalog_publication/publication_metadata_catalog_manifest.json --secrets-json publication_metadata_catalog_publication/publication_metadata_catalog_secrets.json
```

To bind the release-catalog-index, descriptor-index, and metadata-catalog lanes into one signed publication registry:

```bash
satroot1 bootstrap-publication-registry-publication --release-catalog-index-dir publication_network/release_catalog_index --publication-descriptor-index-dir publication_descriptor_index_publication --publication-metadata-catalog-dir publication_metadata_catalog_publication --output-dir publication_registry_publication --channel network --label "SATROOT Publication Registry" --scheme hmac-sha256 --key-id registry-key
```

```bash
satroot1 build-publication-registry --release-catalog-index-dir publication_network/release_catalog_index --publication-descriptor-index-dir publication_descriptor_index_publication --publication-metadata-catalog-dir publication_metadata_catalog_publication --channel network --label "SATROOT Publication Registry" --published-at 2026-07-08T05:00:00Z --output publication_registry.json
```

```bash
satroot1 build-publication-registry --inventory-json artifact_inventory.json --channel network --label "Inventory Publication Registry" --published-at 2026-07-09T02:30:00Z --output publication_registry.json
```

```bash
satroot1 build-publication-registry-manifest publication_registry.json --scheme hmac-sha256 --key-id registry-key --secret registry-secret --output publication_registry_manifest.json
```

```bash
satroot1 publish-publication-registry --release-catalog-index-dir publication_network/release_catalog_index --publication-descriptor-index-dir publication_descriptor_index_publication --publication-metadata-catalog-dir publication_metadata_catalog_publication --output-dir publication_registry_publication --channel network --label "SATROOT Publication Registry" --published-at 2026-07-09T05:00:00Z --scheme hmac-sha256 --key-id registry-key --secret registry-secret
```

At that top publication layer, the `--release-catalog-index-dir`, `--publication-descriptor-index-dir`, and `--publication-metadata-catalog-dir` flags can also point at generated `publication_network`, `publication_catalog_workspace`, or `publication_registry_workspace` roots, or their `summary.json` files, and SATROOT will resolve the nested publication component directories for you.

If all three registry components come from the same `publication_registry_workspace` root or `summary.json`, exported publication-registry presets preserve that higher-level source as `publication_registry_workspace_dir` instead of flattening back to the three nested publication directories.

If all three component lanes must remain SATROOT-MACHINE-1 validated, the machine-only wrappers enforce that before building, signing, or bootstrapping the top-level registry:

```bash
satroot1 build-machine-publication-registry --release-catalog-index-dir machine_release_catalog_index_publication --publication-descriptor-index-dir machine_publication_descriptor_index_publication --publication-metadata-catalog-dir machine_publication_metadata_catalog_publication --channel machine --label "Machine Publication Registry" --published-at 2026-07-14T06:00:00Z --output machine_publication_registry.json
```

```bash
satroot1 build-stable-publication-registry --release-catalog-index-dir stable_release_catalog_index_publication --publication-descriptor-index-dir stable_publication_descriptor_index_publication --publication-metadata-catalog-dir stable_publication_metadata_catalog_publication --channel stable --label "Stable Publication Registry" --published-at 2026-07-15T06:00:00Z --output stable_publication_registry.json
```

```bash
satroot1 build-machine-publication-registry-manifest machine_publication_registry.json --scheme hmac-sha256 --key-id registry-key --secret registry-secret --output machine_publication_registry_manifest.json
```

```bash
satroot1 build-stable-publication-registry-manifest stable_publication_registry.json --scheme hmac-sha256 --key-id registry-key --secret registry-secret --output stable_publication_registry_manifest.json
```

```bash
satroot1 bootstrap-machine-publication-registry-publication --release-catalog-index-dir machine_release_catalog_index_publication --publication-descriptor-index-dir machine_publication_descriptor_index_publication --publication-metadata-catalog-dir machine_publication_metadata_catalog_publication --output-dir machine_publication_registry_publication --channel machine --label "Machine Publication Registry" --published-at 2026-07-14T06:30:00Z --scheme hmac-sha256 --key-id registry-key
```

```bash
satroot1 bootstrap-stable-publication-registry-publication --release-catalog-index-dir stable_release_catalog_index_publication --publication-descriptor-index-dir stable_publication_descriptor_index_publication --publication-metadata-catalog-dir stable_publication_metadata_catalog_publication --output-dir stable_publication_registry_publication --channel stable --label "Stable Publication Registry" --published-at 2026-07-15T06:30:00Z --scheme hmac-sha256 --key-id registry-key
```

```bash
satroot1 bootstrap-publication-registry-publication --inventory-json artifact_inventory.json --output-dir publication_registry_publication --channel network --label "Inventory Publication Registry" --published-at 2026-07-09T03:00:00Z --scheme hmac-sha256 --key-id registry-key
```

To generate that whole registry workspace from an existing publication network in one shot:

```bash
satroot1 bootstrap-publication-registry-workspace --publication-network-dir publication_network --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace --descriptor-index-label "Workspace Descriptor Index" --publication-metadata-catalog-label "Workspace Metadata Catalog" --publication-registry-label "Workspace Publication Registry"
```

```bash
satroot1 bootstrap-publication-registry-workspace --inventory-json artifact_inventory.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace --descriptor-index-label "Inventory Workspace Descriptor Index" --publication-metadata-catalog-label "Inventory Workspace Metadata Catalog" --publication-registry-label "Inventory Workspace Publication Registry"
```

If you already have a reusable publication catalog workspace, the registry workspace bootstrap can copy that lane instead of regenerating descriptor and metadata publications:

```bash
satroot1 bootstrap-publication-registry-workspace --publication-network-dir publication_network --publication-catalog-workspace-dir publication_catalog_workspace --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace --publication-registry-label "Workspace Publication Registry"
```

That same registry-workspace layer can also consume a previously frozen `publication_network_collection_dir` as long as it contains exactly one publication network workspace. If you also freeze a reusable publication catalog workspace collection, the registry-workspace preset layer can now preserve `publication_catalog_workspace_collection_dir` alongside the network collection provenance, and generated nested network presets can in turn preserve their underlying `publication_stack_collection_dir` provenance too:

```bash
satroot1 bootstrap-publication-registry-workspace --publication-network-collection-dir publication_network_collection --publication-catalog-workspace-dir publication_catalog_workspace --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace --publication-registry-label "Workspace Publication Registry"
```

Those collection flags also accept `publication_network_collection/summary.json` and `publication_catalog_workspace_collection/summary.json` directly when you want to point at the frozen collection summaries instead of the collection roots.

There is also a checked-in collection-backed companion preset for the same registry-workspace shape. That checked-in example now resolves both a frozen `publication_network_collection_dir` and a frozen `publication_catalog_workspace_collection_dir` directly from the preset:

```bash
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_collection_backed
```

If the nested generic demo catalog comes from a frozen one-release collection, the same top-level registry workspace can now round-trip from a self-contained preset that carries both the nested catalog preset and the frozen publication network collection reference:

```bash
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace_frozen_catalog
```

To generate just the reusable descriptor-index plus metadata-catalog workspace without the top-level registry lane:

```bash
satroot1 bootstrap-publication-catalog-workspace --discover-under publication_network --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir publication_catalog_workspace --descriptor-index-label "Workspace Descriptor Index" --publication-metadata-catalog-label "Workspace Metadata Catalog"
```

```bash
satroot1 bootstrap-publication-catalog-workspace --inventory-json artifact_inventory.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir publication_catalog_workspace --descriptor-index-label "Inventory Workspace Descriptor Index" --publication-metadata-catalog-label "Inventory Workspace Metadata Catalog"
```

For a checked-in repeatable publication-catalog-workspace composition, the same command can also load a preset:

```bash
satroot1 bootstrap-publication-catalog-workspace --preset-json examples/publication_catalog_workspace_presets/ai_compute_publication_catalog_workspace.json --scheme hmac-sha256 --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --output-dir publication_catalog_workspace --descriptor-index-label "SATROOT Workspace Descriptor Index Override"
```

For a checked-in repeatable registry-workspace composition, the same command can also load a preset:

```bash
satroot1 bootstrap-publication-registry-workspace --preset-json examples/registry_workspace_presets/ai_compute_publication_registry_workspace.json --scheme hmac-sha256 --release-key-id release-key --release-catalog-key-id catalog-key --release-catalog-index-key-id index-key --publication-descriptor-index-key-id descriptor-key --publication-metadata-key-id metadata-key --publication-metadata-catalog-key-id catalog-key --publication-registry-key-id registry-key --output-dir publication_registry_workspace --publication-registry-label "SATROOT Workspace Registry Override"
```

For a checked-in repeatable top-level registry publication, use the publication preset:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry.json --output-dir publication_registry_publication --label "SATROOT Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
```

```bash
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry.json --output-dir machine_publication_registry_publication --label "SATROOT Machine Registry Override" --scheme hmac-sha256 --key-id registry-key
```

If you want the top-level registry publication preset itself to point at one generated `publication_registry_workspace` root instead of three separate nested publication component directories, there are checked-in workspace-backed companions for that too:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_workspace_backed.json --output-dir publication_registry_publication_workspace_backed --label "SATROOT Workspace-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_workspace_backed.json --output-dir machine_publication_registry_publication_workspace_backed --label "SATROOT Machine Workspace-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_workspace_backed.json --output-dir stable_publication_registry_publication_workspace_backed --label "SATROOT Stable Workspace-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

There are matching collection-backed companions when you want the top-level registry publication preset to preserve lineage to one generated `publication_registry_workspace_collection_dir`, with the nested workspace member resolved automatically at load time:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_collection_backed.json --output-dir publication_registry_publication_collection_backed --label "SATROOT Collection-Backed Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_collection_backed.json --output-dir machine_publication_registry_publication_collection_backed --label "SATROOT Machine Collection-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_collection_backed.json --output-dir stable_publication_registry_publication_collection_backed --label "SATROOT Stable Collection-Backed Registry Override" --scheme hmac-sha256 --key-id registry-key
```

If you want that top-level registry publication preset to be fully self-contained for the frozen one-release catalog path, there are checked-in companions that point at a nested `publication_registry_workspace_preset`, which in turn carries a nested collection-backed catalog preset and a single-member publication-network collection reference:

```bash
satroot1 bootstrap-publication-registry-publication --preset-json examples/registry_presets/ai_compute_publication_registry_workspace_catalog_release_collection_backed.json --output-dir publication_registry_publication_frozen_catalog --label "SATROOT Frozen Catalog Publication Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-machine-publication-registry-publication --preset-json examples/registry_presets/machine_compute_publication_registry_workspace_catalog_release_collection_backed.json --output-dir machine_publication_registry_publication_frozen_catalog --label "SATROOT Machine Frozen Catalog Registry Override" --scheme hmac-sha256 --key-id registry-key
satroot1 bootstrap-stable-publication-registry-publication --preset-json examples/registry_presets/stable_reference_publication_registry_workspace_catalog_release_collection_backed.json --output-dir stable_publication_registry_publication_frozen_catalog --label "SATROOT Stable Frozen Catalog Registry Override" --scheme hmac-sha256 --key-id registry-key
```

To verify that registry later:

```bash
satroot1 verify-publication-registry-manifest publication_registry_publication/publication_registry_manifest.json --secrets-json publication_registry_publication/publication_registry_secrets.json
```

To derive a reusable preset back from a generated registry publication:

```bash
satroot1 export-publication-registry-preset publication_registry_publication --output exported_registry.json
```

If that registry was built from one `publication_registry_workspace` root or `summary.json`, the exported preset keeps that workspace reference so later bootstrap and publish flows can resolve the nested component publications automatically.

If you want that exported top-level registry preset to be self-contained for the frozen one-release catalog flow, the export command can also emit a nested registry-workspace preset and nested catalog preset in one pass:

```bash
satroot1 export-publication-registry-preset publication_registry_publication_frozen_catalog --publication-registry-workspace-preset-path exported_registry_workspace.json --catalog-preset-path exported_catalog.json --output exported_registry.json
```

The machine and stable wrappers expose the same nested export flags on `export-machine-publication-registry-preset` and `export-stable-publication-registry-preset`.

The checked-in `examples/registry_presets/` directory now includes companion workspace-backed registry presets for the generic, machine, and stable lanes when you want a reusable registry preset to point at one generated `publication_registry_workspace` root instead of three separate publication component directories.

Machine-only publication lanes now have matching preset-export wrappers too:

```bash
satroot1 export-machine-release-catalog-index-preset machine_release_catalog_index_publication --output exported_machine_release_catalog_index.json
```

```bash
satroot1 export-machine-publication-descriptor-index-preset machine_publication_descriptor_index_publication --output exported_machine_publication_descriptor_index.json
```

```bash
satroot1 export-machine-publication-metadata-catalog-preset machine_publication_metadata_catalog_publication --output exported_machine_publication_metadata_catalog.json
```

```bash
satroot1 export-machine-publication-registry-preset machine_publication_registry_publication --output exported_machine_registry.json
```

The stable-only publication component lane now has matching validated export wrappers too:

```bash
satroot1 export-stable-publication-descriptor-index-preset stable_publication_descriptor_index_publication --output exported_stable_publication_descriptor_index.json
```

```bash
satroot1 export-stable-publication-metadata-catalog-preset stable_publication_metadata_catalog_publication --output exported_stable_publication_metadata_catalog.json
```

```bash
satroot1 export-stable-publication-registry-preset stable_publication_registry_publication --output exported_stable_registry.json
```

To derive a reusable preset back from a generated registry workspace:

```bash
satroot1 export-publication-registry-workspace-preset publication_registry_workspace --output exported_registry_workspace.json
```

That export also accepts `publication_registry_workspace/summary.json` directly, and the same summary-path shortcut works for the machine-only and stable-only registry workspace export wrappers.

That registry-workspace export can also emit nested publication-catalog-workspace and publication-registry preset files, and the nested catalog preset can in turn emit descriptor-index and metadata-catalog presets:

```bash
satroot1 export-publication-registry-workspace-preset publication_registry_workspace --publication-catalog-workspace-preset-path exported_catalog_workspace.json --publication-descriptor-index-preset-path exported_descriptor_index.json --publication-metadata-catalog-preset-path exported_metadata_catalog.json --publication-registry-preset-path exported_registry.json --output exported_registry_workspace.json
```

If that nested generic catalog came from a frozen one-release collection, `--catalog-preset-path` can also emit the nested SATROOT demo catalog preset so the exported registry-workspace preset can rebuild its nested catalog lane from `--preset-json` alone:

```bash
satroot1 export-publication-registry-workspace-preset publication_registry_workspace --catalog-preset-path exported_catalog.json --publication-catalog-workspace-preset-path exported_catalog_workspace.json --output exported_registry_workspace.json
```

Published machine registry-workspace exports are a little stricter: when the original source network is not SATROOT-MACHINE-1-only, the exported machine preset falls back to `release_catalog_index_dir` instead of preserving a generic `publication_network_dir`, so the preset stays reusable by machine-only publish/bootstrap flows.

For the machine-only registry lane, the matching export wrapper validates that the workspace still carries machine provenance. If the nested machine catalog came from a frozen one-release collection, `--catalog-preset-path` can also emit that nested machine catalog preset for a self-contained round-trip:

```bash
satroot1 export-machine-publication-registry-workspace-preset machine_publication_registry_workspace --catalog-preset-path exported_machine_catalog.json --publication-catalog-workspace-preset-path exported_machine_catalog_workspace.json --output exported_machine_registry_workspace.json
```

The stable-only registry lane has the same provenance guard, but validates `SATROOT-STABLE-1` sources instead. The same `--catalog-preset-path` flow works there for frozen one-release stable catalogs:

```bash
satroot1 export-stable-publication-registry-workspace-preset stable_publication_registry_workspace --catalog-preset-path exported_stable_catalog.json --publication-catalog-workspace-preset-path exported_stable_catalog_workspace.json --output exported_stable_registry_workspace.json
```

To derive a reusable preset back from a generated publication catalog workspace:

```bash
satroot1 export-publication-catalog-workspace-preset publication_catalog_workspace --output exported_catalog_workspace.json
```

Like the stack, network, and registry-workspace exports, this command also accepts `publication_catalog_workspace/summary.json` instead of the workspace directory.

If you want the component publications captured as reusable presets at the same time, the catalog-workspace export can also emit nested descriptor-index and metadata-catalog preset files:

```bash
satroot1 export-publication-catalog-workspace-preset publication_catalog_workspace --publication-descriptor-index-preset-path exported_descriptor_index.json --publication-metadata-catalog-preset-path exported_metadata_catalog.json --output exported_catalog_workspace.json
```

And the machine-only publication catalog lane can be exported with the same validation guard:

```bash
satroot1 export-machine-publication-catalog-workspace-preset machine_publication_catalog_workspace --output exported_machine_catalog_workspace.json
```

There is a matching stable-only catalog export wrapper for `SATROOT-STABLE-1` publication catalog workspaces:

```bash
satroot1 export-stable-publication-catalog-workspace-preset stable_publication_catalog_workspace --output exported_stable_catalog_workspace.json
```

To derive a reusable preset back from a generated metadata catalog publication:

```bash
satroot1 export-publication-metadata-catalog-preset publication_metadata_catalog_publication --output exported_publication_metadata_catalog.json
```

If that catalog was built from `--publication-metadata-bundle-collection-dir`, the exported preset keeps the same collection reference so a later bootstrap or publish round-trip can reuse it directly.

To derive a reusable preset back from a generated descriptor index publication:

```bash
satroot1 export-publication-descriptor-index-preset publication_descriptor_index_publication --output exported_publication_descriptor_index.json
```

Inspect a publication descriptor index without signature verification:

```bash
satroot1 publication-descriptor-index-summary publication_descriptor_index_publication
```

Lint a publication descriptor index and its referenced SATROOT artifacts:

```bash
satroot1 publication-descriptor-index-lint publication_descriptor_index_publication
```

Those publication descriptor and registry inspection commands also accept the generated manifest or payload file directly:

```bash
satroot1 publication-descriptor-index-summary publication_descriptor_index_publication/publication_descriptor_index_manifest.json
satroot1 publication-registry-lint publication_registry_publication/publication_registry.json
```

Inspect a publication metadata catalog without signature verification:

```bash
satroot1 publication-metadata-catalog-summary publication_metadata_catalog_publication
```

Lint a publication metadata catalog and its referenced publication metadata bundles:

```bash
satroot1 publication-metadata-catalog-lint publication_metadata_catalog_publication
```

Those publication metadata catalog inspection commands also accept the generated manifest or payload file directly:

```bash
satroot1 publication-metadata-catalog-summary publication_metadata_catalog_publication/publication_metadata_catalog_manifest.json
```

Inspect a bootstrapped publication metadata bundle without signature verification:

```bash
satroot1 publication-metadata-bundle-summary publication_metadata_bundle
```

Lint a publication metadata bundle, its stored report/descriptor files, and the currently referenced packaged SATROOT artifact:

```bash
satroot1 publication-metadata-bundle-lint publication_metadata_bundle
```

Inspect a release catalog publication without signature verification:

```bash
satroot1 release-catalog-summary release_catalog_bootstrap
```

Those read-only release inspection commands also accept the generated manifest or payload file directly when you are already focused on one artifact:

```bash
satroot1 release-summary stable_release/release_manifest.json
satroot1 release-catalog-lint release_catalog_bootstrap/release_catalog.json
satroot1 release-catalog-index-summary release_catalog_index_bootstrap/release_catalog_index_manifest.json
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

Those workspace inspection commands also accept the generated `summary.json` directly when you already have the summary file open:

```bash
satroot1 demo-catalog-summary catalog_workspace/summary.json
satroot1 publication-stack-lint publication_stack/summary.json
satroot1 publication-network-summary publication_network/summary.json
satroot1 publication-catalog-workspace-lint publication_catalog_workspace/summary.json
satroot1 publication-registry-workspace-summary publication_registry_workspace/summary.json
```

The reusable collection layers now have matching summary commands too, so frozen bundle/release/workspace sets can be inspected without manually opening `summary.json`:

```bash
satroot1 bundle-collection-summary bundle_collection
satroot1 release-collection-summary release_collection/summary.json
satroot1 release-catalog-collection-summary release_catalog_collection
satroot1 demo-catalog-workspace-collection-summary catalog_workspace_collection
satroot1 publication-stack-collection-summary publication_stack_collection
satroot1 publication-network-collection-summary publication_network_collection/summary.json
satroot1 publication-metadata-bundle-collection-summary publication_metadata_bundle_collection
satroot1 publication-catalog-workspace-collection-summary publication_catalog_workspace_collection
satroot1 publication-registry-workspace-collection-summary publication_registry_workspace_collection/summary.json
```

Those same reusable collection layers now expose matching lint commands too, so copied collection members can be checked in place without dropping down into each directory one-by-one:

```bash
satroot1 bundle-collection-lint bundle_collection
satroot1 release-collection-lint release_collection/summary.json
satroot1 release-catalog-collection-lint release_catalog_collection
satroot1 demo-catalog-workspace-collection-lint catalog_workspace_collection
satroot1 publication-stack-collection-lint publication_stack_collection
satroot1 publication-network-collection-lint publication_network_collection/summary.json
satroot1 publication-metadata-bundle-collection-lint publication_metadata_bundle_collection
satroot1 publication-catalog-workspace-collection-lint publication_catalog_workspace_collection
satroot1 publication-registry-workspace-collection-lint publication_registry_workspace_collection/summary.json
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

Inspect a publication catalog workspace without signature verification:

```bash
satroot1 publication-catalog-workspace-summary publication_catalog_workspace
```

Lint a publication catalog workspace, its generated publication components, and all referenced publication metadata bundles:

```bash
satroot1 publication-catalog-workspace-lint publication_catalog_workspace
```

Inspect a publication registry workspace without signature verification:

```bash
satroot1 publication-registry-workspace-summary publication_registry_workspace
```

Lint a publication registry workspace, its copied/generated publication components, and all referenced publication metadata bundles:

```bash
satroot1 publication-registry-workspace-lint publication_registry_workspace
```

Inspect a publication registry without signature verification:

```bash
satroot1 publication-registry-summary publication_registry_publication
```

Lint a publication registry and its referenced descriptor, metadata, and release-catalog-index components:

```bash
satroot1 publication-registry-lint publication_registry_publication
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

## Anchored demo lane

The anchored demo lane is the designated entry point for that intentional replacement. It is the first of the four anchored lanes — anchored demo, anchored publication, on-chain envelope, and envelope verification — which are the only lanes ever meant to carry a real outpoint or transaction id, and always only via run-time flags:

```bash
python scripts/run_anchored_demo_smoke.py
python -m satroot_anchored_demo_smoke --root-id <txid>:<vout>
```

It binds one dedicated identity demo namespace to a `root_id` that defaults to its own distinct placeholder (`6666...6666:0`), signs the namespace lifecycle with the `ed25519` scheme instead of the demo or hmac schemes, and emits a report proving five things: the semantic state hash binds the `root_id`, the ed25519 bundle verifies against its generated key material, replay is deterministic, events carrying a foreign root are rejected with `root_id mismatch`, and no ledger event kind models root custody.

That last check is the root lifecycle rule made concrete: moving the root satoshi on-chain never appears in the ledger and cannot alter the semantic state hash. Binding a real one-satoshi outpoint (testnet first) only changes the `root_id` string passed at run time — never the event rules, and never a checked-in file. The lane requires the `[crypto]` extra (`pip install -e ".[crypto]"`).

The companion anchored publication lane pushes the same anchored namespace through the full publication ladder — signed bundles, release, catalog, network, and registry workspace — with ed25519 signing end to end, and verifies the root binding in every generated bundle genesis:

```bash
python scripts/run_anchored_publication_smoke.py
python -m satroot_anchored_publication_smoke --root-id <txid>:<vout>
```

The on-chain envelope lane completes the loop, building the SPEC section 4 commitment script (`OP_FALSE OP_RETURN "SATROOT1" <content-type> <payload>`) for a namespace's root and state hash — deterministically and fully offline; the operator broadcasts the result out-of-band:

```bash
python scripts/run_onchain_envelope_smoke.py
python -m satroot_onchain_envelope_smoke --root-id <txid>:<vout> --state-hash sha256:<hex>
```

The envelope verification lane closes the read side: given a serialized transaction's raw bytes (fetched out-of-band), it confirms — fully offline — that the bytes hash to the expected transaction id and carry exactly one `SATROOT1` envelope output matching the rebuilt commitment byte for byte:

```bash
python scripts/run_envelope_verification_smoke.py
python -m satroot_envelope_verification_smoke --raw-tx-hex-file <path> --root-id <txid>:<vout> --state-hash sha256:<hex> --expected-txid <txid>
```

Intentional anchored runs against real outpoints are recorded in `ANCHORS.md`, the only place in the repository where a real outpoint may appear.
