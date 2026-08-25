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

`draft-mih-sokolov-scitt-payload-binding-01` defines **`jcs-n`**. The full
construction is:

```
CANONICAL-DIGEST(jcs-n, P) = lowercase_hex(SHA-256(JCS(normalize(P minus exclusion_set))))
```

where `normalize` removes, bottom-up and recursively, every member whose
value is `null`, an empty array, or an empty object; and the exclusion set is
declared by the payload class, covering fields that carry the record's own
derived identifier or reference other records in a chain.

Implemented in `satroot_jcs.jcs_n` from the draft text.

**The "n" is *absent-field* normalisation, not Unicode normalisation.** The
draft adds no NFC step, and is explicit that this is a choice: its Related
Work section contrasts `jcs-n` with a draft that does define NFC rules and
notes the two are not byte-compatible.

### What is not a finding

SATROOT's state snapshot carries members `jcs-n` removes — `frozen_accounts`
when empty, `profile` and `profile_mode` when null — so the two digests
differ. **This is arithmetic, not a discovery.** Anyone reading the algorithm
predicts it, and the draft states in the same section that the semantic
equivalence of absent, null, empty array and empty object is a payload-class
decision. It also states that digests are comparable only within the same
digest context, so comparing across two deliberately different contexts is
not a meaningful operation.

Recorded here so the repository does not mistake it for one.

### What implementing it actually surfaced

**1. An emptied object inside an array is ambiguous.** The draft says to
remove "every member" whose value is empty. In JSON a *member* is a
name/value pair in an object, not an array element. Under that reading:

```
{"a": [{"b": null}]}  ->  {"a": [{}]}
```

Under a reading that also prunes emptied objects from their arrays, the array
becomes empty, `a` is then an empty array, and the whole record reduces to
`{}`. **Same input, two defensible readings, different digests.** The draft
does not say which.

**2. Falsy-but-present values are a trap for some languages.** "Members
explicitly set to a non-null value are not removed" is unambiguous in prose,
but an implementer writing `if (!value) delete obj[key]` in a
falsiness-based language also strips `false`, `0` and `""`:

```
{"a": false, "b": 0, "c": "", "d": null, "e": [], "f": {}}
  correct  -> {"a": false, "b": 0, "c": ""}
  falsiness -> {}
```

This is the most likely real-world divergence between conforming
implementations, and a non-normative note would prevent it.

**3. The collapse is unconditional, which constrains which payload classes
can use it.** These four inputs share one digest:

```
{}   {"x": null}   {"x": []}   {"x": {}}     ->  44136fa355b3678a...
```

A payload class may declare an exclusion set, but cannot opt out of the
stripping. So a profile whose commitment binds *shape* — where a member
present-and-empty asserts something different from that member being absent —
cannot express that through `jcs-n` at all. Its options are to accept the
collapse or to register a different algorithm.

Since the canonicalization algorithm registry uses Specification Required
with a Designated Expert, and entries are immutable, that is a registry
question with a real answer space: is a shape-preserving variant in scope,
or is the intended answer that such profiles register their own?

### Limits of this implementation

- Integers above 2**53 are **rejected**, not rendered. RFC 8785 requires
  ECMAScript `Number::toString`, which switches to exponential form at 1e21
  and cannot exactly represent larger integers; `str()` diverges on both.
- Floats are rejected. The draft forbids non-integer JSON numbers in
  digest-bearing fields, so this is stricter than the profile requires rather
  than a gap in it.
- **The official RFC 8785 conformance vectors have not been run.** The JCS
  serialiser here is validated against cases chosen by its own author, which
  is weaker evidence than it looks.

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
