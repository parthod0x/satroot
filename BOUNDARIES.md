# SATROOT-1 Boundaries

SATROOT-1 is a protocol primitive, not a financial product.

## What SATROOT-1 claims

- A native Bitcoin/BSV satoshi is the smallest native accounting unit.
- A specific one-satoshi UTXO can act as a root witness, namespace, or authority handle.
- Protocol-defined token balances can be computed above that root by replaying events.
- The semantic token supply can be arbitrary if the protocol rules permit it.
- The same root model already supports five separate released profiles without changing the base primitive.
- Root satoshi movement is not automatically equivalent to semantic token transfer; SATROOT state follows valid protocol events.
- One real one-satoshi testnet outpoint has been bound as a namespace root, its state commitment broadcast in the recommended on-chain envelope, and that envelope re-verified offline from raw transaction bytes; `ANCHORS.md` is the sole record of those runs.

## What SATROOT-1 does not claim

- It does not subdivide Bitcoin below one satoshi.
- It does not make semantic units into native Bitcoin units.
- It does not create a stablecoin, security token, e-money token, deposit, or redemption right.
- It does not promise reserves, price stability, exchange support, wallet support, profit, or legal rights.
- It defines `hmac-sha256` and `ed25519` verification paths but makes no production key-management, custody, or HSM claims; the `demo` scheme remains an explicit placeholder.

## Stable-value work

Stable-value or fiat-reference designs are implemented as separate profiles; `SATROOT-STABLE-1` is the released reference-only example. The clear distinction stays between:

- reference-only accounting units,
- externally wrapped stablecoin receipts,
- fiat-backed regulated issuer tokens,
- bank/CBDC receipt bridges.
