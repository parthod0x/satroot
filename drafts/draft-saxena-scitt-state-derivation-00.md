---
title: "Application-State Derivation over a SCITT Statement Sequence"
abbrev: "SCITT State Derivation"
docname: draft-saxena-scitt-state-derivation-00
category: info
submissiontype: independent
ipr: trust200902
area: Security
keyword:
  - transparency
  - supply chain
  - state machine
  - COSE
stand_alone: yes
pi: [toc, sortrefs, symrefs]

author:
  - ins: P. M. Saxena
    name: Parth Mauria Saxena
    email: parthms.id@gmail.com

normative:
  RFC9943:
  RFC9052:
  RFC8949:
  RFC8785:
  RFC2119:
  RFC8174:

informative:
  RFC6902:
  RFC6962:

--- abstract

SCITT {{RFC9943}} defines an architecture in which Signed Statements about a
Subject are registered on an append-only Verifiable Data Structure, and
treats the payload of a Signed Statement as opaque to the Transparency
Service. This document describes a complementary layer: given the ordered
sequence of Signed Statements sharing a Subject, a profile may define a
typed transition relation such that replaying the sequence yields a
deterministic application state, together with a commitment to that state
which any party can recompute offline.

This document does not propose changes to SCITT. It describes an
application-layer pattern, reports implementation experience from two
interoperating implementations, and raises questions about where such a
state commitment ought to be carried.

--- middle

# Introduction

A Transparency Service establishes that a Signed Statement was registered,
that registration was consistent with a published policy, and that the log
has not been rewritten. It deliberately does not interpret the payload.
The SCITT charter lists payload data formats as a non-goal, and
{{RFC9943}} states that the Statement is considered opaque to the
Transparency Service.

For a class of applications, the useful question is not only "was this
statement registered" but "what does the accumulated sequence of statements
mean". Examples include prepaid credit balances consumed by automated
agents, custody of an asset transferred between holders, and the assignment
history of a licence. In each case, the value of the log lies in a state
derived from it, and that derived state is what a relying party needs to
check.

This document describes how such a derivation can be specified above SCITT
without modifying it.

## Relationship to Existing Work

The general pattern is state machine replication, and it is not new. Several
systems implement ordered signed logs with deterministic replay to typed
state: blockchain execution layers specify a transition function and commit
to the resulting state root; the Key Event Logs of KERI replay to key state;
Sidetree replays anchored operations to DID Document state; and Verifiable
Log-Derived Maps derive key/value state from an input log.

Standards-track work also exists for the transition mechanism alone: JSON
Patch {{RFC6902}} defines typed operations applied sequentially to structured
state, lacking only signatures, a log, and a commitment.

What those systems have in common is that state derivation is bound either
to a consensus system, to a sequencing system, or to a single fixed domain.
This document is concerned with the narrower case where the derivation is
specified in a profile, is independent of any consensus mechanism, and where
a relying party can verify the derived state from a file without contacting
a service.

The mechanism described here is therefore a composition of existing
primitives, not a new one. Its only claim to novelty is the specific
combination.

# Conventions and Definitions

{::boilerplate bcp14-tagged}

Statement Sequence:
: The ordered sequence of Signed Statements sharing a Subject, as registered
  on a Transparency Service.

Reducer:
: A deterministic function `f(S_prior, E) -> S_next`, defined by a profile,
  mapping a prior application state and an event to a next application
  state, or rejecting the event.

State Commitment:
: A cryptographic digest over a canonical serialisation of the application
  state, recomputable by any party holding the Statement Sequence.

# Model

A profile conforming to this pattern specifies four things.

1. **A payload format.** The payload of each Signed Statement carries an
   event. The payload is opaque to the Transparency Service and interpreted
   only by the profile.

2. **A canonical serialisation.** Both the event and the derived state MUST
   have a canonical byte representation, so that independent implementations
   digest identical bytes. {{RFC8785}} and the deterministic encoding rules
   of {{RFC8949}} Section 4.2 are suitable choices.

3. **A reducer.** The profile defines the admissible event types and, for
   each, the transition applied to the prior state. The reducer MUST be
   total in the sense that every event either produces a next state or is
   rejected; it MUST NOT depend on wall-clock time, network state, iteration
   order of unordered collections, or any input outside the Statement
   Sequence.

4. **A state commitment.** A digest over the canonical serialisation of the
   derived state.

Verification is then: obtain the Statement Sequence, verify each Signed
Statement per {{RFC9052}}, apply the reducer in order, and compare the
resulting state commitment against the value being asserted.

## Ordering

The reducer requires a total order over the Statement Sequence. Two sources
of order are available and they are not equivalent: the order in which
statements were registered on the Transparency Service, and an order
declared within the payloads themselves, for instance by a sequence number
and a reference to the digest of the preceding event.

Payload-declared ordering makes the sequence self-describing and verifiable
from a file alone, at the cost of duplicating information the log already
holds. Registration ordering avoids duplication but makes verification
dependent on the Transparency Service's view. **Which of these a profile
should prefer is an open question**, and is the primary question this
document raises.

## Non-Goals

This pattern does not provide non-equivocation. A party holding two
divergent but internally consistent Statement Sequences cannot determine
which is authoritative from the sequences alone; that is precisely what
registration on a Transparency Service provides, and is the reason this
layer is described as complementary to SCITT rather than as an alternative.

Neither does it provide succinct proofs. Verification as described replays
the entire sequence, and is therefore linear in its length. Where a relying
party needs to check membership of a single entry rather than the whole
derived state, the inclusion proof mechanisms of {{RFC9943}} and
{{RFC6962}} are appropriate and this pattern is not.

# Implementation Experience

The author has implemented this pattern twice, in Python and TypeScript.
The second implementation was written from the specification text rather
than ported from the first, and the two agree byte-for-byte on canonical
serialisation, event digests, and state commitments across a shared
conformance corpus of 33 vectors covering both accepted and rejected inputs.
Both were written by the same author, so this demonstrates that the
specification is implementable from its text; it is not independent
validation. The implementations and corpus are available under Apache-2.0.

Three findings may be useful to others attempting the same thing.

**Canonicalisation is where implementations diverge first.** The
differences encountered were: sorting of object keys by code point versus
UTF-16 code unit, which differ only outside the Basic Multilingual Plane;
serialisation of numeric values, avoided entirely by representing all
quantities as digit strings; and the treatment of optional fields, which
must be absent rather than null if digests are to agree.

**Host-dependent behaviour is a real hazard.** An early defect made the
accept/reject decision for large numeric values depend on an interpreter
configuration setting rather than on the specification, so the same input
was accepted on one host and rejected on another. Any profile defining a
reducer should bound the domain of its value types explicitly rather than
relying on implementation defaults.

**A conformance corpus is more useful than prose.** Every ambiguity
resolved during the second implementation was resolved by adding a vector,
not by amending the specification text.

# Security Considerations

**Key compromise is not addressed by this pattern and requires profile
attention.** If a signing key is compromised, an attacker who also controls
distribution of the Statement Sequence can produce an alternative sequence,
valid under the reducer, diverging from the point of compromise. Replay
alone cannot distinguish the two. Registration on a Transparency Service
mitigates this by making divergence detectable; profiles requiring recovery
semantics should consider mechanisms such as the pre-rotation and duplicity
detection used by KERI, which this pattern does not itself provide.

**Redaction is in tension with state derivation.** Because the state
commitment binds every event, removing an event changes the derived state.
A profile whose payloads may contain personal data, and which is subject to
a legal right of erasure, therefore cannot simply delete an event.
Mitigations include committing to a salted digest of the payload rather
than the payload itself, and holding payloads outside the sequence. A
profile that does neither should say so explicitly.

**Determinism is a security property here, not merely a correctness one.**
If two conforming implementations can derive different states from the same
sequence, a relying party can be shown whichever state suits the presenter.

# IANA Considerations

This document has no IANA actions.

--- back

# Acknowledgements
{:numbered="false"}

This document reports implementation experience rather than proposing new
mechanism, and is offered to the SCITT community as a basis for discussion
about where an application-state commitment ought to be carried.
