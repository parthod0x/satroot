# How SATROOT relates to existing work

Researched August 2026. The short version: **the component parts of SATROOT
all exist as standards already. The contribution is composition, not
invention** — and one specific piece that no published standard specifies.

This document exists so that claim can be checked rather than believed, and
so the places where established systems are *better* than SATROOT are stated
by us rather than discovered by someone else.

---

## The one thing that appears to be unoccupied

Every mature system in this space proves some version of:

> *this opaque entry is at index i of a log whose root is R, and R is
> append-only-consistent with earlier roots.*

None of them defines:

> `S_n = f(S_{n-1}, e_n)` — a canonical serialisation, a **typed transition
> relation**, and a **deterministic state commitment** that any third party
> can recompute offline from the log alone.

That is the gap SATROOT occupies. The payload semantics that transparency
architectures deliberately leave opaque are exactly what SATROOT defines.

| System | Append-only ordered log | Replays to | General typed state |
|---|---|---|---|
| **IETF SCITT** (RFC 9943) | yes, abstract VDS | — payload **opaque by charter** | no |
| **in-toto** | no — unordered evidence DAG | verdict + artifacts | no |
| **SLSA** | no log at all | policy verdict | no |
| **C2PA** | no global order | validation status codes | no |
| **W3C VC** | no | standalone documents | no |
| **KERI KEL** | **yes** | **key state** | no — fixed domain |
| **KERI TEL** | **yes** | **registry state** | no — fixed domain |
| **Certificate Transparency** | yes | — multiset of certs | no |
| **Trillian** | yes | — leaves opaque by design | no (Map API removed) |
| **Sigstore / Rekor** | yes | — independent attestations | no |
| **git** | DAG, mutable refs | filesystem tree | no |

### Honest prior art — the two closest things

**KERI's Key Event Log is a genuine event-sourced state machine.**
Hash-chained, sequence-numbered, replayed to derive control authority, with
duplicity detection as its purpose. It is architecturally the nearest
relative SATROOT has. The difference is domain, not mechanism: a KEL replays
to *key state*, a TEL to *issued/revoked registry state*. Both are fixed,
narrow domains, and the KERI suite has no general typed-state facility. KERI
can anchor commitments to external data via seals, but explicitly does not
interpret or type that data.

**Google's Verifiable Log-Derived Map is the same concept, published first.**
A map derived from an input log via a well-defined mapping function, which
verifiers reconstruct identically by replaying entries. That is SATROOT's
idea, described by someone else, earlier. Its status is the reason the space
is still open: it lives in `trillian/experimental/batchmap`, the
non-experimental Trillian Map API was **removed outright**, and it carries a
stated limitation — verification cost scales linearly in the number of
revisions. SATROOT shares that linear-cost property (see limitations below).

Two adjacent near-misses: **gittuf's Reference State Log** replays to Git ref
values, and **IETF KEYTRANS** standardises identity→key binding — both
narrow-domain log-derived maps.

---

## Where established systems are better than SATROOT

Stated plainly, because these are real and a reader will find them anyway.

**Verification cost.** Certificate Transparency and Rekor give **O(log n)**
inclusion proofs against a published root. SATROOT verification replays the
**entire log** — O(n). For a ledger of thousands of events that is fine; for
hundreds of millions it is not. Let's Encrypt's CT shard currently holds over
640 million entries served as flat files; SATROOT has no story at that scale.

**Non-equivocation.** SATROOT proves a log is internally consistent to
whoever holds it. It does **not** prevent split-view: an operator could serve
two divergent, internally valid histories to two parties. Transparency logs
solve this with published roots, gossip and witnessing. SATROOT does not.

**Third-party witnessing is no longer a differentiator.** C2SP
`tlog-witness/v1.0.0` shipped March 2026, `transparency-dev/witness` is
active, and Rekor v2 checkpoints already carry witness cosignatures. Any
claim that verifiable logs lack independent witnessing is out of date.

**Ecosystem maturity.** Sigstore, CT, in-toto and SLSA have production
deployments, multiple independent implementations, and institutional
governance. SATROOT has two implementations by one author.

---

## The pieces SATROOT composes, and their standards

| Concern | Existing standard | SATROOT's position |
|---|---|---|
| Canonical serialisation | **RFC 8785 (JCS)** — note: Informational, Independent Submission, *not* Standards Track; **RFC 8949 §4.2** deterministic CBOR is Standards Track | SATROOT uses sorted-key, separator-tight, non-ASCII-preserving JSON. For the value types the protocol permits this coincides with JCS; **the relationship is documented rather than assumed** — see below |
| Signed events | COSE `COSE_Sign1`, JOSE, DSSE | SATROOT uses a plain signed-JSON envelope with ed25519/HMAC. **A COSE profile would improve interoperability** and is an obvious future deliverable |
| Append-only log + proofs | RFC 6962/9162, **RFC 9942 COSE Receipts**, C2SP `tlog-tiles` | SATROOT uses a per-event `prev_event_id` hash chain, not a Merkle tree. Simpler; no succinct proofs |
| Transparency architecture | **RFC 9943 (SCITT)**, June 2026 | Complementary, not competing — see below |
| Timestamping | **RFC 3161**; OpenTimestamps | Both supported as commitment backends alongside the chain envelope |

### Canonicalisation and JCS

SATROOT's canonical form is deliberately narrow: objects with string keys,
sorted; no insignificant whitespace; non-ASCII emitted literally; all
quantities as ASCII digit **strings**, never JSON numbers, bounded to 512
digits. Because amounts are strings, SATROOT never encounters the
floating-point serialisation rules that make JCS subtle.

That makes SATROOT's canonicalisation a **strict subset of JCS behaviour for
the documents it permits**, with one thing to watch: JCS sorts keys by UTF-16
code unit, Python sorts by code point. These differ only for keys containing
characters outside the Basic Multilingual Plane, which the schema does not
permit in field names. Anyone building an implementation should treat this as
a conformance question, and the corpus in `vectors/` is where it gets
settled.

---

## Relationship to SCITT specifically

**SCITT and SATROOT solve adjacent, non-overlapping problems.** SCITT's
charter explicitly excludes payload semantics — *"the Statement is considered
opaque to the Transparency Service"* — and lists "define data formats for
payload content" as a non-goal. SCITT standardises registration,
non-equivocation and receipts; it deliberately says nothing about what a
statement *means* or what state a sequence of statements produces.

That is precisely the layer SATROOT defines. A SATROOT ledger could plausibly
be registered as SCITT Signed Statements, gaining witnessing and inclusion
proofs it currently lacks, while SATROOT supplies the typed replay semantics
SCITT declines to specify.

Worth noting for anyone working in this area: eighteen individual drafts
currently orbit the SCITT working group, and a striking number concern
**AI-agent action receipts, agent action capsules, canonical payload binding,
and EU AI Act Article 50 profiles**. Several use RFC 8785 JCS for exactly the
digest-binding purpose SATROOT uses its canonical JSON for. None specifies
deterministic replay to typed state.

---

## What this means for someone evaluating SATROOT

If you need **inclusion proofs at scale, non-equivocation across parties, or
an established ecosystem**, use Certificate Transparency, Sigstore, or a SCITT
Transparency Service. Those problems are solved, well, by others.

If you need **a log whose entries have defined meaning, replaying
deterministically to a typed state that any party can recompute offline from
a file**, no standard specifies that today, and that is what SATROOT is for.

The honest summary is that SATROOT is a small, well-tested composition of
established primitives that fills one specific unoccupied gap — not a new
cryptographic idea, and not a replacement for transparency infrastructure.
