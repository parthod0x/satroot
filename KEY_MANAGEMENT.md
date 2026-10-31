# SATROOT Key Management Guidance

This document gives operational guidance for handling signing keys above the
frozen `SATROOT-1` signature schemes. It adds no new kernel rules, no new
schemes, and no new dependencies: everything here composes the released
`demo`, `hmac-sha256`, and `ed25519` paths.

## Scheme selection

- `demo` is a placeholder for tests and examples only. It verifies nothing.
  Never use it for state anyone else must trust.
- `hmac-sha256` authenticates events with shared secrets plus key identifiers.
  Use it only inside one trust domain where every verifier may also sign.
- `ed25519` is the public-key path and the default for anything published
  outside one trust domain. It is what the anchored lanes use end to end, and
  it requires the `[crypto]` extra (`pip install -e ".[crypto]"`).

## Custody separation

SATROOT deliberately separates three kinds of custody. Keep them separate
operationally too:

- **Root satoshi custody** lives in the operator's wallet, entirely outside
  this repository. Moving the root satoshi never signs, and never needs, a
  SATROOT event.
- **Event signing keys** authorize semantic state transitions. In a version
  `0.2` ledger each account's key is bound at genesis (`account_keys`) and
  changed with `bind-key` events inside the ledger itself.
- **Publication signing keys** (`release-key`, `catalog-key`, registry and
  index key ids) sign artifact manifests, not ledger events. Compromise of a
  publication key lets someone republish artifacts, not rewrite ledger state.

A compromise in one layer must not be treated as a compromise of the others,
and no key in any layer can move the root satoshi.

## Signer-to-key binding (3.0.0)

A version `0.2` ledger binds keys to accounts in the kernel (SPEC section
6.7):

- **Genesis declares `account_keys`**, account to `signature_key_id`, and is
  signed with the mint authority's bound key. `sign_ledger_events` and
  `bind_genesis_keys` produce such a genesis.
- **Every record must be signed with its signer's bound key.** A key the
  verifier holds can no longer sign as an account it is not bound to.
- **`bind-key` changes a binding.** The authority binds an account that has
  no key; only the account itself can rebind its key. The authority cannot
  take an account's key.
- **Value sits only in bound accounts.** Genesis may credit only bound
  accounts, and a mint or transfer to an unbound account is rejected. So the
  authority's power to bind a new account never reaches one that holds funds.
- **`rotate-authority`** requires the new authority to be bound already.

Before 3.0.0 the kernel compared the `signer` string only, so any registered
key could sign as any account, and this document recommended an
application-level key-to-account policy. That is no longer needed for `0.2`
ledgers. A `0.1` ledger under a real scheme replays only with
`allow_unbound_keys=True`, and the caller is then trusting every key its
verifier holds.

Binding does not make a ledger authentic. Anyone can write a different
ledger from a genesis of their own. Pin the genesis `event_id` you trust:
`replay(..., expected_genesis_event_id=...)`, or
`verify-bundle --expect-genesis`.

## Verifier-only distribution

Every ed25519 bundle flow supports `--verifier-only`, which writes
`public_keys.json` without `private_keys.json`. Distribute verifier-only
artifacts by default: consumers can verify every signature and replay every
ledger without ever holding a private key. Ship private key material only to
the signer that needs it, and never inside a published workspace.

The generated `private_keys.json` files in demo workspaces are throwaway demo
material regenerated on every run. Real deployments must generate keys outside
the repository, keep them out of any directory that gets published or
committed, and pass only key identifiers and public keys through SATROOT
tooling.

## Rotation

- Rotate an account's event-signing key with `bind-key`, signed by the
  account's current key, so the rotation is a verifiable protocol event.
  `rotate-authority` moves the mint authority to another account; it does
  not change or retire any key.
- Rotate publication keys by issuing new key ids in the next publication and
  letting consumers pin the registry manifest hashes recorded for each
  release; `ANCHORS.md` shows the pattern for hash-pinning published
  artifacts.
- After any suspected compromise, republish from a clean key id rather than
  reusing the old one; deterministic replay means the semantic state survives
  unchanged.

## Verification model: lint versus verify

The artifact tooling has two distinct layers, and only one of them is
cryptographic:

- **`*-lint` commands are structural.** They check declared file lists,
  counts, paths, and metadata consistency. They do not hash file contents and
  do not check signatures: a ledger with a tampered balance, or a release
  manifest with a forged signature, can pass every lint. Lint answers "is this
  artifact tree well-formed", never "is this artifact tree authentic".
- **`verify-*` commands are cryptographic.** `verify-bundle` re-hashes every
  bundle file against the bundle manifest and replays the ledger under the
  signature verifier. The manifest itself is **not signed**, and neither is the
  key file beside it: pass `--public-keys-json` (or `--secrets-json`) with keys
  you hold, and `--expect-genesis` with the genesis you kept. The result
  reports `keys_pinned` and `genesis_pinned`; `verify-release-manifest` checks the release signature
  and the bundle-index hash. These are the mandatory gate for integrity and
  authenticity.

Two operational consequences:

- Verify at the index level, not only per bundle: a whole-bundle swap is
  internally self-consistent and is caught by the release-level checks
  (`release-lint` metadata binding plus `verify-release-manifest`), not by
  `verify-bundle` on the swapped directory alone.
- For `hmac-sha256` bundles, `verify-bundle` reads the shared secret from the
  bundle directory it is verifying, so its result is meaningful only when the
  artifact tree comes from a trusted channel — an attacker who can rewrite the
  artifacts can rewrite the secret and self-attest. Supply secrets out-of-band
  (as `verify-release-manifest --secrets-json` does), or use `ed25519` with
  independently pinned public keys, for anything crossing a trust boundary.

Generated workspace summaries embed absolute paths, so a moved or copied
workspace fails lint for benign reasons: regenerate workspaces in place rather
than relocating them, and treat manifest hashes (as recorded in `ANCHORS.md`)
as the portable identity of published artifacts.

## What this guidance does not claim

Consistent with `BOUNDARIES.md`, SATROOT does not define or provide HSM
integration, PKI hierarchies, certificate formats, key escrow, recovery
procedures, or any production key-storage standard. Those choices belong to
the deployment, not the protocol. This document only fixes the discipline for
composing the frozen schemes safely.
