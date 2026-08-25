# How SATROOT relates to existing work

Researched August 2026, and corrected after two adversarial reviews found the
first version of this document selectively scoped.

**Summary: SATROOT is a compact, well-tested implementation of a
well-established design family — log-derived state. It does not occupy an
empty category. Its contribution is a precisely specified state commitment, a
cross-language conformance corpus, and offline verification from a file.**

---

## First, what SATROOT actually is

Stated precisely, because an earlier version of this document and the README
overstated it.

The kernel defines **one reducer**, with five actions — `mint`, `transfer`,
`burn`, `freeze`, `rotate-authority` — over a fixed state shape: balances,
supply, mint authority, frozen accounts, sequence, and last event id.

The six "profiles" (stable reference units, machine credits, receipts,
identities, licenses, event streams) **add required genesis metadata and
validation. They do not define profile-specific state or transitions.** Each
maps its lifecycle onto the same account/balance operations.

So SATROOT is **a typed token-and-account ledger with domain-labelled
profiles**, not a general application-state machine framework. Anyone
evaluating it should hold it to that description.

---

## The pattern is old, and named

Deterministic replay of an ordered log to typed state is **state machine
replication** (Schneider, 1990). It is not a new idea, and this document
should not have implied otherwise.

Contemporary systems implementing it:

| System | Ordered signed log | Deterministic replay | State commitment | Verifiable offline from a file |
|---|---|---|---|---|
| **Ethereum** (and EVM chains) | yes, RLP-encoded signed txs | yes — a formally specified transition function | yes, state root | no — requires the chain |
| **CometBFT / ABCI** | yes | yes — apps are deterministic state machines | yes, AppHash in the header | no — requires consensus |
| **Sidetree** (DIF) | yes, anchored ops | **yes — replayed under common deterministic rules** | DID Document state | partially |
| **AT Protocol** | yes, signed commits, DAG-CBOR | records, not derived state | Merkle Search Tree root | **yes** — repo exports as a CAR file |
| **KERI KEL / TEL** | yes | **yes** | key state / registry state | yes |
| **Trillian log-derived map** | yes | **yes, by definition** | map root | audit is O(n); entry proofs are efficient |
| **Automerge** | op log | yes | document state | yes |
| **draft-sato-soos-sov** (SCITT-adjacent) | yes, Event Stream | **yes — SO Type defines a state machine** | derived typed graph | — |
| **SATROOT** | yes | yes | state hash | **yes** |

**Ethereum disproves any mechanism-level novelty claim outright.** Canonical
serialisation, signed events in total order, a formally specified typed
transition function, a state commitment third parties recompute — with
cross-client differential testing far beyond a 33-vector corpus. Omitting it
from a comparison table, in a project whose flagship demonstration is a chain
anchor, was indefensible.

**The honest distinction** is not novelty of mechanism. It is the trust and
availability model: Ethereum, CometBFT and Sidetree bind state transition to
a **consensus or sequencing system** and require a globally shared history.
SATROOT verifies **your** ledger from **your** file, with no shared history,
no consensus, and no network. AT Protocol comes closest — its repos verify
offline from a CAR file — but its MST commits to the **current record set**,
not to state derived by a transition relation, so balances and custody are
not recoverable from the root.

That is a real difference. It is a difference of deployment model and scope,
not of invention.

### Adjacent standards worth naming

**RFC 6902 (JSON Patch)** is standards-track and already supplies typed
operations applied sequentially to structured state — a general deterministic
transition mechanism, lacking only signatures, a log, and a commitment. Since
this document claims composition rather than invention, JSON Patch belongs in
the list of things being composed from.

**draft-sato-soos-sov** is the omission that mattered most. It is
SCITT-adjacent and defines an SO Type specifying a state machine, an
append-only causally ordered signed Event Stream, state derived from that
stream, and SCITT submission of entries. Any claim that no SCITT-adjacent
work specifies typed state evolution is untenable.

**KERI is more extensible than previously stated here.** ACDC allows any
number of transaction-event types for different applications, TELs can track
public or private transaction state, and BADA-RUN provides monotonic
authenticated update rules. Calling the TEL a "fixed narrow domain" understated
it. The remaining difference is that KERI has no single general reducer and no
whole-application state commitment equivalent to SATROOT's snapshot hash.

---

## The narrowest claim that survives scrutiny

Not "no standard specifies this." That is false.

What appears to be true, and is worth stating only in this form:

> No **IETF or W3C standards-track** document specifies deterministic typed
> replay to application state above a signed log, **independent of a
> consensus or sequencing system**, with a portable state commitment
> verifiable offline from a file.

Even that is a conjunction of five conditions, and a conjunction assembled
after the fact can always be made to fit. It should be read as a description
of where SATROOT sits, not as a claim to territory.

**The strongest honest framing:** SATROOT applies a KERI-like architecture to
account-ledger semantics, adds a whole-state commitment, and pins it with a
cross-language conformance corpus. That is checkable and survives contact with
someone who knows the field.

---

## Where established systems are better

**Verification cost.** CT and Rekor give **O(log n)** inclusion proofs.
SATROOT replays the entire log — **O(n)**. Trillian's log-derived map
separates expensive global auditing from efficient per-entry client queries;
SATROOT does not, and every ordinary verifier pays full replay. Google built
a log-derived map, shipped it experimentally, and **removed the
non-experimental Map API** — the fair reading is low demand and a fatal
cost profile, not merely an abandoned opportunity.

**Non-equivocation.** SATROOT does not prevent split-view: an operator can
serve two divergent, internally valid histories to two parties. Transparency
logs solve this with published roots, gossip and witnessing.

**Witnessing is not a differentiator.** C2SP `tlog-witness/v1.0.0` shipped
March 2026; Rekor v2 checkpoints carry witness cosignatures.

**Maturity.** Sigstore, CT, in-toto and SLSA have production deployments,
multiple independent implementations, and institutional governance. SATROOT
has two implementations by one author.

---

## Weaknesses a domain expert would ask about

The list above is performance and maturity — the kind a benchmark reveals.
These are the ones that require knowing the field to ask, and an earlier
version of this document omitted all of them.

**Key compromise.** This is the sharpest gap, and it is conspicuous precisely
because KERI is named above as the nearest relative — pre-rotation and
duplicity detection under key compromise is what a KEL exists for. SATROOT
has **no pre-rotation, no duplicity detection, and no defined recovery
procedure.** If a signing key is compromised, an attacker who also controls
distribution can produce an alternative valid history from the compromise
point forward. `rotate-authority` changes the mint authority going forward;
it does not repudiate anything already signed, and prior state is only as
trustworthy as the key that signed it was at the time. There is no protocol
answer to "which of these two valid histories is real."

**Erasure.** An append-only signed log with a binding state commitment is in
direct tension with a GDPR right to erasure. SATROOT specifies **no
redaction, no salted commitments, and no off-log payload mechanism.** Removing
an event breaks the hash chain and changes the state hash. Any deployment
holding personal data in event payloads has an unresolved problem, and any
claim of GDPR *suitability* has to be qualified by this.

**No formal semantics.** The transition relation is specified in **prose and
pinned by test vectors**, not formally verified. There is no type system, no
machine-checked specification, no proof of determinism. Two implementations
agreeing on 33 vectors is evidence, not proof — and both were written by the
same author.

**Scale.** No sharding, no compaction, no snapshot-with-proof. A long-lived
ledger grows without bound and replay cost grows with it.

---

## Canonicalisation, measured against RFC 8785

Full result in `docs/CANONICALISATION.md`; reproduce with
`PYTHONPATH=src python src/satroot_jcs.py`.

Several drafts in the SCITT orbit use RFC 8785 (JCS) for the same
digest-binding purpose SATROOT uses its canonical JSON for, so whether the
two agree is worth measuring rather than assuming.

**13 of 15 cases agree.** The two that diverge do so for one reason: JCS
sorts object keys by **UTF-16 code unit**, Python's `sort_keys=True` sorts by
**Unicode code point**, and those orders differ whenever a key contains a
character outside the Basic Multilingual Plane, since UTF-16 encodes those as
surrogate pairs that sort below ordinary BMP characters.

The divergence is unreachable through any schema-valid SATROOT record,
because field names come from a fixed ASCII vocabulary — but that is a
property of the schema, not of the canonicalisation. Any profile permitting
user-supplied object keys must choose a scheme explicitly.

Neither scheme normalises Unicode: NFC and NFD forms remain distinct keys
under both, and both emit identical bytes. Normalisation is therefore a
producer-side concern that no canonicalisation scheme reconciles.

Numbers are out of scope in this comparison: RFC 8785 requires ECMAScript
`Number::toString` semantics, and `satroot_jcs` rejects floats rather than
approximating it. SATROOT never emits a JSON number for a quantity, so the
result is unaffected.

## Relationship to SCITT

SCITT treats the Statement payload as opaque **to the Transparency Service**,
and the charter lists payload data formats as a non-goal. That was a
deliberate decision — payload semantics are where interoperability becomes
hard — and it should not be characterised as a vacancy waiting to be filled.

SCITT is also explicitly **extensible**: application profiles may define
payload semantics, and several already do. "Adjacent and non-overlapping" was
too absolute. There is real overlap in signed statements, ordering,
commitments and verification; the application reducer is an additional layer
above.

**Terminology note:** RFC 9943 already uses *replayability* for replaying
registration into the Verifiable Data Structure. To avoid collision, SATROOT's
property is better called **application-state derivation**.

---

## What this means for someone evaluating SATROOT

If you need inclusion proofs at scale, non-equivocation, key-compromise
recovery, or an established ecosystem — use Certificate Transparency,
Sigstore, a SCITT Transparency Service, or KERI. Those problems are solved
elsewhere, by more people, better.

If you want a small, inspectable, dependency-free ledger whose state any
party can recompute offline from a file, with a cross-language conformance
corpus pinning the rules — that is what SATROOT is, and it is a modest and
useful thing to be.
