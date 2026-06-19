# SATROOT-1 Boundaries

SATROOT-1 is a protocol primitive, not a financial product.

## What SATROOT-1 claims

- A native Bitcoin/BSV satoshi is the smallest native accounting unit.
- A specific one-satoshi UTXO can act as a root witness, namespace, or authority handle.
- Protocol-defined token balances can be computed above that root by replaying events.
- The semantic token supply can be arbitrary if the protocol rules permit it.
- The same root model can later support separate profiles without changing the base primitive.

## What SATROOT-1 does not claim

- It does not subdivide Bitcoin below one satoshi.
- It does not make semantic units into native Bitcoin units.
- It does not create a stablecoin, security token, e-money token, deposit, or redemption right.
- It does not promise reserves, price stability, exchange support, wallet support, profit, or legal rights.
- It does not define production-grade signature verification in v0.1.

## Stable-value work

Stable-value or fiat-reference designs should be implemented as separate profiles, for example `SATROOT-STABLE-1`, with clear distinction between:

- reference-only accounting units,
- externally wrapped stablecoin receipts,
- fiat-backed regulated issuer tokens,
- bank/CBDC receipt bridges.
