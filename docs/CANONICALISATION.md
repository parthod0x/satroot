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

## What this is offered as

A small, reproducible cross-implementation result, of the kind that is useful
to anyone binding digests over JSON payloads — including the drafts in the
IETF SCITT orbit that use JCS for exactly that purpose.

The finding is unremarkable in itself: two reasonable schemes disagree on one
narrow input class, and the disagreement is easy to avoid once known. It is
recorded here because "we checked" is worth more than "it should be fine",
and because the earlier assertion in this repository was the latter.
