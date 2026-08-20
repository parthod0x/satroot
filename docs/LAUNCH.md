# A satoshi is the floor of value, not the ceiling of meaning

SATROOT turns one native BSV satoshi into the root of a deterministic, replayable semantic ledger — and we anchored one for real, on testnet, with every step independently verifiable from raw bytes.

## The idea

Bitcoin's smallest native unit is the satoshi. Most token designs respond to that floor in one of two ways: pretend to subdivide it, or ignore the chain entirely and keep balances in a database. SATROOT takes a third position:

> The satoshi is not subdivided. The satoshi anchors a protocol-defined state space.

One specific one-satoshi UTXO becomes a **root witness** — the namespace handle for a ledger whose state is computed purely by replaying signed events. Token units, machine credits, receipts, identities, licenses, and event-stream custody all live as overlay state above that root. The chain provides the anchor, ordering, and publication; the protocol provides deterministic meaning. Nothing about the satoshi itself changes, and moving it is never mistaken for a semantic transfer: state follows valid signed events, not UTXO activity.

## What shipped

The reference implementation is a dependency-free, pure-Python kernel — a canonical event format, a replay engine with strict sequence and hash-chain enforcement, and three signature schemes (a demo placeholder, `hmac-sha256`, and `ed25519`). Above the kernel sit six released object profiles — stable reference units, machine credits, receipts, identities, licenses, and event-stream heads — and a full publication ladder that packages ledgers into signed bundles, releases, catalogs, and registry workspaces, each layer carrying its own manifest hashes and verification tooling.

Nineteen tagged releases, ~1,700 tests behind a single release gate, and the protocol rules declared frozen as the v1 draft.

```bash
pip install satroot
satroot1 replay examples/events_floor1.json
```

## The proof

A protocol document can claim anything. So instead of claiming, we ran the whole loop against the real chain and recorded every artifact:

1. **Anchor.** A real one-satoshi testnet outpoint was bound as the `root_id` of a demo namespace, its full lifecycle signed and verified with ed25519.
2. **Publish.** That namespace was pushed through the entire publication ladder — bundles, release, catalog, registry — with ed25519 at every layer.
3. **Commit.** The namespace's state hash was broadcast on-chain inside the spec's `OP_RETURN` envelope.
4. **Verify.** The broadcast transaction's raw bytes were fetched and verified fully offline: the bytes hash to the recorded txid, and the envelope matches the deterministically rebuilt commitment byte for byte.

The records (BSV testnet):

- Root outpoint: `147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0`
- State commitment: `sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3`
- Envelope transaction: `6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0` (output 0 is a zero-value `OP_FALSE OP_RETURN` carrying the `SATROOT1` tag and the canonical JSON commitment)

Don't take this post's word for it. Save the raw transaction hex to a file and run the offline verifier yourself:

```bash
python scripts/run_envelope_verification_smoke.py \
  --raw-tx-hex-file rawtx.hex \
  --root-id 147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0 \
  --state-hash sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3 \
  --expected-txid 6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0
```

No network access, no trust in us: the verifier parses the bytes, hashes them, finds the envelope output, and compares it byte-for-byte against the commitment it rebuilds from scratch. The complete record of every intentional anchored run lives in `ANCHORS.md` — the only place in the repository a real outpoint may appear.

## What it deliberately is not

- It does not subdivide Bitcoin below one satoshi, and semantic units are not native Bitcoin units.
- It creates no stablecoin, security, redemption right, or reserve claim; stable-value designs are reference-only profiles with those non-claims stated in the genesis record itself.
- There is no token sale. The protocol is Apache-2.0, and the anchored satoshi is worth exactly one satoshi.
- The frozen kernel authorizes on the signer string plus a valid signature under a registered key; binding keys to accounts across trust domains is explicitly an application-layer responsibility, documented rather than hand-waved.

## Where this goes

The profile system is the point. A namespace rooted in one satoshi can carry the custody lineage of a telemetry stream, the prepaid credit balance of an autonomous agent, or the assignment history of a license — deterministically, with offline verification, for the cost of almost nothing. The machine-credit and event-stream profiles are aimed squarely at the emerging problem of proving what autonomous agents consumed, published, and were authorized to do.

The kernel is frozen; the profiles are open. If you want to build an object class on a one-satoshi root, the repository ships everything this post described — including the tooling that produced its own proof.

Code: https://github.com/parthod0x/satroot · Package: https://pypi.org/project/satroot/ · Apache-2.0
