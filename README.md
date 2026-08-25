# SATROOT

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22055844.svg)](https://doi.org/10.5281/zenodo.22055844)
[![PyPI](https://img.shields.io/pypi/v/satroot.svg)](https://pypi.org/project/satroot/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**SATROOT is a signed, hash-linked, append-only event log with deterministic
replay to a typed state.**

Anyone holding the log and the public keys can recompute the exact state and
its hash offline — no server, no database, no trust in whoever produced it.
Two independent implementations (Python and TypeScript) reproduce every state
hash byte for byte against a shared conformance corpus.

Ledger state can *optionally* be committed to an external timestamping
backend, so a third party can attest that a given state existed at a given
time. Two backends ship: an **RFC 3161 Time-Stamp Authority** (no blockchain
involved) and a **Bitcoin SV** `OP_RETURN` transaction. Both are optional and
interchangeable — they commit byte-identical documents — and **verifying a
ledger never requires either.**

The kernel defines **one reducer**: five actions (`mint`, `transfer`, `burn`,
`freeze`, `rotate-authority`) over balances, supply, mint authority and frozen
accounts. Six **profiles** — stable reference units, machine credits,
receipts, identities, licenses, and event-stream custody — add required
genesis metadata and validation on top of that single reducer; they do not
define their own state or transitions. SATROOT is therefore a typed
token-and-account ledger with domain-labelled profiles, not a general
application-state framework. `COMPARISON.md` places it against related work,
including where that work is better.

<details>
<summary>Where the name comes from, and the original framing</summary>

Its base primitive, **SATROOT-1**, can treat one native BSV satoshi UTXO as
an irreducible accounting floor, using that UTXO as a root witness, authority
handle, and namespace anchor for deterministic protocol state.

> The satoshi is not subdivided. The satoshi anchors a protocol-defined state space.

That origin explains the vocabulary, but it is not a requirement: a namespace
root is an identifier, and the chain is one way to publish commitments about
it.
</details>

## Project thesis

SATROOT starts from one idea:

> A satoshi is the floor of value; it is not the ceiling of meaning.

That means one satoshi can anchor a replayable semantic ledger without pretending to create sub-satoshis. Token units, credits, receipts, rights, and other objects live as protocol-defined state above the native chain unit.

## Quickstart

Requires Python 3.10 or newer. From a clone of this repo:

```bash
pip install -e .
satroot1 replay examples/events_floor1.json
```

That replays the checked-in `FLOOR1` demo ledger and prints its deterministic balances and state hash. Add the extras for the full surface: `pip install -e ".[crypto,validation]"` enables ed25519 signing (used by the anchored lanes) and JSON-schema validation (used by the publication workspace generators). Every checked-in example runs on placeholder roots — see `ANCHORS.md` for the real mainnet anchoring record, and `SPEC.md` for the protocol itself. Licensed Apache-2.0.

## Citation

Archived on Zenodo; every tagged release gets its own DOI. The concept
DOI below always resolves to the latest version:

> Saxena, Parth Mauria. *SATROOT: deterministic, offline-verifiable
> semantic ledgers rooted in a single satoshi*. https://doi.org/10.5281/zenodo.22055844

Machine-readable metadata is in `CITATION.cff`.

## What this repo delivers

This repository ships the `SATROOT-1` kernel, six registered profiles, the publication ladder, and the anchored proof loop:

- `SPEC.md` - human-readable protocol specification.
- `ARCHITECTURE.md` - top-level model, layer boundaries, and deliverable framing.
- `BOUNDARIES.md` - claim discipline, non-goals, and legal boundary language.
- `SECURITY_REVIEW.md` - record of internal adversarial passes over the kernel: what was attacked, what held, what was fixed.
- `ROADMAP.md` - project scope, deliverables, and released plus planned protocol profiles.
- `ANCHORS.md` - the only checked-in record of real on-chain outpoints and transaction ids.
- `COMPARISON.md` - how SATROOT relates to SCITT, in-toto/SLSA, C2PA, W3C VC, KERI, Certificate Transparency, Sigstore and git: what it composes from existing standards, the one gap it fills, and where those systems are better than it.
- `INTEGRATION.md` - integrator's guide: how to build an application on the package (provisioning, appending, verifiable exports, envelope commitments) and the pitfalls the kernel enforces.
- `docs/CLI.md` - complete `satroot1` command and smoke-lane reference.
- `docs/TESTING.md` - running the test suite and each individual lane.
- `vectors/` - deterministic conformance corpus for validating any SATROOT-1 implementation; see `vectors/README.md`.
- `verifiers/typescript/` - a second implementation, in TypeScript, that passes the same corpus. Written by the same author from the specification rather than ported from the reference code, so it demonstrates the spec is implementable from its text - but it is not third-party independent validation.
- `KEY_MANAGEMENT.md` - operational guidance for composing the frozen signature schemes: custody separation, verifier-only distribution, rotation, and the lint-versus-verify trust model (`*-lint` is structural; `verify-*` is the cryptographic gate).
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
- `examples/` - seven runnable demo ledgers (`FLOOR1`, `USDROOT1`, `APICREDIT1`, `RECEIPT1`, `IDENTITY1`, `LICENSE1`, `EVENT1`) and the reusable preset trees.
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

## Profile lanes and preset tree

The base protocol stays intentionally small. Expansion belongs in separate profiles, and the released profile lanes below all follow that rule.

This repo includes the stable-value profile:

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

## Tests and CLI reference

The full command surface lives in dedicated references, kept out of this
overview so it stays readable:

- **[`docs/CLI.md`](docs/CLI.md)** - every `satroot1` command and smoke
  lane, with runnable examples: signing utilities, bundles, releases,
  catalogs, registries, and the anchored lanes.
- **[`docs/TESTING.md`](docs/TESTING.md)** - running the suite, the
  chunked full-suite helper, and each individual lane.
- **[`INTEGRATION.md`](INTEGRATION.md)** - building an application on the
  Python API.

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

## Anchored lanes

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
