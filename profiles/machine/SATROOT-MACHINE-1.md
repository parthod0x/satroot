# SATROOT-MACHINE-1

Status: Draft profile
Depends on: SATROOT-1

## Purpose

SATROOT-MACHINE-1 defines a machine-native credit profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile uses the base ledger model for prepaid or usage-scoped machine credits such as API calls, compute quotas, inference units, automation budgets, or service entitlements.

## Safe starting mode

The first supported mode is **prepaid-credit**.

In this mode, a token:

- represents a protocol-defined service credit,
- can be minted, transferred, and burned using SATROOT events,
- is suitable for internal billing or machine-to-machine accounting,
- does not claim to be fiat, a redeemable instrument, or a regulated payment rail.

## Machine profile fields

The draft machine profile uses these optional genesis fields:

- `profile`: `SATROOT-MACHINE-1`
- `profile_mode`: `prepaid-credit`
- `service_scope`: a compact identifier such as `api-compute`
- `billing_unit`: a compact identifier such as `request`
- `consumption_model`: a compact identifier such as `burn-on-use`
- `intended_use`: short machine-readable description of the service ledger

These fields describe operational meaning. They do not change the underlying SATROOT-1 replay model.

## Demo token

This repo includes a machine-credit example token:

```text
Symbol: APICREDIT1
Name: SATROOT API Credit
Profile mode: prepaid-credit
Service scope: api-compute
Billing unit: request
Consumption model: burn-on-use
Intended use: machine-api-credit
```

## Interpretation

`SATROOT-MACHINE-1` is useful where one root satoshi should anchor deterministic service balances without requiring every machine action to be a native on-chain asset transfer.

Example uses:

- API request credits
- compute budget credits
- inference unit balances
- automation workflow quotas
- internal service accounting
