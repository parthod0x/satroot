# Reporting a security issue

**Email parthms.id@gmail.com.** Put "SATROOT security" in the subject.

If you would rather not use email, GitHub's private vulnerability reporting
is enabled on this repository: **Security → Report a vulnerability**. Both
reach the same person.

Please do not open a public issue for something exploitable until it has been
fixed. For anything else — a spec ambiguity, a conformance disagreement, a
question — a public issue is better, because other implementers benefit from
reading it.

## What to expect, honestly

This is maintained by one person. There is no security team, no on-call
rotation, and no service-level agreement. What you will get:

- An acknowledgement within a few days.
- An honest assessment, including "you are right and I do not have a fix yet".
- Credit in the changelog and the release notes, unless you prefer otherwise.
- No legal threats, ever, for reporting something in good faith.

What you will not get is a bounty. There is no money in this project.

## In scope

Anything that breaks the protocol's central claim — **that a holder of a
ledger and the public keys can recompute the exact state offline, and detect
any alteration**:

- Forging, altering, reordering, truncating or omitting events in a way that
  still replays as valid.
- Two different ledgers that produce the same state hash, or one ledger that
  produces different hashes across conforming implementations.
- Any signature check that can be satisfied without the corresponding key.
- Canonicalisation differences that change a hash.
- Parser behaviour that admits malformed input as valid, in the kernel, the
  envelope reader, or the timestamp-token reader.

**Spec defects count.** The most serious issue found in this project so far
was not a code bug: the specification never required the genesis record to be
authenticated, so a forged or absent genesis signature replayed clean under
every scheme, and the root of every ledger was forgeable. That was fixed in
**v2.0.0** — see `MIGRATION.md`.

It was found by someone implementing the spec from scratch and reading only
the document. If your reading of `SPEC.md` disagrees with what the reference
implementation does, **that disagreement is a finding**, whichever one turns
out to be wrong.

## Out of scope

- The hosted service at api.satledger.org is a separate, proprietary product.
  Report issues there to the same address, but they are not SATROOT issues.
- Denial of service through resource exhaustion on inputs a caller controls
  and is expected to bound.
- Anything requiring the operator's private keys. `BOUNDARIES.md` and
  `THREAT_MODEL.md` state plainly what an operator holding the signing keys
  can do; that is a documented limit, not a vulnerability.

## The fastest path to a finding

The conformance corpus is the sharpest tool here — 68 vectors, 19 that must
replay and 49 that must be rejected, with a standalone runner:

```bash
python vectors/run.py --impl your_verifier.py
```

An implementation that accepts something in the reject set, or rejects
something in the accept set, has found either a defect in your verifier or a
defect in the specification. Both are worth reporting, and the corpus grew
from 33 vectors to 68 because of exactly that exercise.

## Supported versions

| Version | Status |
|---|---|
| 2.0.x | Supported. |
| 1.7.x and earlier | **Unsupported, and known to accept an unauthenticated genesis record.** Pin it only to keep verifying existing ledgers, never for new ones. |
