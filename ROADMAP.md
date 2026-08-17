# SATROOT Roadmap

## Project position

SATROOT is a BSV-anchored overlay protocol for deterministic semantic assets.

The base idea is:

`1 satoshi -> 1 root-bound namespace -> unbounded protocol-defined state`

The project should remain disciplined about this separation:

- BSV anchors the root satoshi and provides ordering, publication, and custody.
- SATROOT defines semantic balances, rights, and validity rules above that root.

## Current deliverable

`v0.2` is the stable-profile proof artifact for `SATROOT-1`.

It proves that one native satoshi can anchor an arbitrary semantic ledger without claiming subdivision below one satoshi, and that the first reference-only stable profile can be replayed and published end to end without changing the base primitive.

Current scope:

- root-bound namespace via `root_id`
- token genesis
- `mint`, `transfer`, `burn`, `freeze`, and `rotate-authority`
- sequence enforcement
- deterministic replay
- supply invariants
- example token `FLOOR1`
- example stable token `USDROOT1`
- stable-only smoke verification from replay through publication registry workspace

Release status:

- `v0.1-genesis` has been tagged and pushed from this repository.
- The reference CLI, example preset tree, collection summary/lint surface, chunked test runner, and CI verification flow are now part of the frozen base deliverable.
- `v0.2-stable-profile` has been tagged and pushed from this repository.
- The `SATROOT-STABLE-1` reference-only lane now has a dedicated smoke workflow, packaged entrypoint, CI coverage, and a tagged publication-path milestone.

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
- `SATROOT-IDENTITY-1` draft exists in this repo.
- `IDENTITY1` examples are included as the first identity-object implementation artifact.
- `SATROOT-LICENSE-1` draft exists in this repo.
- `LICENSE1` examples are included as the first license-object implementation artifact.

Recommended order inside `v0.3`:

1. machine-credit lane
2. receipt/invoice lane
3. identity/authority lane
4. license/usage-right lane

That order keeps the project close to machine-native accounting and operational workflows before moving into heavier rights semantics.

## Immediate next milestone

If work resumes right away, the best next milestone is:

`v0.3-namespace-expansion`

The success condition should be narrow:

- the base `SATROOT-1` kernel remains unchanged in principle,
- `SATROOT-MACHINE-1` becomes the first post-stable expansion lane to get the same crisp replay-to-publication verification story,
- namespace expansion stays machine-accounting-first before drifting into heavier legal or rights semantics,
- the docs keep separating protocol state from legal and economic claims as strictly as the current base and stable-profile lanes.

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
