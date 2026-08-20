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
- **Event signing keys** authorize semantic state transitions. They belong to
  the accounts named in `signer` fields and rotate with `rotate-authority`
  events inside the ledger itself.
- **Publication signing keys** (`release-key`, `catalog-key`, registry and
  index key ids) sign artifact manifests, not ledger events. Compromise of a
  publication key lets someone republish artifacts, not rewrite ledger state.

A compromise in one layer must not be treated as a compromise of the others,
and no key in any layer can move the root satoshi.

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

- Rotate event-signing authority with the ledger's own `rotate-authority`
  action, so the rotation itself is a verifiable protocol event.
- Rotate publication keys by issuing new key ids in the next publication and
  letting consumers pin the registry manifest hashes recorded for each
  release; `ANCHORS.md` shows the pattern for hash-pinning published
  artifacts.
- After any suspected compromise, republish from a clean key id rather than
  reusing the old one; deterministic replay means the semantic state survives
  unchanged.

## What this guidance does not claim

Consistent with `BOUNDARIES.md`, SATROOT does not define or provide HSM
integration, PKI hierarchies, certificate formats, key escrow, recovery
procedures, or any production key-storage standard. Those choices belong to
the deployment, not the protocol. This document only fixes the discipline for
composing the frozen schemes safely.
