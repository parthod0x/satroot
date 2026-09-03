# Migrating from SATROOT v1 to v2

**v2.0.0 breaks state hashes.** A ledger written under v1 does not replay
under v2, and a v2 ledger does not replay under v1. This document says exactly
what changed, why the break could not be avoided, and what to do with an
existing ledger.

If you are starting fresh, you need none of this. Use v2 and read `SPEC.md`.

---

## Why there is a break at all

**The genesis record was never authenticated.**

Genesis is the record that fixes `mint_authority`, `max_supply` and the entire
opening allocation. Every later event is authenticated against the authority
that genesis declares. But genesis itself was never checked: a forged
signature, an empty one, or no signature at all replayed clean under every
scheme.

So the root of every ledger was forgeable, and every event above it was being
authenticated against a root anyone could have authored. Signature checking on
events 2..n was doing less work than it appeared to.

Authenticating genesis changes its `event_id`. `event_id` feeds
`last_event_id`, which feeds the section 7 state commitment. So every state
hash in every ledger changes.

That is the whole break. **The alternative was leaving the root of every
ledger forgeable, which is not a trade.**

## What else changed

Twenty-six specification defects were fixed across seven rounds of independent
implementation. Nothing in the protocol changed *shape* — the specification
now says what the implementations always did, in the places where it
previously said nothing or said it wrong.

The two that carried security weight:

1. **Unauthenticated genesis**, above.
2. **An orphan `profile_mode` committed arbitrary JSON** — including nested
   objects — into the state hash. Two ledgers identical but for that field
   replayed as valid with different state hashes.

The rest are in `CHANGELOG.md` under v2.0.0. Most are cases where the document
was silent and two readers could reasonably disagree: the default signature
scheme outside genesis, canonical amount forms, per-scheme `key_id` rules,
what "account control" means byte-for-byte.

Neither of the two above was findable by 1,751 tests, two implementations, or
twelve review rounds — because all of those were written against the code.
Both were found by someone reading the document and implementing it fresh.

## What to do with an existing ledger

### If you only need to keep verifying history

**Pin v1.** `pip install satroot==1.7.1`. It still replays your ledger exactly
as it always did.

Understand what you are pinning: the genesis of that ledger cannot be
authenticated, and its state hashes were computed under rules that permitted a
forgeable root. If you are the only party who has ever written to it, that may
be acceptable. If someone else supplied any part of it, it is not.

### If you need to carry the ledger forward

There is no in-place upgrade, and this is deliberate: silently rewriting
signed history is exactly the thing this protocol exists to make impossible.

The honest path is to **start a new v2 ledger and treat the v1 ledger as
closed**:

1. Keep the v1 ledger, its keys, and a v1 verifier. It remains verifiable
   under v1 rules forever.
2. Record the v1 ledger's final state hash somewhere durable — an anchor, a
   timestamp token, a note handed to your counterparty.
3. Open a v2 ledger whose genesis is properly signed, with opening balances
   matching the v1 final state.
4. Publish both. The pair is the continuous record: v1 verifiable under v1,
   v2 under v2, joined by the state hash you carried across.

That leaves a seam. The seam is honest and visible, which is better than a
migration that quietly re-signs old records under new rules and produces a
history that never happened.

### If you anchored a v1 state hash on-chain

The anchor still attests what it always attested: that *that* state hash
existed at *that* time under v1 rules. It does not become invalid. Note in
your records which protocol version the hash was computed under, because a v2
verifier will compute a different one from the same events.

## Checking which version a ledger was written under

A v2 genesis carries a real signature that verifies. A v1 genesis either has
no signature, or one that no verifier ever checked.

```python
import json, satroot1 as sr

events = json.load(open("ledger.json", encoding="utf-8"))
genesis = events[0]
print("has a signature field:", "signature" in genesis)
```

Under v2, replaying a ledger whose genesis is unsigned or wrongly signed
raises rather than passing. That refusal is the feature.

## The conformance corpus

The corpus grew from 33 vectors to 68, and `EXPECTED.txt` is derived from the
declared `expect` blocks rather than from running the reference
implementation. If you maintain an independent implementation, re-run it:

```bash
python vectors/run.py --impl your_verifier.py
```

Nineteen vectors are expected to pass and forty-nine to be rejected. An
implementation that accepts something in the reject set has the same defect
the corpus was grown to catch.
