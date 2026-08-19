# SATROOT Roadmap

## Project position

SATROOT is a BSV-anchored overlay protocol for deterministic semantic assets.

The base idea is:

`1 satoshi -> 1 root-bound namespace -> unbounded protocol-defined state`

The project should remain disciplined about this separation:

- BSV anchors the root satoshi and provides ordering, publication, and custody.
- SATROOT defines semantic balances, rights, and validity rules above that root.

## Current deliverable

`v0.5` is the root-anchoring proof artifact for `SATROOT-1`.

It proves that one real one-satoshi BSV testnet outpoint can be bound as the root of a dedicated demo namespace whose lifecycle is signed and verified through the ed25519 path, that the semantic state binds that root while rejecting foreign roots, and that root-satoshi custody stays out-of-band by construction — all without changing the base one-satoshi kernel and while every checked-in example keeps a placeholder root.

Current scope:

- root-bound namespace via `root_id`
- token genesis
- `mint`, `transfer`, `burn`, `freeze`, and `rotate-authority`
- sequence enforcement
- deterministic replay
- supply invariants
- example token `FLOOR1`
- example stable token `USDROOT1`
- released profile-matrix smoke verification across stable, machine, receipt, identity, and license publication registry workspaces
- released mixed-profile publication federation with collection-backed federated registry round trips, one packaged top-level operator proof, and one packaged local release gate above the per-profile lanes

Release status:

- `v0.1-genesis` has been tagged and pushed from this repository.
- The reference CLI, example preset tree, collection summary/lint surface, chunked test runner, and CI verification flow are now part of the frozen base deliverable.
- `v0.2-stable-profile` has been tagged and pushed from this repository.
- The `SATROOT-STABLE-1` reference-only lane now has a dedicated smoke workflow, packaged entrypoint, CI coverage, and a tagged publication-path milestone.
- `v0.3-namespace-expansion` has been tagged and pushed from this repository.
- The machine, receipt, identity, and license lanes now join the stable lane under one released profile-matrix smoke surface with dedicated per-profile publication-path verification.
- `v0.4-publication-federation` has been tagged and pushed from this repository.
- The mixed-profile federation surface, the collection-backed federated registry round trip, the stable/machine and singleton publication ladders, the top-level operator proof, and the local release gate are now part of the released deliverable.
- `v0.5-root-anchoring` binds the first real one-satoshi testnet outpoint through the anchored demo lane, recorded in `ANCHORS.md`.

## Near-term build order

### v0.2 Stable profile

Goal: add reference-value accounting without changing the base primitive.

- Add `SATROOT-STABLE-1` as a profile only.
- Include `USDROOT1` or `INRROOT1` example records.
- Keep claims reference-only unless a later legal/compliance layer exists.
- Add a clear end-to-end preset and publication path for stable profile artifacts, parallel to the current generic/machine/stable publication lanes.
- Keep the output framed as deterministic accounting state, not redemption-bearing money.

Current status:

- `SATROOT-STABLE-1` draft exists in this repo.
- `USDROOT1` reference-only examples are included as the first profile implementation artifact.
- A dedicated stable-profile smoke workflow now replays the checked-in `USDROOT1` ledger and generates, summarizes, and lints a full `SATROOT-STABLE-1` publication registry workspace through the direct stable builder lane.
- This milestone has now been tagged as `v0.2-stable-profile`.

Recommended concrete deliverables for `v0.2`:

- one stable profile example that runs end-to-end from example records to signed publication output,
- one stable profile bundle/release/catalog/index lane that mirrors the generic kernel ergonomics,
- one profile-specific verification section in the docs explaining what is and is not being claimed,
- one release tag such as `v0.2-stable-profile` only after the profile path is tested as thoroughly as the current `v0.1` kernel.

### v0.3 Namespace expansion

Goal: show that the root is more than a token anchor.

- Define receipt and invoice objects.
- Define machine-credit balances.
- Define rights, license, or identity records.

Current status:

- `SATROOT-MACHINE-1` draft exists in this repo.
- `APICREDIT1` examples are included as the first machine-credit implementation artifact.
- A dedicated machine-profile smoke workflow now replays the checked-in `APICREDIT1` ledger and generates, summarizes, and lints a full `SATROOT-MACHINE-1` publication registry workspace through the direct machine builder lane.
- `SATROOT-RECEIPT-1` draft exists in this repo.
- `RECEIPT1` examples are included as the first receipt-object implementation artifact.
- A dedicated receipt-profile smoke workflow now replays the checked-in `RECEIPT1` ledger and generates, summarizes, and lints a full `SATROOT-RECEIPT-1` singleton publication registry workspace from the checked-in receipt preset.
- `SATROOT-IDENTITY-1` draft exists in this repo.
- `IDENTITY1` examples are included as the first identity-object implementation artifact.
- A dedicated identity-profile smoke workflow now replays the checked-in `IDENTITY1` ledger and generates, summarizes, and lints a full `SATROOT-IDENTITY-1` singleton publication registry workspace from the checked-in identity preset.
- `SATROOT-LICENSE-1` draft exists in this repo.
- `LICENSE1` examples are included as the first license-object implementation artifact.
- A dedicated license-profile smoke workflow now replays the checked-in `LICENSE1` ledger and generates, summarizes, and lints a full `SATROOT-LICENSE-1` singleton publication registry workspace from the checked-in license preset.
- A released profile-matrix smoke workflow now runs the stable, machine, receipt, identity, and license lanes together and emits one consolidated verification report.
- This milestone has now been tagged as `v0.3-namespace-expansion`.

Recommended order inside `v0.3`:

1. machine-credit lane
2. receipt/invoice lane
3. identity/authority lane
4. license/usage-right lane

That order keeps the project close to machine-native accounting and operational workflows before moving into heavier rights semantics.

### v0.4 Publication federation

Goal: consolidate released profile artifacts into reusable higher-level publication collections without flattening their profile-specific provenance.

The success condition is narrow:

- the base `SATROOT-1` kernel remains unchanged in principle,
- multiple generated profile artifacts can be consolidated into reusable higher-level publication collections without flattening their profile-specific provenance,
- operator-facing workflows stay deterministic, inspectable, and lintable at every aggregation layer,
- profile-specific semantics remain explicit instead of being blurred into a generic registry abstraction,
- the docs keep separating protocol state from legal and economic claims as strictly as the current base, stable, and namespace-expansion lanes.

Current status:

- The top-level operator proof now has a matching packaged local release-gate wrapper above it for import smoke, proof execution, and chunked pytest in one pass before tagging.
- The stable/machine publication ladder, singleton publication ladder, and mixed-profile federation helpers now also roll up under one packaged top-level operator-proof smoke wrapper.
- The stable and machine bundle-index, release-catalog, and release-catalog-index matrix helpers now also roll up under one packaged publication-ladder smoke wrapper.
- The receipt, identity, and license singleton bundle-index, release-catalog, and release-catalog-index matrix helpers now also roll up under one packaged singleton publication-ladder smoke wrapper.
- The receipt, identity, and license singleton lower-level demo bundle-index helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- The receipt, identity, and license singleton higher-level demo release-catalog publication helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- The receipt, identity, and license singleton higher-level demo release-catalog-index publication helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- The stable and machine lower-level demo bundle-index helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- The stable and machine higher-level demo release-catalog index publication helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- The stable and machine higher-level demo release-catalog publication helpers now have dedicated packaged smoke wrappers plus one small matrix wrapper above them.
- A first `satroot_profile_federation_smoke` wrapper now reuses the released profile matrix as source material.
- That wrapper freezes the resulting per-profile demo catalog, publication stack, publication network, publication catalog workspace, and publication registry workspace outputs into explicit collections.
- It also proves that those released profile demo catalogs can be republished through one mixed-profile publication stack, publication network, publication catalog workspace, and publication registry workspace without changing the base kernel.
- The mixed federated publication catalog workspace and publication registry workspace are now also snapshotted into their own explicit top-level collections for reuse.
- The mixed federated publication catalog workspace, publication stack, publication network, and publication registry workspace are now all exported and rebuilt through nested publication presets as part of the same smoke proof.
- Those mixed federated registry workspace collections can now also drive a top-level publication-registry publication bootstrap and exported-preset round trip through a dedicated packaged smoke surface.
- This milestone has now been tagged as `v0.4-publication-federation`.

### v0.5 Root anchoring

Goal: replace the placeholder root with one intentional real outpoint in one dedicated demo lane, without changing kernel rules or default examples.

The success condition is narrow:

- the `SATROOT-1` kernel rules remain unchanged,
- one real 1-satoshi BSV outpoint, on testnet first, is bound as the `root_id` of one dedicated demo namespace, replacing the all-zeros placeholder only in that lane,
- the root lifecycle rule is demonstrated against that real outpoint, keeping root-satoshi custody and movement separate from semantic transfer events,
- all other checked-in examples keep placeholder roots by default so the repo never accidentally claims a live anchor,
- signature verification for the anchored demo lane graduates from the placeholder interface to the existing Ed25519 verifier path without adding production key-management claims,
- the docs keep separating protocol state from legal and economic claims as strictly as every released lane.

Current status:

- The anchored identity demo lane (`satroot_anchored_demo_smoke`) now exists with its own distinct placeholder root, accepts a real outpoint only through its `--root-id` flag at run time, and signs and verifies its lifecycle through the existing Ed25519 path.
- The lane's report demonstrates the root lifecycle rule: state binds `root_id`, replay is deterministic, foreign-root events are rejected, and no ledger event kind models root custody.
- One real one-satoshi BSV testnet outpoint has been bound through the lane with every check passing, the run is recorded in `ANCHORS.md`, and every checked-in example still carries a placeholder root.

## Immediate next milestone

If work resumes right away, the best next milestone is:

`v0.6-anchored-publication`

The success condition should be narrow:

- the `SATROOT-1` kernel rules remain unchanged,
- the anchored demo namespace is published through the existing ladder — signed bundle, release, catalog, and registry workspace — with ed25519 signing end to end instead of the hmac default,
- the published artifacts carry the real `root_id` only because the operator passes it at run time; checked-in presets stay on placeholder roots,
- `ANCHORS.md` gains the published-artifact hashes as the continuation of the anchored-run record,
- the docs keep separating protocol state from legal and economic claims as strictly as every released lane.

## Core architectural rule

SATROOT does not merely mint tokens from one satoshi.

It turns one satoshi into a root-bound namespace for deterministic semantic state.

That namespace may later support:

- tokens,
- credits,
- receipts,
- licenses,
- identities,
- machine-readable rights,
- event streams.

## Non-goals for the base protocol

The `SATROOT-1` kernel should not absorb:

- stablecoin reserve logic,
- redemption systems,
- exchange integration assumptions,
- wallet interoperability claims,
- legal-rights claims by default,
- production signature standards before the data model is settled.
