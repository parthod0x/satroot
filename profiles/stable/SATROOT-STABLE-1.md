# SATROOT-STABLE-1 Profile Draft

Status: Sketch / future profile
Depends on: SATROOT-1 v0.1

## Purpose

SATROOT-STABLE-1 defines a future stable-value accounting profile above SATROOT-1.

The base SATROOT-1 primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state.

This profile adds a reference-value field, such as USD, INR, USDC, or another external unit.

## v0.1-safe profile mode

The first safe mode is **reference-only accounting**.

Example token:

```text
Symbol: USDROOT1
Unit reference: USD
Peg mode: reference-only
Redemption: none
Reserve: none
Purpose: invoices, SaaS credits, API balances, machine-native accounting
```

## Required disclaimer

A reference-only SATROOT-STABLE-1 token is not a redeemable stablecoin. It does not represent a bank deposit, e-money claim, security, debt instrument, or right to receive fiat or another token.

## Future profile modes

- Wrapped stablecoin receipt: units correspond to externally held USDC/USDT/etc.
- Fiat-backed issuer token: reserves, redemption, legal terms, and compliance required.
- Bank/CBDC receipt bridge: SATROOT records receipts or state commitments for regulated rails.
