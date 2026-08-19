# SATROOT-IDENTITY-1

Status: Draft profile
Depends on: SATROOT-1

## Purpose

SATROOT-IDENTITY-1 defines an identity and authority object profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile uses the base ledger model for single identity objects whose lifecycle benefits from deterministic issuance, controller rotation, archival, or revocation tracking.

## Safe starting mode

The first supported mode is **single-identity**.

In this mode, a token:

- represents one protocol-defined identity or authority object,
- can move between accounts as control or custody changes,
- can be burned when revoked or intentionally retired,
- does not claim to be a government identifier, legal personhood record, or regulated registry by default.

## Identity profile fields

The draft identity profile uses these optional genesis fields:

- `profile`: `SATROOT-IDENTITY-1`
- `profile_mode`: `single-identity`
- `identity_type`: a compact identifier such as `service-identity`
- `subject_id`: application-level subject identifier
- `controller_entity`: the initial controller of the identity object
- `authority_scope`: a compact identifier such as `api-signing`
- `intended_use`: short machine-readable description of the identity ledger

These fields describe operational meaning. They do not change the underlying SATROOT-1 replay model.

## Demo object

This repo includes an identity-object example:

```text
Symbol: IDENTITY1
Name: SATROOT Service Identity
Profile mode: single-identity
Identity type: service-identity
Subject ID: node-alpha
Controller entity: issuer-co
Authority scope: api-signing
Intended use: machine-identity-ledger
```

## Interpretation

`SATROOT-IDENTITY-1` is useful where one root satoshi should anchor a deterministic identity lifecycle without forcing the identity object itself to become a native on-chain asset class.

Example uses:

- service identities
- delegated signing authorities
- operator credentials
- machine controller rotation records
- revocable automation identities
