# SATROOT-LICENSE-1

Status: Draft profile
Depends on: SATROOT-1 v0.1

## Purpose

SATROOT-LICENSE-1 defines a license and usage-right object profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile uses the base ledger model for single license objects whose lifecycle benefits from deterministic issuance, assignment, archival, or revocation tracking.

## Safe starting mode

The first supported mode is **single-license**.

In this mode, a token:

- represents one protocol-defined license or usage-right object,
- can move between accounts as assignment or custody changes,
- can be burned when expired, revoked, or intentionally retired,
- does not claim to be a statutory registry, legal opinion, or universally recognized entitlement by default.

## License profile fields

The draft license profile uses these optional genesis fields:

- `profile`: `SATROOT-LICENSE-1`
- `profile_mode`: `single-license`
- `license_type`: a compact identifier such as `software-license`
- `asset_id`: application-level licensed asset identifier
- `licensor_entity`: the issuing rights holder
- `licensee_entity`: the intended recipient or customer
- `usage_scope`: a compact identifier such as `production-api`
- `intended_use`: short machine-readable description of the rights ledger

These fields describe operational meaning. They do not change the underlying SATROOT-1 replay model.

## Demo object

This repo includes a license-object example:

```text
Symbol: LICENSE1
Name: SATROOT Software License
Profile mode: single-license
License type: software-license
Asset ID: sdk-pro-2026
Licensor entity: issuer-co
Licensee entity: customer-co
Usage scope: production-api
Intended use: software-license-ledger
```

## Interpretation

`SATROOT-LICENSE-1` is useful where one root satoshi should anchor a deterministic license lifecycle without forcing the license object itself to become a native on-chain asset class.

Example uses:

- software licenses
- API access rights
- dataset usage rights
- media distribution entitlements
- internal feature-access grants
