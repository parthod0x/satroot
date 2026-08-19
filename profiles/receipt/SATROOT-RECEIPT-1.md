# SATROOT-RECEIPT-1

Status: Draft profile
Depends on: SATROOT-1

## Purpose

SATROOT-RECEIPT-1 defines a receipt and invoice object profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile uses the base ledger model for document-like objects whose lifecycle benefits from deterministic issuance, transfer, archival, or settlement tracking.

## Safe starting mode

The first supported mode is **single-receipt**.

In this mode, a token:

- represents one protocol-defined receipt object,
- can move between accounts as custody or acknowledgement changes,
- can be burned when archived, settled, or intentionally closed,
- does not claim to be fiat, a regulated instrument, or a native blockchain transaction output.

## Receipt profile fields

The draft receipt profile uses these optional genesis fields:

- `profile`: `SATROOT-RECEIPT-1`
- `profile_mode`: `single-receipt`
- `document_type`: a compact identifier such as `invoice-receipt`
- `reference_id`: application-level document identifier
- `issuer_entity`: the party creating the receipt object
- `counterparty_entity`: the intended recipient or counterparty
- `settlement_unit`: external accounting unit such as `USD`
- `intended_use`: short machine-readable description of the receipt ledger

These fields describe business meaning. They do not change the underlying SATROOT-1 replay model.

## Demo object

This repo includes a receipt-object example:

```text
Symbol: RECEIPT1
Name: SATROOT Invoice Receipt
Profile mode: single-receipt
Document type: invoice-receipt
Reference ID: INV-2026-0001
Issuer entity: issuer-co
Counterparty entity: buyer-co
Settlement unit: USD
Intended use: invoice-receipt-ledger
```

## Interpretation

`SATROOT-RECEIPT-1` is useful where one root satoshi should anchor a deterministic document lifecycle without forcing the document itself to become a native on-chain asset class.

Example uses:

- invoice receipts
- proof-of-delivery records
- settlement acknowledgements
- service completion receipts
- escrow release acknowledgements
