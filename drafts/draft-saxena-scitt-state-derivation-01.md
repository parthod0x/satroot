---
title: "Carrying an Application-State Commitment in a SCITT Statement Sequence"
abbrev: "SCITT State Commitments"
docname: draft-saxena-scitt-state-derivation-01
category: info
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
  RFC9597:
  RFC2119:
  RFC8174:

informative:
  RFC8949:
  RFC8785:
  RFC6902:
  RFC9162:
  RFC3161:
  I-D.sato-soos-sov:
  I-D.mih-sokolov-scitt-payload-binding:
  I-D.noa-scitt-ai-agent-receipt:
  I-D.emirdag-scitt-ai-agent-execution:
  I-D.ietf-keytrans-architecture:

--- abstract

SCITT {{RFC9943}} treats the payload of a Signed Statement as opaque to the
Transparency Service. For a class of applications the useful question is not
only whether a statement was registered but what the accumulated sequence of
statements means: a prepaid credit balance, custody of an asset, the
assignment history of a licence. Several individual drafts in the SCITT orbit
now define such sequences independently.

This document does not propose that SCITT interpret payloads. It asks a
narrower question: **where should a commitment to derived application state be
carried, so that a Transparency Service can attest to it without interpreting
the payload it summarises?** Four placements are compared. The document reports
implementation experience, including a class of verification failure that
recurred four times across independent review of one implementation, and which
the placement choice bears on directly.

--- middle

# Introduction

A Transparency Service establishes that a Signed Statement was registered,
that registration was consistent with a published policy, and that the log has
not been rewritten. It deliberately does not interpret the payload. The SCITT
charter lists payload data formats as a non-goal, and {{RFC9943}} states that
the Statement is opaque to the Transparency Service.

That scope decision is correct, and this document does not propose changing
it. But several individual drafts now define ordered, causally linked
application sequences above SCITT:
{{I-D.sato-soos-sov}} defines an object type carrying a state machine and an
append-only signed event stream; {{I-D.noa-scitt-ai-agent-receipt}} defines
hash-chained receipts; {{I-D.emirdag-scitt-ai-agent-execution}} defines signed
sequence numbers and predecessor hashes. Each solves the ordering problem
separately, and each must decide independently where a summary of the derived
state lives, if anywhere.

This document is about that placement decision.

## Relationship to Existing Work

The general pattern is state machine replication and it is not new. Blockchain
execution layers specify a transition function and commit to a state root.
KERI's Key Event Logs replay to key state; its Transaction Event Logs admit
application-defined event types. Sidetree replays anchored operations to DID
Document state. Verifiable log-derived maps derive key/value state from an
input log. {{I-D.ietf-keytrans-architecture}} derives identity-to-key bindings
from a log, and is the closest active IETF work: it faces the same question of
what a service can attest to about derived state without reproducing the
derivation.

Standards-track work exists for the transition mechanism alone: JSON Patch
{{RFC6902}} defines typed operations applied sequentially to structured state,
lacking only signatures, a log, and a commitment.

The mechanism described here is a composition of existing primitives. Nothing
in it is novel and the document does not claim otherwise.

# The Placement Question

A profile that derives state from a Statement Sequence produces a value — a
digest over a canonical serialisation of that state — which a relying party
wants to check. There are four places it can go, and they differ in what a
Transparency Service can say about it.

## In the payload

The state commitment is a field of the event, and the Transparency Service
sees an opaque blob. This is where implementations put it today, including
the one described in {{implementation}}.

**What the Service can attest:** that a statement containing the commitment
was registered at a point in the log. Nothing about the commitment itself.

**Consequence:** two relying parties can hold different sequences for one
Subject and the Service cannot distinguish them, because divergence is only
visible to a party that fetches the statements and replays them.

## In a protected header parameter

A registered COSE header parameter carrying the commitment. The Service still
does not interpret it, but it is now at a defined location, outside the opaque
payload, and can be echoed into a Receipt or indexed without payload
interpretation.

**Open point:** whether this constitutes "interpreting" the statement in the
sense the charter excludes. A parameter the Service copies without
understanding seems to fall on the permitted side, but the group should say
so.

## As a CWT claim

{{RFC9597}} CWT Claims in the protected header are already how SCITT carries
issuer and subject. A claim for derived state is a natural extension of the
same mechanism and inherits its registration discipline.

## As a distinct registered statement type

A checkpoint statement whose payload *is* the commitment, registered
alongside the sequence it summarises, and referring to the sequence position
it covers. The Service treats it as another opaque payload, but a relying
party can locate it by type without replaying anything.

**This is the placement the author found most defensible while implementing**,
and {{implementation}} says why: the checkpoint has to bind more than one
artifact, and a payload field of one event cannot.

# Requirements on the Sequence {#requirements}

Whatever the placement, a profile deriving state must specify four things, and
this document records them because implementation showed each to be a real
source of divergence rather than a formality.

1. **A canonical serialisation.** Both the event and the derived state MUST
   have a canonical byte representation. {{RFC8785}} and the deterministic
   encoding rules of {{RFC8949}} Section 4.2 are suitable.
   {{I-D.mih-sokolov-scitt-payload-binding}} defines `jcs-n` for this purpose;
   an independent implementation of it, and six test vectors, are cited in
   {{implementation}}.

2. **A reducer.** The profile defines admissible event types and, for each,
   the transition applied. **A profile MUST state whether rejection
   invalidates the entire sequence or skips the event leaving state
   unchanged**; two implementations choosing differently derive different
   state from identical input.

   Determinism requires excluding more than the obvious: wall-clock time,
   network state, and iteration order of unordered collections, but also
   Unicode normalisation form, locale-dependent collation, floating-point
   arithmetic, and integer width. Arithmetic should be exact over an
   explicitly bounded domain, with out-of-domain values rejected rather than
   truncated or promoted.

3. **An ordering source.** The total order MUST be declared in the payloads —
   a sequence number and a reference to the digest of the preceding event.
   Registration order is not viable: SCITT permits registering the same
   statement with more than one Transparency Service, so state derived from
   registration order depends on which Service is asked. An earlier version of
   this document raised the choice as an open question. It is not open;
   {{RFC9943}}'s own model settles it.

4. **A completeness statement.** See {{truncation}}. This is the requirement
   implementations are most likely to omit, because omitting it is invisible.

# The Truncation Threat {#truncation}

**A prefix of a valid signed sequence is itself a valid signed sequence.**

Nothing inside a sequence commits to how long it is meant to be. A presenter
who supplies a valid prefix supplies a sequence that verifies completely and
derives a state that is internally consistent, current-looking, and stale.
Every signature checks. Every hash link holds. The reducer runs to completion.

This is the threat that most sharply motivates the placement question, and it
is the one an implementation is most likely to miss, because **every test that
uses an honest sequence passes**.

Three observations from implementation:

**Signatures do not help.** If the party presenting the sequence also holds
the signing keys — the ordinary case for a hosted service — it can produce a
shorter or wholly different history and sign it correctly. Re-signing is not
an attack requiring skill; it is the normal code path.

**A commitment inside the payload does not help either.** It is produced by
the same party from the same truncated input.

**What does help is an external, dated attestation over a checkpoint that
covers the sequence position.** If a third party attested at time T that the
sequence contained N entries, a later presentation of N-2 entries is
detectable — not because the presenter cannot obtain a fresh attestation, but
because it cannot obtain one **dated T**. Backdating requires the attesting
party's key.

This is why the placement matters. A checkpoint that binds only one artifact
is insufficient when the application has more than one — see
{{implementation}}.

# Implementation Experience {#implementation}

The author implemented this pattern twice, in Python and TypeScript. The
second implementation was written from the specification text rather than
ported, and the two agree byte-for-byte on canonical serialisation, event
digests and state commitments across a shared conformance corpus of 33
vectors covering accepted and rejected inputs. **Both were written by the same
author, so this demonstrates that the specification is implementable from its
text; it is not independent validation.** The implementations and corpus are
available under Apache-2.0.

One genuinely independent check exists: an unrelated COSE library verified a
signature produced by this implementation, confirming the `Sig_structure`
construction, protected header encoding and `#6.18` tagging. It validates the
COSE encoding only, not the reducer.

## What repeated review found

An implementation of this pattern was reviewed adversarially in ten rounds by
independent reviewers. Four separate findings shared one shape, and the shape
is what this section is for:

**A verification check whose trust anchor was supplied by the party being
checked.**

1. A canonicalisation comparison whose corpus was generated by the
   implementation under test.
2. A binding between two artifacts recorded in an unsigned file written by the
   party presenting them — the verifier compared the artifacts against that
   file.
3. An RFC 3161 timestamp token verified by reading its `messageImprint` and
   nothing else; a reviewer forged one by replacing 32 bytes in place, leaving
   every DER length valid.
4. After the signature check was added: an {{RFC3161}} token carries the
   certificate that signed it, so a verifier checking the signature verifies
   against a certificate a forger also controls. The documentation compounded
   this by instructing users to obtain the authority's fingerprint from a
   first run — against a forged artifact, the first run is the forgery.

Findings 3 and 4 were each introduced by the fix for the finding before it.

**Relevance to this document:** a state commitment is a verification anchor.
Where it is placed determines who supplied it. A commitment in a payload is
supplied by the sequence's author; a commitment echoed by a Transparency
Service into a Receipt is supplied by a third party. That difference is the
entire security value, and it is invisible in a test suite that only ever
sees honest input.

## Why a checkpoint must bind more than one artifact

The implementation carries two artifacts per subject: a credit ledger and a
separate hash-chained action log. Binding them by recording each one's head in
a file next to the other was insufficient for the reason above — the file was
written by the presenter. The binding became meaningful only when the
attested document covered both heads and both counts, so that agreement
between the artifacts was attested rather than asserted.

A profile whose application has one artifact will not encounter this. A
profile with two will, and a placement that can hold only a single value
forecloses the fix.

## Three findings a reader may find useful

**Canonicalisation is where implementations diverge first.** Sorting of object
keys by code point versus UTF-16 code unit, which differ only outside the
Basic Multilingual Plane; serialisation of numeric values, avoided entirely by
representing all quantities as digit strings; and the treatment of optional
fields, which must be absent rather than null if digests are to agree.

**Host-dependent behaviour is a real hazard.** An early defect made the
accept/reject decision for large numeric values depend on an interpreter
configuration setting rather than on the specification, so the same input was
accepted on one host and rejected on another.

**A conformance corpus is more useful than prose, and vectors are more useful
than corrections.** {{I-D.mih-sokolov-scitt-payload-binding}} defines `jcs-n`
and publishes no test vectors. Implementing it from the text surfaced four
readings a vector would have settled, and one the draft does not settle at
all: whether the exclusion set is name-scoped or path-scoped. Six vectors are
offered separately.

# Scope: Single-Issuer Transparency

{{RFC9943}} describes transparency for statements made by an issuer about a
subject. Sequences in which custody transfers between parties — the licence
and identity examples above — involve multiple issuers over one subject.

Whether that fits the SCITT model is a real question and this document does
not resolve it. Two readings are available: the subject is the constant and
multiple issuers making statements about it is ordinary; or a sequence with
transferred authority is a different structure requiring its own treatment. A
profile author needs an answer before relying on either.

# Non-Goals

This pattern does not provide non-equivocation. A party holding two divergent
but internally consistent sequences cannot determine which is authoritative
from the sequences alone; that is what registration on a Transparency Service
provides.

Neither does it provide succinct proofs. Verification replays the entire
sequence and is linear in its length. Where a relying party needs membership
of a single entry, the inclusion proof mechanisms of {{RFC9943}} and
{{RFC9162}} are appropriate and this pattern is not.

# Security Considerations

{{truncation}} is a security consideration and is stated there rather than
repeated.

**Key compromise is not addressed by this pattern.** If a signing key is
compromised, an attacker who also controls distribution can produce an
alternative sequence, valid under the reducer, diverging from the point of
compromise. Registration does not by itself detect this: the payload is opaque
to the Service, so divergence is detectable only by a party that fetches the
statements and replays them. Profiles requiring recovery semantics should
consider mechanisms such as KERI's pre-rotation and duplicity detection, which
this pattern does not provide.

**Redaction is in tension with state derivation.** Because the commitment
binds every event, removing an event changes the derived state. A profile
whose payloads may contain personal data, subject to a legal right of erasure,
cannot simply delete an event. Mitigations include committing to a salted
digest of the payload rather than the payload, and holding payloads outside
the sequence. A profile that does neither should say so explicitly.

**Determinism is a security property here, not merely a correctness one.** If
two conforming implementations can derive different states from the same
sequence, a relying party can be shown whichever state suits the presenter.

# IANA Considerations

This document has no IANA actions. Should the group prefer the header
parameter or CWT claim placements described above, registrations would be
required in the COSE Header Parameters or CWT Claims registries respectively.

--- back

# Acknowledgements
{:numbered="false"}

The implementation experience in {{implementation}} exists because independent
reviewers repeatedly demonstrated that it was wrong. The classification of
findings 1 through 4 as one recurring shape is theirs, not the author's.
