# Canonicalisation: SATROOT compared against RFC 8785 (JCS)

An earlier version of `COMPARISON.md` asserted that SATROOT's canonical form
was "a strict subset of JCS behaviour for the documents it permits, with one
thing to watch." That was an assertion, not a measurement. This document
replaces it with a measurement.

Reproduce with:

```bash
PYTHONPATH=src python src/satroot_jcs.py
```

## Result

**13 of 15 cases agree. Two diverge, both for the same reason.**

| Case | Result |
|---|---|
| ASCII keys, nesting, empty containers, null/booleans | agree |
| Control characters, quotes, backslashes | agree |
| Non-ASCII values, emoji in values | agree |
| Non-ASCII keys within the BMP, CJK keys | agree |
| NFC vs NFD keys, NFC vs NFD values | agree |
| **Non-BMP key against a high-BMP key** | **diverge** |
| **Mathematical alphanumerics against U+FFFD** | **diverge** |

## The divergence

RFC 8785 section 3.2.3 sorts object keys **by UTF-16 code unit**. Python's
`json.dumps(sort_keys=True)` sorts **by Unicode code point**. The two orders
differ whenever a key contains a character outside the Basic Multilingual
Plane, because UTF-16 encodes those as surrogate pairs beginning in
U+D800–U+DBFF, which sort *below* ordinary BMP characters in U+E000–U+FFFF.

Concretely, with keys U+1F600 (an emoji) and U+FF00:

```
JCS      : {"\U0001f600":1,"＀":2}      emoji first
SATROOT  : {"＀":2,"\U0001f600":1}      emoji last
```

Two implementations following the two schemes will digest different bytes for
the same logical record, and therefore disagree on every downstream hash.

## Why it does not affect SATROOT today

SATROOT's schema does not permit non-BMP characters in field names — every
field name in the protocol is drawn from a fixed ASCII vocabulary. The
divergence is therefore unreachable through any schema-valid SATROOT record.

That is a property of the schema, not of the canonicalisation. **Any profile
that permits arbitrary user-supplied object keys must choose one scheme
explicitly**, because the choice is observable and the two answers are both
defensible.

## Normalisation: neither scheme normalises

Worth stating plainly, because it is a live topic among implementers:

- U+00E9 (NFC "é") and U+0065 U+0301 (NFD "é") are **different keys** under
  both schemes.
- Both schemes produce **identical output** for a record containing both.
- Neither applies NFC, NFD, NFKC or NFKD.

The consequence is that normalisation is a **producer-side** concern. A
producer that normalises and one that does not will emit different bytes for
what a human would call the same record, and no canonicalisation scheme will
reconcile them. A profile carrying user-supplied text should state whether
producers must normalise, and to which form.

## Numbers are out of scope here

RFC 8785 requires ECMAScript `Number::toString` semantics for numeric values,
which is a subtle algorithm. `src/satroot_jcs.py` **rejects floats** rather
than approximating it.

This does not weaken the comparison for SATROOT, which never emits a JSON
number for a quantity — every amount, balance and supply value is an ASCII
digit string, bounded to 512 digits. Integers used for `sequence` and
`decimals` serialise identically under both schemes.

An implementation seeking general JCS conformance must handle numbers
properly and should not use this module for that purpose.

## Compared against `jcs-n`

`draft-mih-sokolov-scitt-payload-binding-01` (Mih, Action State Group;
Sokolov, Tyche Institute; 27 July 2026) defines **`jcs-n`**, a digest over
JSON payloads. Implemented here from the draft text, in `satroot_jcs.jcs_n`.

The algorithm is:

1. Remove, bottom-up and recursively, every member whose value is JSON
   `null`, an empty array, or an empty object.
2. Apply RFC 8785 (JCS).
3. SHA-256.
4. Lowercase hexadecimal.

**Worth stating clearly, because it is easy to assume otherwise: the "n" is
*absent-field* normalisation, not Unicode normalisation.** The draft adds no
NFC or NFD step. So `jcs-n` inherits the behaviour measured above — NFC and
NFD forms remain distinct — and normalisation stays a producer-side concern.

### Result: the schemes disagree on the ordinary SATROOT snapshot

Not on exotic input. On the common case:

```
commitment snapshot of an unprofiled ledger, no frozen accounts

  jcs-n   : de0e21d70f84fd91e5919cdd5399d178...
  satroot : c2c8ba71dc82384ce11547e47f5f0b10...
```

`jcs-n` strips three members that SATROOT retains:

| Member | Value in an ordinary snapshot | jcs-n |
|---|---|---|
| `frozen_accounts` | `[]` when nothing is frozen | removed |
| `profile` | `null` when the ledger has no profile | removed |
| `profile_mode` | `null` likewise | removed |
| `max_supply` | `null` when no cap is set | removed |

Records containing none of these agree.

### Why this matters beyond the two implementations

The two schemes encode different answers to a real modelling question:
**is an absent member the same as an empty one?**

`jcs-n` says yes — `{"frozen_accounts": []}` and `{}` denote the same state,
so they should digest identically, which makes digests stable across
producers that differ only in whether they emit empty collections.

SATROOT says no — the snapshot is a fixed shape, and every member is present
whether or not it holds anything, so the digest binds the shape as well as
the contents.

Both are defensible. Neither is a bug. But a profile that digests a payload
under one scheme and verifies it under the other will fail, and the failure
will look like corruption rather than a specification mismatch. **Any profile
combining SCITT payload binding with a state commitment should state which
convention it uses.**

## What this is offered as

A small, reproducible cross-implementation result, of the kind that is useful
to anyone binding digests over JSON payloads — including the drafts in the
IETF SCITT orbit that use JCS for exactly that purpose.

Two findings, of different weight.

Against plain RFC 8785, the disagreement is narrow — non-BMP object keys —
and unreachable through a schema-valid SATROOT record.

Against `jcs-n`, it is not narrow. The schemes disagree on the ordinary
snapshot, because they encode different answers to whether an absent member
is the same as an empty one. That is a modelling decision a profile has to
make explicitly, and it is the kind of thing that surfaces as a mysterious
digest mismatch if nobody writes it down.

Recorded here because "we checked" is worth more than "it should be fine",
and because the earlier claim in this repository was the latter.
