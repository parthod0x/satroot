# SATROOT-1 Boundaries

SATROOT-1 is a protocol primitive, not a financial product.

## What SATROOT-1 claims

- A native Bitcoin/BSV satoshi is the smallest native accounting unit.
- A specific one-satoshi UTXO's outpoint can name a namespace. The name is a label: SATROOT-1 checks `root_id` for form only, does not tie a ledger or its keys to whoever controls the UTXO, and does not require commitments to spend it. Authority over a ledger comes from its genesis and the keys bound there.
- Protocol-defined token balances can be computed above that root by replaying events.
- The semantic token supply can be arbitrary if the protocol rules permit it.
- The same root model already supports six registered profiles without changing the base primitive.
- Root satoshi movement is not automatically equivalent to semantic token transfer; SATROOT state follows valid protocol events.
- One real one-satoshi testnet outpoint has been bound as a namespace root, its state commitment broadcast in the recommended on-chain envelope, and that envelope re-verified offline from raw transaction bytes; `ANCHORS.md` is the sole record of those runs.

## What SATROOT-1 does not claim

- It does not subdivide Bitcoin below one satoshi.
- It does not make semantic units into native Bitcoin units.
- It does not create a stablecoin, security token, e-money token, deposit, or redemption right.
- It does not promise reserves, price stability, exchange support, wallet support, profit, or legal rights.
- It defines `hmac-sha256` and `ed25519` verification paths but makes no production key-management, custody, or HSM claims; the `demo` scheme remains an explicit placeholder.
- It does not make the root satoshi a witness, an authority, or a minimum of value. A one-satoshi output is worth less than the fee needed to spend it.
- It does not bind keys in a version `0.1` ledger. Since 3.0.0 a ledger signed under a real scheme is version `0.2`: genesis binds each signing account to its key and every record must be signed with its signer's bound key (SPEC section 6.7). A `0.1` ledger under a real scheme replays only when the caller explicitly accepts unbound keys. Before 3.0.0 this document said only the final record was exposed; that was wrong, because a holder of any registered key can re-sign every record, not just the last.
- It does not make a ledger authentic on its own. A forger can write a whole new ledger, from a genesis binding the authority to the forger's key, and it is valid; it is a different ledger. Pin the genesis `event_id` you trust (kept from an earlier copy, or anchored) and supply the public keys yourself; see `KEY_MANAGEMENT.md`.

## Stable-value work

Stable-value or fiat-reference designs are implemented as separate profiles; `SATROOT-STABLE-1` is the released reference-only example. The clear distinction stays between:

- reference-only accounting units,
- externally wrapped stablecoin receipts,
- fiat-backed regulated issuer tokens,
- bank/CBDC receipt bridges.
