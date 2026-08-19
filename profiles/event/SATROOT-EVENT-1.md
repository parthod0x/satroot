# SATROOT-EVENT-1

Status: Draft profile
Depends on: SATROOT-1

## Purpose

SATROOT-EVENT-1 defines an event-stream head object profile above SATROOT-1.

The SATROOT-1 base primitive remains unchanged:

> one native satoshi anchors protocol-defined semantic state

This profile uses the base ledger model for single stream-head objects that mark deterministic custody of an append-only event stream: who currently publishes it, and how publishing authority was handed off over time.

## Safe starting mode

The first supported mode is **single-stream**.

In this mode, a token:

- represents the head of one protocol-defined append-only event stream,
- can move between accounts as publishing custody is handed off,
- is not normally burned, because streams persist even when publication stops,
- does not claim that the stream's payload events themselves live on-chain or in this ledger by default; the stream content stays application-level, with this object anchoring only its custody lineage.

## Event profile fields

The draft event profile uses these optional genesis fields:

- `profile`: `SATROOT-EVENT-1`
- `profile_mode`: `single-stream`
- `stream_type`: a compact identifier such as `telemetry-stream`
- `stream_subject`: application-level stream subject identifier
- `publisher_entity`: the initial publishing entity
- `sequence_policy`: a compact identifier such as `append-only`
- `intended_use`: short machine-readable description of the stream ledger

These fields describe operational meaning. They do not change the underlying SATROOT-1 replay model.

## Demo object

This repo includes an event-stream example:

```text
Symbol: EVENT1
Name: SATROOT Telemetry Stream
Profile mode: single-stream
Stream type: telemetry-stream
Stream subject: stream-0001
Publisher entity: issuer-co
Sequence policy: append-only
Intended use: machine-event-stream-ledger
```

## Interpretation

`SATROOT-EVENT-1` is useful where one root satoshi should anchor the custody lineage of a machine-generated event stream without forcing the stream content itself to become on-chain state.

Example uses:

- sensor and telemetry feeds
- machine-to-machine message streams
- audit and log stream custody
- data-product publication feeds
- automated agent output streams
