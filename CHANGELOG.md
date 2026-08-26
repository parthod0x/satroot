# Changelog

## Unreleased

- Corrects an overstatement in `satroot_commitment.verify_timestamp_token`. It performs no cryptographic verification of a timestamp token: it parses out the SHA-256 `messageImprint` and compares it against the commitment digest, and nothing in the module checks the TSA's signature over `TSTInfo` or validates a certificate chain. The previous docstring said only that certificate chain validation was left to the relying party, which invites the reading that the signature *is* checked. A forged token carrying the right imprint passes, and `tests/test_commitment_backends.py` now pins exactly that. The returned mapping gained `binding_matches`, `signature_verified` and `chain_validated`, and `describe_backends` no longer calls the function a "verifier".

## v1.7-standards-alignment - 2026-08-26

- Publishes the package for the first time since `v1.4-prepublication-hardening`, closing a two-milestone gap between the repository and PyPI. `pip install satroot` now resolves to 1.7.0; it previously resolved to 1.4.0, which predated the v1.6 determinism fix: the `MAX_AMOUNT_DIGITS` bound whose absence made the accept/reject decision for long digit strings depend on CPython's host-configurable integer-conversion limit. Installed users therefore had a host-dependent kernel boundary that the repository had already fixed, and had none of `satroot_commitment`, `satroot_cose` or `satroot_jcs`. `pyproject.toml` and `CITATION.cff` now both carry the milestone version, as `RELEASE_CHECKLIST.md` requires - `CITATION.cff` previously carried no version field at all.

- Validates `satroot_jcs` against the published RFC 8785 conformance vectors, via `scripts/fetch_rfc8785_vectors.py` and `tests/test_rfc8785_official_vectors.py`: 3 pass, 0 fail, 2 skipped for non-integer numbers that are out of declared scope. `weird.json` settles the UTF-16 question empirically - it holds an astral emoji key and a BMP Hebrew letter, the reference output sorts the astral character first, `satroot_jcs` reproduces that output exactly and SATROOT's `canonical_json` does not. Also records a correction to `draft-mih-sokolov-scitt-payload-binding-01` section 11.3: it forbids floats on the grounds that JCS does not normalise lexical forms such as `1.0`, `1e0` and `1.00`, but JCS re-serialises via ECMAScript `Number::toString`, and the RFC's own vectors show `4.50` becoming `4.5` and `2e-3` becoming `0.002`. The prohibition is sound; the stated reason is not.

- Implements `jcs-n` from `draft-mih-sokolov-scitt-payload-binding-01` in `satroot_jcs`, including the exclusion-set step, and records the result in `docs/CANONICALISATION.md`. The headline digest difference against SATROOT is arithmetic rather than a finding - the draft states that the equivalence of absent, null and empty values is a payload-class decision, and that digests are comparable only within one digest context. Implementing it did surface three things: an emptied object inside an array has two defensible readings producing different digests; "explicitly set to a non-null value" is a trap for falsiness-based languages, which would strip `false`, `0` and `""`; and the collapse is unconditional, so a profile binding record shape cannot use the scheme. Also bounds integer serialisation at 2**53 rather than diverging from ECMAScript `Number::toString`, and records that the official RFC 8785 vectors have not been run.

- Adds `satroot_jcs` and `docs/CANONICALISATION.md`: a measured comparison of SATROOT's canonical JSON against RFC 8785 (JCS). 13 of 15 cases agree; the two that diverge do so because JCS sorts object keys by UTF-16 code unit while Python sorts by Unicode code point, which differ for characters outside the Basic Multilingual Plane. The divergence is unreachable through any schema-valid SATROOT record because field names are ASCII, but that is a property of the schema rather than the canonicalisation. Also records that neither scheme normalises Unicode, so NFC and NFD forms are distinct keys under both, making normalisation a producer-side concern.

- Adds `drafts/draft-saxena-scitt-state-derivation-00.md`, an Internet-Draft for the IETF SCITT community. It reports implementation experience rather than proposing new mechanism: what a profile must specify for an ordered Statement Sequence to reduce deterministically to application state, the three places independent implementations diverged in practice, and an open question about whether the reducer's total order should come from registration order or from the payloads. Security considerations state plainly that this pattern does not address key compromise and is in tension with a right of erasure.

- Adds `satroot_cose`: encodes SATROOT events as COSE_Sign1 Signed Statements, the payload form used by SCITT (RFC 9943) transparency services, with every statement in a ledger sharing the namespace `root_id` as its CWT subject. Includes a dependency-free deterministic CBOR encoder implementing the RFC 8949 section 4.2 subset COSE requires, checked against the RFC's own test vectors. Signatures are over the raw `Sig_structure`, so they interoperate with other COSE implementations. Tests pin that the encoding is lossless: the encoded payloads replay to the same state hash as the original ledger. Scope is deliberately limited to Signed Statements - no Transparency Service, no Receipts, no inclusion proofs.

- Corrects how the project describes itself, in `README.md` and `COMPARISON.md`: the kernel defines a single reducer over five actions and a fixed state shape, and the six profiles add genesis metadata and validation rather than their own state or transitions. SATROOT is a typed token-and-account ledger with domain-labelled profiles, not a general application-state framework - earlier wording overstated this.
- Adds `COMPARISON.md`, an honest field survey placing SATROOT against SCITT (RFC 9943), in-toto/SLSA, C2PA, W3C Verifiable Credentials, KERI/ACDC, Certificate Transparency, Trillian, Sigstore/Rekor and git. Records that the component parts are all existing standards and the contribution is composition; names KERI's Key Event Log and Google's experimental Verifiable Log-Derived Map as the closest prior art; and states plainly where those systems are better than SATROOT - O(log n) inclusion proofs versus SATROOT's O(n) full replay, non-equivocation and split-view resistance, and ecosystem maturity. Also records that third-party witnessing is no longer a differentiator for anyone, and documents the relationship between SATROOT's canonical JSON and RFC 8785 JCS.

- Adds `satroot_commitment`, which separates *what* a namespace commits from *where* it is published. The commitment document - canonical JSON binding `root_id` to `state_hash` - is now defined independently of any backend, and two backends implement it: the existing `bsv-opreturn` envelope, and a new dependency-free `rfc3161` backend that submits the commitment digest to any Time-Stamp Authority with no blockchain involved. `tests/test_commitment_backends.py` pins the property that matters: both backends commit byte-identical documents, so "the anchoring backend is interchangeable" is demonstrated rather than asserted. Ledger replay and state verification continue to require no backend at all.

## v1.6-mainnet-anchor - 2026-08-22

- Records the first **mainnet** anchoring run in `ANCHORS.md`: root satoshi `38ff9da029e66ee9b6a1b175025388caf7fb6d3bb0273812737d7dd6b347c473:0` (confirmed, block 963415), namespace bound and published through the full ladder with ed25519, semantic state hash `sha256:34049329f152c388cad547440b32213d48be583c0fa16d93a94582f7399fde58` committed on-chain in the SPEC section 4 envelope (tx `7f5946898440a96e18526440ed7140eda85e7dad7e753c7d0b88d09f008b1f83`), and the broadcast bytes verified fully offline with all seven checks passing. Updates the launch note to lead with the mainnet proof.
- Adds `SECURITY_REVIEW.md` recording the first internal adversarial pass over the kernel - the surfaces attacked, the twelve attack shapes that were correctly rejected, the two findings, and the highest-value places for a future external reviewer to look.
- Refines the signer-key-binding boundary in `BOUNDARIES.md`: because `prev_event_id` binds each event into its successor, key substitution on an interior event is rejected by the chain and only the final event is genuinely exposed; `test_key_substitution_is_chain_blocked_except_at_the_tip` pins both halves.
- Bounds protocol amounts at 512 digits (`MAX_AMOUNT_DIGITS`) across the engine, the JSON schema, and the TypeScript verifier, fixing a determinism defect found by the adversarial pass: `parse_amount` previously delegated to `int()`, whose string-conversion limit is host-configurable in CPython, so a sufficiently long digit string raised a bare `ValueError` instead of `SatRootError` and the accept/reject decision depended on interpreter configuration - and diverged from implementations with unbounded integers. The bound sits below CPython's configurable floor of 640, so conforming implementations now agree on every host. Adds two conformance vectors (transfer amount and genesis balance) and two adversarial regression tests.
- Adds `verifiers/typescript/`, an independent TypeScript implementation of the SATROOT-1 replay rules with zero runtime dependencies, which reproduces canonical JSON, event ids, and state hashes byte for byte and passes all conformance vectors across all three signature schemes; wired into CI as a second job so any kernel change that breaks cross-implementation agreement fails the build. Its README records the details a second implementer must get right (key sorting at every level, HMAC secrets as literal UTF-8 of the hex string, raw Ed25519 keys in an SPKI envelope, zero balances omitted from the commitment snapshot).
- Grows the conformance corpus from 14 to 31 vectors (12 accept, 19 reject), covering the two previously untested kernel actions (`freeze`, `rotate-authority`, plus standalone `mint`), authority enforcement (non-authority mint/rotate/freeze), frozen-account transfers, amount canonicalization (zero, negative, leading zeros), and chain integrity (broken `prev_event_id`, reordered events, forged signatures).

## v1.5-integration-and-vectors - 2026-08-22

- Adds `CITATION.cff` so archived releases and citations carry correct authorship, and enables Zenodo archiving of tagged releases.
- Adds `INTEGRATION.md`, an integrator's guide distilled from building a real multi-agent credit-ledger service on the published wheel: provisioning, appending, bundle export with persistent keys, envelope commitments, and a pitfall index.
- Adds `vectors/`, a deterministic 14-vector conformance corpus over the frozen kernel rules (three schemes, fixed key material, byte-stable regeneration), with `scripts/generate_conformance_vectors.py`, `scripts/run_conformance_vectors.py`, and `tests/test_conformance_vectors.py` pinning the corpus to the reference engine.
- Adds `docs/index.html` and `docs/LAUNCH.md`, the launch note "One Satoshi, One Namespace", served via GitHub Pages from the `docs/` folder.

## v1.4-prepublication-hardening - 2026-08-20

- Makes the reference engine conform to its own JSON schema on three input classes the schema already forbade, so no valid artifact changes: `parse_amount` now rejects non-ASCII/Unicode digit strings (previously accepted, or raised a non-`SatRootError`), and `decimals` and `sequence` now reject JSON booleans at genesis and replay.
- Bounds-checks the standalone on-chain envelope parser against truncated `OP_PUSHDATA1`/`OP_PUSHDATA2` length bytes so malformed scripts raise `SatRootError` instead of `IndexError`.
- Documents the deliberate v1 boundary that the kernel authorizes on the `signer` string plus a valid signature under some registered key, and does not bind a signing key to the account it acts for, across `BOUNDARIES.md`, `KEY_MANAGEMENT.md`, and the `SPEC.md` claim-discipline section; adds `tests/test_kernel_adversarial.py` pinning this boundary plus type-strictness and replay/sequence enforcement.
- Ships the protocol schemas and example ledgers as package data (`satroot_protocol`, `satroot_examples`) with a source-checkout-first resolver, so an installed wheel resolves the profile registry, schemas, and example presets without the source tree; adds a `## Quickstart` with install/first-command/license to the top of the README and fixes the stale direct-invocation and demo-ledger-count references surfaced by the pre-publication review.

## v1.3-key-management - 2026-08-20

- Adds `KEY_MANAGEMENT.md`: operational guidance for composing the frozen `demo`, `hmac-sha256`, and `ed25519` schemes — scheme selection, three-layer custody separation (root satoshi, event signing keys, publication keys), verifier-only distribution as the default, rotation via the ledger's own `rotate-authority` action and publication key-id succession, and an explicit non-claims section consistent with `BOUNDARIES.md`.
- Docs-only release: no kernel rules, lanes, schemes, or dependencies change.

## v1.2-event-matrix-promotion - 2026-08-20

- Promotes the event lane into the demo catalog matrix: `SATROOT-EVENT-1` joins `DEMO_CATALOG_BUNDLE_SPECS` and the structure-override specs, gains the checked-in `examples/catalog_presets/event_stream_catalog.json` preset, and the generic demo catalog surfaces now generate six bundles.
- Upgrades the event profile lane from a bundle-level check to a full singleton publication registry workspace lane mirroring the identity lane, and adds it to the profile-matrix smoke and the federation `PROFILE_ORDER`, growing the matrix to six lanes and the federated registry workspace to eighteen artifacts.
- Updates every profile-count and artifact-count assertion across the federation, matrix, operator-proof, and federated-collection test surfaces from five/fifteen to six/eighteen.

## v1.1-event-streams - 2026-08-19

- Registers `SATROOT-EVENT-1` as the sixth profile: an append-only event-stream head object in `single-stream` mode with deterministic publisher handoff, added to the profile registry, the record schema (four new genesis fields), kernel scaffold defaults, singleton demo defaults, genesis validation, and the singleton-object profile set — with the frozen `SATROOT-1` kernel rules unchanged, exactly as the namespace-expansion boundary requires.
- Adds `examples/genesis_event1.json` and `examples/events_event1.json` as the schema-valid `EVENT1` stream-custody ledger example on its own placeholder root, plus the `profiles/event/SATROOT-EVENT-1.md` draft.
- Adds `python -m satroot_event_profile_smoke`, `satroot-event-profile-smoke`, and `scripts/run_event_profile_smoke.py` as the dedicated event lane: replays the checked-in example, scaffolds a fresh single-stream demo ledger, and verifies a signed bundle over it; demo-catalog-matrix promotion for the event lane is deferred to a future milestone.

## v1.0-draft-freeze - 2026-08-19

- Declares the `SATROOT-1` kernel rules frozen as the v1 protocol draft: no kernel-rule, lane, or dependency changes in this release.
- Completes one full documentation consistency pass aligning `SPEC.md`, `README.md`, `ARCHITECTURE.md`, `BOUNDARIES.md`, `ROADMAP.md`, `ANCHORS.md`, and the five profile drafts with what the released lanes actually prove: removes stale "future"/"v0.1" claims for shipped profiles and schemes, corrects the operator-proof surface count and anchored-lane check count, adds the anchored loop to the claims-discipline and boundaries statements, documents the released SPEC section 4 builder and verifier under the envelope section, and adds an anchoring-loop subsection to the architecture doc.
- Fixes the kernel module docstring, which referenced a nonexistent `verify_signature_placeholder` function and a stale v0.1 label, to name the real `demo_signature_verifier` placeholder and the shipped `hmac-sha256` and `ed25519` schemes.

## v0.9-anchored-operator-proof - 2026-08-19

- Promotes the four anchored-surface lanes — anchored demo, anchored publication, on-chain envelope, and envelope verification — into the top-level operator proof on their placeholder defaults, so the canonical proof and the local release gate cover the whole anchoring loop on every run.
- Keeps non-crypto installs green: the two ed25519-dependent anchored surfaces skip gracefully with an explicit skip record when the `[crypto]` extra is unavailable, while the offline envelope surfaces always run.

## v0.8-envelope-verification - 2026-08-19

- Adds `python -m satroot_envelope_verification_smoke`, `satroot-envelope-verification-smoke`, and `scripts/run_envelope_verification_smoke.py` as a fully offline verifier that parses serialized transaction bytes, confirms they hash to an expected transaction id, locates the single zero-value SPEC section 4 `SATROOT1` envelope output, and matches it byte for byte against the deterministically rebuilt commitment; with no transaction supplied it builds and verifies a synthetic offline demo transaction.
- Verifies the real broadcast envelope transaction from operator-fetched raw bytes with every check passing, and extends `ANCHORS.md` with the verified confirmation as the continuation of the anchored-run record.

## v0.7-onchain-envelope - 2026-08-19

- Adds `python -m satroot_onchain_envelope_smoke`, `satroot-onchain-envelope-smoke`, and `scripts/run_onchain_envelope_smoke.py` as a deterministic, fully offline builder for the SPEC section 4 on-chain envelope: `OP_FALSE OP_RETURN "SATROOT1" <content-type> <payload>` carrying a canonical JSON commitment of the namespace `root_id` and semantic state hash, with a round-trip parser that rejects malformed scripts and foreign protocol tags.
- Keeps the repository network-free by design: the lane builds and verifies the envelope script offline, and the operator broadcasts it out-of-band exactly as the anchor outpoint itself was created.
- Broadcasts the real envelope for the anchored testnet namespace out-of-band and extends `ANCHORS.md` with the envelope transaction id as the continuation of the anchored-run record.

## v0.6-anchored-publication - 2026-08-19

- Adds `python -m satroot_anchored_publication_smoke`, `satroot-anchored-publication-smoke`, and `scripts/run_anchored_publication_smoke.py` to publish the anchored identity demo namespace through the full publication ladder — signed bundles, release, catalog, network, and registry workspace — with ed25519 signing end to end, verifying the root binding in every generated bundle genesis and emitting published-artifact hashes for the anchored-run record.
- Fixes the singleton branch of the demo catalog workspace bundle generator to forward `root_id`, `issuer`, `rules_hash`, and `nonce` structure overrides into the generated bundle instead of silently dropping them, so runtime root injection now produces lint-clean workspaces whose bundle geneses actually carry the requested root.
- Publishes the real anchored testnet namespace through the new lane and extends `ANCHORS.md` with the published-artifact hashes as the continuation of the anchored-run record.

## v0.5-root-anchoring - 2026-08-19

- Binds the first real one-satoshi BSV testnet outpoint through the anchored demo lane with every lane check passing, and adds `ANCHORS.md` as the sole checked-in record of intentional anchored runs, keeping every example, preset, and default on placeholder roots.
- Slims the GitHub Actions test workflow to one Linux job that runs installed-module import smoke and then the release-gate umbrella, dropping the Windows matrix leg and the intermediate per-surface smoke steps that the gate's operator proof and chunked pytest already re-run, and cancels superseded in-progress runs for the same ref.
- Adds `python -m satroot_anchored_demo_smoke`, `satroot-anchored-demo-smoke`, and `scripts/run_anchored_demo_smoke.py` as the first `v0.5-root-anchoring` lane: one dedicated identity demo namespace whose `root_id` defaults to a distinct placeholder and can be bound to a real one-satoshi outpoint via `--root-id` at run time, with its lifecycle signed and verified through the ed25519 path instead of the demo or hmac schemes.
- Demonstrates the root lifecycle rule inside that lane's report: the semantic state hash binds the `root_id`, replay is deterministic, events carrying a foreign root are rejected with `root_id mismatch`, and no ledger event kind models root custody, so on-chain root movement stays out-of-band by construction.
- Registers the anchored lane in packaging metadata, packaging assertions, release-gate import smoke, the CI installed-import check, and the release checklist, which now names it as the only lane ever intended to carry a real outpoint and only via its runtime flag, never in checked-in files.

## v0.4-publication-federation - 2026-08-18

- Moves the release-gate smoke to the final umbrella step of the GitHub Actions test workflow so CI ordering matches the documented flow of narrower smoke surfaces before one consolidated gate.
- Generalizes the release checklist so its tag steps target the current milestone tag instead of a hardcoded `v0.1-genesis`, and syncs its installed-import check with the full packaged module list used in CI.
- Cuts the accumulated unreleased changelog into explicit `v0.1-genesis`, `v0.2-stable-profile`, `v0.3-namespace-expansion`, and `v0.4-publication-federation` milestone sections.
- Bumps the packaged version metadata to `0.4.0` in `pyproject.toml` and `CITATION.cff` so installed distributions report the released milestone line.
- Marks `v0.4-publication-federation` as the completed publication-federation milestone and points the roadmap at `v0.5-root-anchoring` as the next concrete build target.
- Adds `python -m satroot_federated_registry_collection_smoke`, `satroot-federated-registry-collection-smoke`, and `scripts/run_federated_registry_collection_smoke.py` for a higher mixed-profile proof surface that reruns the federation smoke, reuses the generated top-level publication-registry-workspace collection, bootstraps a top-level publication-registry publication from that collection-backed preset, exports the resulting publication back into a preset, and bootstraps it again for a collection-backed round trip.
- Runs the new federated registry collection smoke workflow in CI, adds the packaged module to installed-import verification and packaging assertions, and ignores the generated smoke workspaces by default so the collection-backed top-level publication-registry publication surface is easy to rerun from both source and editable installs.
- Promotes the new federated registry collection smoke into the top-level operator proof and release-gate import smoke so the canonical proof and local pre-tag gate both cover the collection-backed top-level registry publication path.
- Adds `python -m satroot_release_gate_smoke`, `satroot-release-gate-smoke`, and `scripts/run_release_gate_smoke.py` for one local pre-tag release gate that runs installed-module import smoke, the top-level operator proof, and chunked pytest together and emits one consolidated gate report.
- Adds the packaged release-gate module to installed-import verification, packaging assertions, release guidance, local ignore rules, and the final GitHub Actions umbrella check so the repo now has one canonical command for the full local release check before tagging.
- Adds `python -m satroot_operator_proof_smoke`, `satroot-operator-proof-smoke`, and `scripts/run_operator_proof_smoke.py` for one top-level operator proof surface that runs the stable/machine publication ladder, the singleton publication ladder, and the mixed-profile federation smoke together and emits one consolidated proof report.
- Runs the new operator-proof smoke workflow in CI, adds the packaged proof module to installed-import verification and packaging assertions, and ignores the generated proof workspaces by default so the repo now has one command for the full currently released operator story.
- Adds `python -m satroot_publication_ladder_smoke`, `satroot-publication-ladder-smoke`, and `scripts/run_publication_ladder_smoke.py` for one umbrella operator proof that runs the stable/machine bundle-index, release-catalog, and release-catalog-index matrix smokes together and emits one consolidated ladder report.
- Runs the new publication-ladder smoke workflow in CI, adds the packaged ladder module to installed-import verification and packaging assertions, and ignores the generated ladder workspaces by default so the stable/machine operator ladder has one easy rerun surface alongside the singleton ladder.
- Adds `python -m satroot_singleton_publication_ladder_smoke`, `satroot-singleton-publication-ladder-smoke`, and `scripts/run_singleton_publication_ladder_smoke.py` for one umbrella operator proof that runs the receipt/identity/license singleton bundle-index, release-catalog, and release-catalog-index matrix smokes together and emits one consolidated ladder report.
- Runs the new singleton publication-ladder smoke workflow in CI, adds the packaged ladder module to installed-import verification and packaging assertions, and ignores the generated ladder workspaces by default so the full singleton operator ladder has one easy rerun surface.
- Adds `python -m satroot_receipt_demo_release_catalog_smoke`, `satroot-receipt-demo-release-catalog-smoke`, `python -m satroot_identity_demo_release_catalog_smoke`, `satroot-identity-demo-release-catalog-smoke`, `python -m satroot_license_demo_release_catalog_smoke`, `satroot-license-demo-release-catalog-smoke`, `python -m satroot_singleton_demo_release_catalog_matrix_smoke`, and `satroot-singleton-demo-release-catalog-matrix-smoke` for packaged singleton operator smokes that stage receipt, identity, and license presets, generate reusable signed release collections, publish per-profile release catalogs, and verify those middle singleton publication layers through compact reports.
- Adds `python -m satroot_receipt_demo_release_catalog_index_smoke`, `satroot-receipt-demo-release-catalog-index-smoke`, `python -m satroot_identity_demo_release_catalog_index_smoke`, `satroot-identity-demo-release-catalog-index-smoke`, `python -m satroot_license_demo_release_catalog_index_smoke`, `satroot-license-demo-release-catalog-index-smoke`, `python -m satroot_singleton_demo_release_catalog_index_matrix_smoke`, and `satroot-singleton-demo-release-catalog-index-matrix-smoke` for packaged singleton operator smokes that stage receipt, identity, and license presets, generate reusable signed release collections, publish per-profile release catalogs and release-catalog indexes above them, and verify the higher singleton publication ladder through compact reports.
- Runs the new singleton demo release-catalog and release-catalog-index matrix smoke workflows in CI, adds the packaged singleton catalog modules to installed-import verification and packaging assertions, and ignores the generated singleton catalog workspaces by default so the receipt/identity/license publication ladder is now covered from bundle index through catalog and catalog-index layers.
- Adds `python -m satroot_receipt_demo_bundle_index_smoke`, `satroot-receipt-demo-bundle-index-smoke`, `python -m satroot_identity_demo_bundle_index_smoke`, `satroot-identity-demo-bundle-index-smoke`, `python -m satroot_license_demo_bundle_index_smoke`, `satroot-license-demo-bundle-index-smoke`, `python -m satroot_singleton_demo_bundle_index_matrix_smoke`, and `satroot-singleton-demo-bundle-index-matrix-smoke` for packaged singleton operator smokes that stage receipt, identity, and license presets, generate reusable signed bundle collections, build per-profile bundle indexes, and verify those lower singleton publication layers through compact reports.
- Runs the new singleton demo bundle-index matrix smoke workflow in CI, adds the packaged singleton bundle-index smoke modules to installed-import verification, packaging assertions, release guidance, and local ignore rules so the receipt/identity/license lanes now have dedicated lower-ladder operator coverage beneath the existing profile-matrix and federation surfaces.
- Adds `python -m satroot_machine_demo_bundle_index_smoke`, `satroot-machine-demo-bundle-index-smoke`, `python -m satroot_stable_demo_bundle_index_smoke`, `satroot-stable-demo-bundle-index-smoke`, `python -m satroot_demo_bundle_index_matrix_smoke`, and `satroot-demo-bundle-index-matrix-smoke` for packaged operator smokes that stage checked-in stable and machine presets, generate reusable signed bundle collections, build matching bundle indexes, and verify the lower release ladder through one compact report surface.
- Runs the new demo bundle-index matrix smoke workflow in CI, adds the packaged bundle-index smoke modules to installed-import verification, packaging assertions, release guidance, and local ignore rules so the stable/machine operator ladder now has dedicated bundle-index coverage beneath the existing release-catalog and release-catalog-index layers.
- Adds `python -m satroot_machine_demo_release_catalog_index_smoke`, `satroot-machine-demo-release-catalog-index-smoke`, `python -m satroot_stable_demo_release_catalog_index_smoke`, `satroot-stable-demo-release-catalog-index-smoke`, `python -m satroot_demo_release_catalog_index_matrix_smoke`, and `satroot-demo-release-catalog-index-matrix-smoke` for packaged higher-level operator smokes that stage multiple checked-in stable and machine catalog presets, generate signed multi-release collections, bootstrap matching release catalog publications, bootstrap release catalog index publications above them, and verify the whole lower release ladder through one compact report surface.
- Runs the new demo release-catalog-index matrix smoke workflow in CI, adds the packaged release-catalog-index smoke modules to installed-import verification, packaging assertions, release guidance, and local ignore rules so the higher-level machine/stable operator lane now covers both catalog and index layers from source and editable installs.
- Adds `python -m satroot_machine_demo_release_catalog_smoke`, `satroot-machine-demo-release-catalog-smoke`, `python -m satroot_stable_demo_release_catalog_smoke`, `satroot-stable-demo-release-catalog-smoke`, `python -m satroot_demo_release_catalog_matrix_smoke`, and `satroot-demo-release-catalog-matrix-smoke` for packaged higher-level operator smokes that stage multiple checked-in stable and machine catalog presets, generate signed multi-release collections, bootstrap matching release catalog publications, and verify those lower publication layers through one compact report surface.
- Runs the new demo release-catalog matrix smoke workflow in CI, adds the packaged release-catalog smoke modules to installed-import verification, packaging assertions, release guidance, and local ignore rules so the higher-level machine/stable operator lane stays easy to re-run from source and editable installs.
- Adds `python -m satroot_profile_federation_smoke`, `satroot-profile-federation-smoke`, and `scripts/run_profile_federation_smoke.py` for a first `v0.4-publication-federation` operator wrapper that reuses the released profile matrix, freezes the resulting per-profile demo-catalog, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace outputs into collections, proves and snapshots a shared mixed-profile publication catalog workspace plus publication registry workspace above the federated network, and now round-trips the federated catalog workspace, stack, network, and top-level registry workspace back through exported nested presets.
- Runs the federation smoke workflow in CI and adds the packaged federation smoke module to installed-import verification, packaging assertions, release guidance, and local ignore rules so the new `v0.4` proof surface is easy to run from both source and editable installs.

## v0.3-namespace-expansion - 2026-08-18

- Adds `python -m satroot_profile_matrix_smoke`, `satroot-profile-matrix-smoke`, and `scripts/run_profile_matrix_smoke.py` for a single end-to-end verification surface that runs the released stable, machine, receipt, identity, and license lanes and writes one consolidated report.
- Replaces the five separate CI profile-smoke execution steps with one released profile-matrix smoke step, adds the packaged matrix smoke module to installed-import verification, and ignores generated `.tmp_profile_matrix_smoke*/` workspaces by default.
- Marks `v0.3-namespace-expansion` as the completed namespace milestone and points the roadmap at `v0.4-publication-federation` as the next operator-focused build target.
- Tightens the roadmap around the post-`v0.2-stable-profile` state by recording the released stable-profile deliverable and naming `v0.3-namespace-expansion` as the next concrete milestone.
- Adds `python -m satroot_license_profile_smoke`, `satroot-license-profile-smoke`, and `scripts/run_license_profile_smoke.py` for an explicit SATROOT-LICENSE-1 end-to-end smoke pass that replays the checked-in `LICENSE1` example and generates, summarizes, and lints a full singleton publication registry workspace from the checked-in license preset.
- Runs the license-profile smoke workflow in CI, adds the packaged license smoke module to the installed-import check, and ignores generated `.tmp_license_profile_smoke*/` workspaces so local verification stays tidy by default.
- Adds `python -m satroot_identity_profile_smoke`, `satroot-identity-profile-smoke`, and `scripts/run_identity_profile_smoke.py` for an explicit SATROOT-IDENTITY-1 end-to-end smoke pass that replays the checked-in `IDENTITY1` example and generates, summarizes, and lints a full singleton publication registry workspace from the checked-in identity preset.
- Runs the identity-profile smoke workflow in CI, adds the packaged identity smoke module to the installed-import check, and ignores generated `.tmp_identity_profile_smoke*/` workspaces so local verification stays tidy by default.
- Adds `python -m satroot_receipt_profile_smoke`, `satroot-receipt-profile-smoke`, and `scripts/run_receipt_profile_smoke.py` for an explicit SATROOT-RECEIPT-1 end-to-end smoke pass that replays the checked-in `RECEIPT1` example and generates, summarizes, and lints a full singleton publication registry workspace from the checked-in receipt preset.
- Runs the receipt-profile smoke workflow in CI, adds the packaged receipt smoke module to the installed-import check, and ignores generated `.tmp_receipt_profile_smoke*/` workspaces so local verification stays tidy by default.
- Adds `python -m satroot_machine_profile_smoke`, `satroot-machine-profile-smoke`, and `scripts/run_machine_profile_smoke.py` for an explicit SATROOT-MACHINE-1 end-to-end smoke pass that replays the checked-in `APICREDIT1` example and generates, summarizes, and lints a full machine publication registry workspace through the direct machine builder lane.
- Runs the machine-profile smoke workflow in CI, adds the packaged machine smoke module to the installed-import check, and ignores generated `.tmp_machine_profile_smoke*/` workspaces so local verification stays tidy by default.

## v0.2-stable-profile - 2026-08-18

- Adds `python -m satroot_stable_profile_smoke`, `satroot-stable-profile-smoke`, and `scripts/run_stable_profile_smoke.py` for an explicit SATROOT-STABLE-1 end-to-end smoke pass that replays the checked-in `USDROOT1` example and generates, summarizes, and lints a full stable publication registry workspace through the direct stable builder lane.
- Runs the stable-profile smoke workflow in CI, adds the packaged stable smoke module to the installed-import check, and ignores generated `.tmp_stable_profile_smoke*/` workspaces so local verification stays tidy by default.

## v0.1-genesis - 2026-08-17

- Adds `python -m satroot_test`, `satroot-test`, and `scripts/run_pytest_chunked.py` for deterministic chunked pytest execution across the full `tests/` tree, keeps the repo-local wrapper usable from a fresh checkout by wiring `src/` directly, and adds a matching GitHub Actions workflow for repository verification without a single long-lived pytest process.
- Clarifies the README and release guidance so plain `pytest` is framed as a smoke path while chunked execution is the preferred full-suite verification route.
- Expands the GitHub Actions test workflow to cover both `ubuntu-latest` and `windows-latest`, and adds `workflow_dispatch` plus non-fail-fast matrix behavior for easier cross-platform verification and reruns.
- Adds an explicit installed-module import smoke check in CI and the release checklist so packaging regressions are caught even when repo-local pytest `pythonpath` injection would otherwise hide them.
- Adds first-class CLI summary commands for reusable collection layers such as bundle, release, release-catalog, publication-metadata-bundle, demo-catalog-workspace, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace collections.
- Adds matching first-class CLI lint commands for those reusable collection layers so copied bundle, release, catalog, metadata-bundle, demo-catalog, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace collections can be validated directly from their frozen `summary.json` roots.
- Adds `bootstrap-publication-stack-collection`, `bootstrap-machine-publication-stack-collection`, and `bootstrap-stable-publication-stack-collection` for copying publication stack workspaces into reusable higher-level collections.
- Extends publication-network presets plus `bootstrap-publication-network`, `bootstrap-machine-publication-network`, `bootstrap-stable-publication-network`, `publish-publication-network`, `publish-machine-publication-network`, and `publish-stable-publication-network` so they can consume a saved `publication_stack_collection_dir`.
- Adds `bootstrap-publication-network-collection`, `bootstrap-machine-publication-network-collection`, and `bootstrap-stable-publication-network-collection` for copying publication network workspaces into reusable higher-level collections.
- Extends publication-registry-workspace presets plus `bootstrap-publication-registry-workspace`, `bootstrap-machine-publication-registry-workspace`, `bootstrap-stable-publication-registry-workspace`, `publish-publication-registry-workspace`, `publish-machine-publication-registry-workspace`, and `publish-stable-publication-registry-workspace` so they can consume a saved `publication_network_collection_dir` containing exactly one publication network workspace.
- Preserves `publication_network_collection_dir` provenance during publication-registry-workspace preset export so collection-backed registry workspaces can round-trip without collapsing back to direct publication-network paths.
- Preserves `publication_stack_collection_dir` provenance inside generated publication-network presets and bootstrap flows even when nested stack presets are emitted, so collection-backed network lanes can round-trip without duplicating execution inputs or losing their original frozen-stack lineage.
- Preserves `bundle_collection_dir`, `release_collection_dir`, and `release_catalog_collection_dir` provenance inside generated lower release-layer artifacts so exported bundle-index, release-catalog, and release-catalog-index presets can round-trip collection-backed builds without flattening back to explicit directory lists.
- Preserves `publication_metadata_bundle_collection_dir` provenance inside generated publication-metadata catalogs and exported presets so catalog build/publish/bootstrap flows can round-trip collection-backed metadata lanes without flattening back to explicit bundle directories.
- Preserves `publication_registry_workspace_dir` provenance inside generated publication registries and exported presets so top-level registry build/publish/bootstrap flows can round-trip workspace-backed component inputs without flattening back to three explicit publication directories.
- Adds checked-in generic, machine, and stable workspace-backed publication-registry example presets so the new `publication_registry_workspace_dir` flow is represented in the reusable example set.
- Adds checked-in generic, machine, and stable collection-backed example presets for bundle indexes, release catalogs, and release-catalog indexes so frozen generated artifact sets have reusable example entry points at each lower aggregation layer.
- Adds checked-in generic, machine, and stable collection-backed example presets for publication networks and publication-registry workspaces so frozen publication-stack and publication-network collections have reusable higher-layer example entry points too.
- Adds `examples/README.md` so the checked-in generic, machine, stable, and collection-backed SATROOT preset trees have one navigable entry point.
- Extends lower release-layer path resolution so bundle-index, release-catalog, and release-catalog-index commands can consume generated workspace roots directly, including machine/stable demo release roots, demo catalog workspaces, and publication stack workspaces.
- Extends upper publication-layer path resolution so publication-metadata-catalog and publication-registry build/publish/bootstrap commands can consume generated publication catalog, publication network, and publication registry workspace roots directly, including matching `summary.json` files.
- Adds `bootstrap-release-catalog-collection`, `bootstrap-machine-release-catalog-collection`, and `bootstrap-stable-release-catalog-collection` for copying signed release catalog directories into reusable higher-level collections.
- Extends release-catalog-index presets plus `build-release-catalog-index`, `publish-release-catalog-index`, and `bootstrap-release-catalog-index-publication` across generic, machine, and stable lanes so they can consume a saved `release_catalog_collection_dir` instead of repeating release-catalog discovery.
- Fixes release-catalog-index bootstrap wrapper preset loading so the generic, machine, and stable commands validate the correct preset profile before publication.
- Adds `bootstrap-release-collection`, `bootstrap-machine-release-collection`, and `bootstrap-stable-release-collection` for copying signed release directories into reusable multi-release collections.
- Extends release-catalog presets plus `build-release-catalog`, `publish-release-catalog`, and `bootstrap-release-catalog-publication` across generic, machine, and stable lanes so they can consume a saved `release_collection_dir` instead of repeating release-dir discovery.
- Fixes release-catalog bootstrap wrapper preset loading so the generic, machine, and stable commands validate the correct preset profile before publication.
- Adds stable-only `SATROOT-DEMO-CATALOG-PRESET` support to `bootstrap-stable-demo`, `bootstrap-stable-demo-bundle`, and `bootstrap-stable-demo-release`.
- Adds `bootstrap-stable-demo-catalog` for generating single-profile SATROOT-STABLE-1 catalog workspaces, including stable-only preset and release-metadata defaults.
- Adds `bootstrap-stable-publication-stack` and `bootstrap-stable-publication-network` for stable-only higher-level catalog packaging from validated `SATROOT-STABLE-1` preset trees.
- Adds `publish-stable-publication-stack`, `publish-stable-publication-network`, `export-stable-publication-stack-preset`, and `export-stable-publication-network-preset` for stable-only higher-level workspace reuse and preset round-trips.
- Adds `bootstrap-stable-publication-catalog-workspace` and `bootstrap-stable-publication-registry-workspace` for stable-only publication descriptor, metadata, and registry lanes, including preset-driven stable wrapper coverage.
- Adds `publish-stable-publication-catalog-workspace`, `publish-stable-publication-registry-workspace`, `export-stable-publication-catalog-workspace-preset`, and `export-stable-publication-registry-workspace-preset` for stable-only workspace reuse and round-trip preset export.
- Adds `export-stable-publication-descriptor-index-preset`, `export-stable-publication-metadata-catalog-preset`, and `export-stable-publication-registry-preset` for stable-only component publication preset export.
- Adds `export-stable-release-catalog-preset` and `export-stable-release-catalog-index-preset` for stable-only release catalog preset export parity with the machine lane.
- Extends release catalog and release catalog index preset export so lower release layers can emit nested bundle-index and release-catalog preset trees while preserving source workspace directories for round-trip reuse.
- Expands the checked-in release catalog and release catalog index example presets to include nested bundle-index and release-catalog preset references, and hardens machine/stable release-layer preset loading plus example-tree coverage around those nested release preset chains.
- Hardens publication stack and publication network preset loading so nested catalog and stack preset references are validated eagerly, and adds staged end-to-end bootstrap coverage for the checked-in generic, machine, and stable example preset trees.
- Hardens machine/stable publication descriptor index, publication metadata catalog, and publication registry preset handling across build, publish, and bootstrap wrappers, and adds executable generic example-preset coverage for the checked-in top publication layer presets.
- Adds executable bootstrap coverage for the checked-in generic, machine, and stable publication descriptor index, publication metadata catalog, and publication registry example presets, and fills the remaining stable-only preset override coverage gaps in the top publication layer.
- Adds `bootstrap-publication-metadata-bundle-collection`, `bootstrap-machine-publication-metadata-bundle-collection`, and `bootstrap-stable-publication-metadata-bundle-collection` for building reusable publication metadata bundle sets from multiple discovered artifacts, with collection summaries and typed wrapper validation.
- Adds `bootstrap-bundle-collection`, `bootstrap-machine-bundle-collection`, and `bootstrap-stable-bundle-collection` for copying signed bundle directories into reusable lower release-layer collections.
- Extends bundle-index presets plus `build-bundle-index`, `publish-release`, and `bootstrap-release-publication` across generic, machine, and stable lanes so they can consume a saved `bundle_collection_dir` instead of repeating bundle-dir discovery.
- Extends `bootstrap-publication-catalog-workspace` so it can copy and reuse an existing publication metadata bundle collection via direct CLI path or preset reference, while preserving source-collection provenance in the workspace summary.
- Extends generic `bootstrap-publication-registry-workspace` so it can consume nested publication-catalog-workspace presets, including collection-backed catalog workspace presets, and preserves those nested collection references through generated registry-workspace preset exports.
- Extends generic publication stack and publication network bootstraps so they can consume workspace-directory references from exported presets, and updates preset export to fall back to those workspace references only when nested preset paths are unavailable.
- Extends publication-registry-workspace preset export and bootstrap so the top workspace layer can round-trip nested publication-network presets, including generated stack and catalog preset trees when requested, and updates the checked-in registry-workspace example presets to use those nested network references.
- Extends publication-registry-workspace publish flows, including the machine and stable wrappers, so exported presets can round-trip nested publication-network presets by materializing a copied `publication_network/` when release, release-catalog, and release-catalog-index signing key ids are supplied.
- Extends publication catalog workspace and publication registry workspace preset export so higher workspace layers can emit nested descriptor-index, metadata-catalog, catalog-workspace, and publication-registry preset files while preserving their existing round-trip source references.
- Expands the checked-in publication catalog workspace and publication registry workspace example presets to include nested component preset references, and adds machine-specific workspace example presets alongside the existing generic and stable variants.
- Hardens publication catalog workspace and publication registry workspace preset loading so nested preset references are validated eagerly, and adds staged end-to-end bootstrap coverage for the checked-in generic, machine, and stable workspace preset trees.
- Adds `export-stable-bundle-index-preset` for stable-only bundle-index preset export parity with the machine lane.
- Adds `bootstrap-stable-publication-descriptor-index-publication`, `bootstrap-stable-publication-metadata-bundle`, `bootstrap-stable-publication-metadata-catalog-publication`, and `bootstrap-stable-publication-registry-publication` for stable-only component publication generation.
- Adds `build-stable-release-catalog`, `build-stable-release-catalog-manifest`, `publish-stable-release-catalog`, `bootstrap-stable-release-catalog-publication`, `build-stable-release-catalog-index`, `build-stable-release-catalog-index-manifest`, `publish-stable-release-catalog-index`, and `bootstrap-stable-release-catalog-index-publication` for stable-only release catalog packaging parity with the machine lane.
- Adds `build-stable-bundle-index`, `build-stable-release-manifest`, `publish-stable-release`, and `bootstrap-stable-release-publication` for stable-only release packaging parity beneath the catalog layer.
- Adds `build-stable-publication-descriptor-index`, `build-stable-publication-descriptor-index-manifest`, `build-stable-publication-metadata-manifest`, `build-stable-publication-metadata-catalog`, `build-stable-publication-metadata-catalog-manifest`, `build-stable-publication-registry`, and `build-stable-publication-registry-manifest` for stable-only component build/sign parity with the machine lane.
- Adds `publish-publication-descriptor-index`, `publish-machine-publication-descriptor-index`, `publish-stable-publication-descriptor-index`, `publish-publication-metadata-bundle`, `publish-machine-publication-metadata-bundle`, `publish-stable-publication-metadata-bundle`, `publish-publication-metadata-catalog`, `publish-machine-publication-metadata-catalog`, `publish-stable-publication-metadata-catalog`, `publish-publication-registry`, `publish-machine-publication-registry`, and `publish-stable-publication-registry` for signed component publication-directory generation from existing signer material.
- Adds checked-in machine-only and stable-only example presets for bundle indexes, release catalogs, release catalog indexes, publication descriptor indexes, publication metadata catalogs, and publication registries.
- Lets bundle, release, release-catalog, and release-catalog-index build/publish commands reuse saved `inventory-artifacts` reports via `--inventory-json`.
- Extends that same `--inventory-json` reuse pattern across publication descriptor index, publication metadata catalog, publication registry, publication catalog workspace, and publication registry workspace build/bootstrap flows.
- Extends `--inventory-json` reuse into top-level publication-registry publication bootstraps, including the machine-only wrapper.
- Extends `--inventory-json` reuse into publication stack and publication network publish flows, including the machine-only wrappers.
- Extends `--inventory-json` reuse into publication catalog workspace and publication registry workspace publish flows, including the machine-only wrappers.
- Adds preset support to `publish-publication-stack`, `publish-machine-publication-stack`, `publish-publication-network`, and `publish-machine-publication-network`.
- Adds preset support to `publish-publication-catalog-workspace`, `publish-machine-publication-catalog-workspace`, `publish-publication-registry-workspace`, and `publish-machine-publication-registry-workspace`.
- Extends exported publication-stack presets with source `catalog_workspace_dirs` so they can drive publish flows as well as bootstrap flows.
- Extends exported publication-network presets with source `publication_stack_dirs` so they can drive publish flows as well as bootstrap flows.
- Makes machine publication-registry-workspace preset export fall back to `release_catalog_index_dir` when the original source network is not machine-valid, preserving machine-only preset reusability.
- Lets machine publication-registry bootstrap consume an existing machine publication catalog workspace via direct CLI path or preset reference.
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
- Adds first-class `freeze` events for authority-controlled account locking and unlocking.
- Adds `bundle-index-summary` and `bundle-index-lint` commands for inspecting unsigned multi-bundle bundle indexes before release signing.
- Makes publication descriptor indexes and publication metadata catalogs first-class detected artifact kinds across inventory, reports, descriptor export, and read-only inspection.
- Makes raw standalone `bundle_index.json` artifacts first-class detected artifact kinds across inventory, reports, descriptor export, descriptor-index discovery, and publication metadata catalog flows.
- Makes bootstrapped publication metadata bundles first-class detected artifact kinds across inventory, reports, descriptor export, descriptor-index discovery, and machine-only wrapper flows.
- Adds `publication-metadata-bundle-summary` and `publication-metadata-bundle-lint` commands for inspecting bootstrapped publication metadata bundles plus packaged artifact drift.
- Adds `build-machine-publication-metadata-manifest` for enforcing SATROOT-MACHINE-1 validation before publication metadata manifest signing.
- Adds `bootstrap-machine-publication-metadata-bundle` for enforcing SATROOT-MACHINE-1 validation before publication metadata bundle signing.
- Adds a `bootstrap-stable-demo` workflow for generating runnable reference-only SATROOT-STABLE-1 ledgers.
- Adds a `bootstrap-stable-demo-bundle` workflow for generating signed reference-only SATROOT-STABLE-1 bundles.
- Adds a `bootstrap-stable-demo-release` workflow for generating signed reference-only SATROOT-STABLE-1 bundles plus release directories.
- Adds a `bootstrap-singleton-demo` workflow for generating runnable receipt, identity, and license lifecycle ledgers.
- Adds a `bootstrap-singleton-demo-bundle` workflow for generating signed receipt, identity, and license lifecycle bundles.
- Adds a `bootstrap-singleton-demo-release` workflow for generating signed receipt, identity, and license bundles plus release directories.
- Hardens Ed25519 stable demo bundle/release coverage, including verifier-only bundle verification.
- Adds a `consume-machine-credit` lifecycle helper for burn-on-use `SATROOT-MACHINE-1` ledgers.
- Adds a `transfer-singleton-object` lifecycle helper for receipt, identity, and license ledgers.
- Adds an `archive-singleton-object` lifecycle helper for receipt, identity, and license ledgers.
- Adds a `retire-singleton-object` lifecycle helper for archived receipt, identity, and license ledgers.
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
