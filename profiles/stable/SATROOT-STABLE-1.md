# SATROOT-STABLE-1

Status: Draft profile
Depends on: SATROOT-1 v0.1

## Purpose

SATROOT-STABLE-1 defines a stable-value accounting profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile adds reference-value metadata so a SATROOT ledger can express balances in relation to an external unit such as USD or INR without claiming that the base satoshi itself has become fiat.

## Safe starting mode

The first supported mode is **reference-only accounting**.

In this mode, a token:

- names an external reference unit,
- uses SATROOT events for mint, transfer, and burn,
- may be useful for invoices, API credits, machine accounting, or internal ledgers,
- does not promise redemption,
- does not claim reserves,
- does not claim regulated money status.

## Stable profile fields

The draft stable profile uses these optional genesis fields:

- `profile`: `SATROOT-STABLE-1`
- `profile_mode`: `reference-only`
- `reference_unit`: an external unit such as `USD`
- `redemption`: `none`
- `reserve_model`: `none`
- `intended_use`: short machine-readable description of the use case

These fields describe economic interpretation. They do not change the underlying SATROOT-1 replay model.

## Demo token

This repo includes a reference-only example token:

```text
Symbol: USDROOT1
Name: SATROOT Reference Dollar
Reference unit: USD
Profile mode: reference-only
Redemption: none
Reserve model: none
Intended use: invoice-credit-accounting
```

## Required disclaimer

A reference-only SATROOT-STABLE-1 token is not a redeemable stablecoin. It does not represent a bank deposit, e-money claim, security, debt instrument, investment product, or legal right to receive fiat or another token.

## Future profile modes

- Wrapped stablecoin receipt: units correspond to externally held USDC, USDT, or similar instruments.
- Fiat-backed issuer token: reserves, redemption, legal terms, and compliance required.
- Bank or CBDC receipt bridge: SATROOT records receipts or state commitments for regulated rails.
