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

## `jcs-n` was withdrawn on 2026-08-24 — read this section as history

`draft-mih-sokolov-scitt-payload-binding-02` **withdraws `jcs-n`** (§4.2) and
registers plain `jcs` — RFC 8785 with no normalization pass — in its place
(§4.1), prohibiting new declarations using `jcs-n`.

Everything below describes implementing the **-01** text and remains accurate
about that text. It is no longer a description of anything current.

**Two things are worth carrying forward.**

**The scope question resolved the way this implementation guessed.** -01 said
only "the set of fields declared by the payload class" (§4, *The Derived
Identifier* — an earlier version of this document cited §5, which is *Envelope
Conventions*, and was wrong). -02 §4.1 states it outright:

> The exclusion set is matched against the top-level member names of P only; a
> member of the same name nested inside a member's value is not removed.

That is what `satroot_jcs.jcs_n` does. It was a guess when it was written, and
recording that it was a guess matters more than recording that it was right.

**The withdrawal rationale rests on an implementer census** that found "the
reference implementation was the only implementer of the normalization step it
added". This implementation was a second. That is a footnote to the premise
and changes nothing about the conclusion: the byte audit reported alongside it
found 191 of 203 records byte-identical under plain `jcs`, and that is the
substantive reason.

**How this was found is the uncomfortable part.** Six test vectors and a
message asking the scope question were prepared and reviewed internally before
sending. Two reviewers independently established that -02 had been published
**four days before the message was written**, answering the question and
withdrawing the algorithm. The draft had been fetched at -01 without checking
for a newer revision — the same failure that a previous round had already
caught with a different document, where the revision landed the day it was
read.

## Compared against `jcs-n` (as defined in -01, now withdrawn)

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

**1. The draft publishes no `jcs-n` test vectors.** Appendix A walks an
example and stops before the digest. Every divergence below is prevented by a
vector rather than by prose, which makes vectors the useful contribution.

**2. A generic recursive prune diverges on arrays — though the text is not
ambiguous.** RFC 8259 defines `member` as a name/value pair occurring only
inside an object; array contents are elements. The draft uses the terms
correspondingly: "empty array (zero elements)" against "empty object (zero
members)". So there is exactly one conforming reading:

```
{"a": [{"b": null}]}  ->  {"a": [{}]}
```

An implementer writing a generic prune that also filters arrays reduces this
to `{}`. That is a nonconforming implementation rather than a second reading
— but it is exactly what a published vector prevents.

**3. "Explicitly set to a non-null value" is imprecise.** An empty array and
an empty object *are* non-null values, and they are removed. An implementer
writing `if (!value) delete obj[key]` in a falsiness-based language
additionally strips `false`, `0` and `""`:

```
{"a": false, "b": 0, "c": "", "d": null, "e": [], "f": {}}
  conforming -> {"a": false, "b": 0, "c": ""}
  falsiness  -> {}
```

**4. Section 3.1 holds a small internal tension.** It says the semantic
equivalence of absent, null, empty array and empty object "is a payload-class
decision", but `jcs-n`'s stripping is unconditional and runs *after* the
profile's own normalisation. A payload class does not configure that
equivalence; it decides only by selecting `jcs-n` or not. Reading the sentence
as a **precondition** for selecting the algorithm would remove the tension.

These four inputs share one digest, which is the behaviour such a
precondition would describe:

```
{}   {"x": null}   {"x": []}   {"x": {}}     ->  44136fa355b3678a...
```

### A fifth input, and a better one

**The draft does not say whether the exclusion set is name-scoped or
path-scoped.** Section 13.2's only registered example is the bare pair
`{capsule_id, chain}`, which cannot distinguish the two readings, and section
3.1 says only "minus exclusion_set". Given

```
{"chain": "drop me", "inner": {"chain": "keep me"}}
```

a name-scoped implementation removes both members and a top-level-scoped one
removes the first. Two conforming-looking implementations produce different
digests for the same payload class.

`satroot_jcs.jcs_n` excludes **top-level member names only**, and now says so.
That is a choice, not a reading of the text.

This is a better contribution than the four below, because the other four are
things a careful implementer gets right from the prose and a vector would
confirm. This one the prose does not settle at all.

### Limits of this implementation

- Integers above 2**53 are **rejected**, not rendered. RFC 8785 requires
  ECMAScript `Number::toString`, which switches to exponential form at 1e21
  and cannot exactly represent larger integers; `str()` diverges on both.
- Floats are rejected. The draft forbids non-integer JSON numbers in
  digest-bearing fields, so this is stricter than the profile requires rather
  than a gap in it.
- The integer and float limits above are declared scope, not silent failure:
  the vector tests skip on them explicitly rather than passing quietly.

## Partial validation against the JCS reference corpus

```bash
python scripts/fetch_rfc8785_vectors.py
python -m pytest tests/test_rfc8785_official_vectors.py
```

**Number serialisation is not implemented, so this is not evidence of RFC
8785 conformance.** Of five files from the JCS authors' reference corpus,
`arrays.json`, `unicode.json` and `weird.json` pass; `values.json` and
`structures.json` are skipped because they contain non-integer numbers.

The skipped pair is precisely where JCS is hard — everything else is key
sorting and JSON escaping, the easy majority. The reference repository also
publishes a far larger number-serialisation corpus, which has not been run at
all. Treat this as coverage of the easy part, not as conformance.

### The RFC's own vector settles the UTF-16 question

`weird.json` contains **U+1F602** (astral) and **U+FB33** (BMP). The reference
output orders the astral character **first**, because its surrogate pair
begins `D83D`, below `FB33` as a code unit. Under code-point ordering the
smiley (128514) would sort after the Hebrew letter (64307).

- `satroot_jcs.jcs_serialize` reproduces the official output exactly.
- SATROOT's `canonical_json` **does not**.

The divergence documented above is therefore demonstrated by the reference
test data for the RFC itself, not by inputs chosen to prove a point.

### A wording point on section 11.3

`draft-mih-sokolov-scitt-payload-binding-01` section 11.3 forbids floats in
digest-bearing fields, on the grounds that "the same quantity serialises as
1.0, 1e0 or 1.00 in different implementations and JCS does not normalise
these forms".

**The conclusion is right; the stated reason appears to undersell it.** As a
statement about the specification, JCS does normalise those forms: it parses
each number and re-serialises via ECMAScript `Number::toString`. The RFC's
own vectors show it:

| input | canonical output |
|---|---|
| `4.50` | `4.5` |
| `2e-3` | `0.002` |
| `333333333.33333329` | `333333333.3333333` |

Two readings would make the sentence defensible, and both are worth stating.
As an *operational* claim it holds — shortest-round-trip float rendering is
genuinely hard, which is why the reference suite ships a separate
hundred-million-value number corpus, and implementations do vary in practice.

More importantly, **JCS normalises destructively.** It round-trips through
IEEE-754 binary64, so `333333333.33333329` becomes `333333333.3333333`, and
two distinct decimal quantities that map to the same double become
byte-identical. For monetary values that is worse than not normalising: the
digest binds the double rather than the decimal anyone wrote down. That is a
stronger argument for the same prohibition than the one given.

**Standing caveat:** this implementation rejects floats and integers above
2^53 rather than rendering them, and therefore skips exactly the reference
vectors that exercise number handling. The observation rests on reading RFC
8785 and its published vectors, not on having implemented the algorithm.

## What this is, and is not

**Not a cross-implementation result.** Both sides are driven by one author's
Python — SATROOT's canonicalisation, and that same author's restricted
implementation of another specification. No independent `jcs-n`
implementation is involved.

**Not a finding that the two disagree.** The payload-binding draft states
that digests are comparable only within a single digest context. Comparing
across two deliberately different contexts carries no information, and an
earlier version of this document treated that comparison as the headline
result. It was wrong to.

What this is: a restricted implementation of `jcs-n` written from the draft
text, whose construction surfaced four things a published test vector would
prevent, one question the prose does not settle at all - whether exclusion is
name-scoped or path-scoped - plus one point about the rationale in section
11.3.

The value, if any, lies in the vectors and the scoping question. The digest
comparison which prompted the work is not the contribution.

## A note on the surrounding code

The two modules this document leans on were reviewed externally on 26 August
2026, and the review found a defect worth recording here because it bears on
how much any of the above should be trusted.

`satroot_commitment.extract_message_imprint` could not parse a real RFC 3161
timestamp token. It searched for a structure shaped like a `messageImprint`,
descending only into SEQUENCEs - and the path from `ContentInfo` to `TSTInfo`
crosses a context-specific `[0]`, a SET and an OCTET STRING. So it rejected
every genuine token, while accepting any DER that happened to contain a
matching shape, including a bare `TimeStampReq`.

It survived because no test had ever handed it a real token: every fixture
was a request the module had built and fed back to its own parser, so the
implementation and its tests shared one wrong model of the ASN.1. It is now
a structural parse, and two genuine tokens - from freetsa.org and DigiCert -
are checked in under `tests/fixtures/rfc3161/`.

The lesson generalises to this document: a conformance corpus written by the
author of the implementation tests the author's understanding, not the
specification. The RFC 8785 results above are worth more than the `jcs-n`
ones precisely because the vectors came from someone else.
