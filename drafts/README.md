# Drafts

## draft-saxena-scitt-state-derivation-00

**Status: NOT READY FOR SUBMISSION.** Two independent reviewers returned
"do not submit this -00" on 2026-08-25, and they were right.

### What was corrected after that review

- `submissiontype: independent` removed. That value means the RFC Independent
  Submission Stream - work *outside* the IETF process - not "an individually
  authored draft". Wrong, and visible in the header before anyone reads a line.
- RFC 6962 replaced with RFC 9162, which obsoletes it.
- RFC 8785 and RFC 8949 moved to informative, matching how the text uses them.
- The residual novelty claim cut.
- KERI's Transaction Event Logs described accurately - they admit
  application-defined event types, so "fixed registry" understated them.
- Automerge corrected: it is a CRDT converging on state, not ordered replay.
- `draft-sato-soos-sov` described as an individual draft and work in progress,
  not as work carrying community standing.
- Rejection semantics specified: a profile must state whether rejection
  invalidates the sequence or skips the event, since implementations choosing
  differently derive different state. SATROOT rejects the whole sequence,
  per SPEC section 8.
- Determinism requirements extended to Unicode normalisation, locale
  collation, floating point and integer width.
- Corrected an overclaim: a Transparency Service cannot detect payload-level
  divergence, because the payload is opaque to it.

### What is still wrong, and why it should not be submitted yet

**The central question is already answered.** The draft asks whether the
reducer's order should come from registration order or from payloads.
Registration order is not viable - SCITT permits registering the same
statement with multiple Transparency Services, so state would depend on which
Service you asked, destroying the offline-verifiability the draft claims.
Both reviewers noted the draft's own Non-Goals section refutes its central
question. Asking a settled question reads as looking for a reason to exist.

**The better question, per both reviewers:** where should a state commitment
be carried so a Transparency Service can attest to it *without* interpreting
the payload - a protected header parameter, a CWT claim, a distinct
registered statement type, or a Receipt extension?

**Zero working-group citations.** Eighteen individual drafts orbit SCITT, several
directly relevant - `draft-mih-sokolov-scitt-payload-binding` on canonical
payload binding, `draft-noa-scitt-ai-agent-receipt` on hash-chained receipts,
`draft-emirdag-scitt-ai-agent-execution` on signed sequence numbers and
predecessor hashes. Not citing them, having researched them, reads as not
having read the group's work.

**Missing: KEYTRANS** - an active IETF working group doing log-derived state
for identity-to-key binding, absent from an IETF draft surveying log-derived
state.

**Missing threat: truncation.** A presenter can supply a valid prefix and
derive a valid but stale state. Nothing in the design proves a sequence is
complete. This is the threat that most sharply motivates the real open
question.

**Unresolved scope question:** RFC 9943 describes single-issuer signed
statement transparency, while this draft's examples involve custody
transferred between parties. Whether that fits SCITT at all needs an answer
before submission.

### The sequence both reviewers recommended instead

1. **Run a cross-implementation canonicalisation comparison** and report the
   result. **DONE** - `docs/COSE_INTEROP.md`: pycose, an implementation this
   author did not write, verified a SATROOT Signed Statement. It validates the
   COSE encoding only. Two findings came out of it, including that pycose
   1.1.0 rejects the RFC 9864 identifier -19, so conformance and compatibility
   currently point in opposite directions.
2. **Review an existing draft.** **DONE, awaiting send** -
   `SCITT_DRAFT_REVIEW.md` in the workspace root reviews
   `draft-fassbender-scitt-time-anchor-05`. It reports an implementation
   finding that strengthens that draft's own contrast with RFC 3161, offers a
   sentence for its section 2.6.6, and asks one genuine question about step 4.
3. **Post a short technical question to the list.** Not done. This is a manual
   send and should follow (2), not precede it.
4. **Then** write a real specification, if there is interest.

## draft-saxena-scitt-state-derivation-01

**Status: BETTER, STILL NOT READY.** The -01 rewrite addresses every defect
the reviewers named. It should still not be submitted until step 3 above has
happened and produced some signal.

### What -01 changed

- **The central question is replaced.** The -00 asked whether the reducer's
  order should come from registration or from payloads. That is settled -
  SCITT permits registering one statement with several Services, so state
  derived from registration order depends on which Service you ask. The -01
  states it as settled in the requirements section and asks the question both
  reviewers proposed instead: **where should a state commitment be carried so
  a Transparency Service can attest to it without interpreting the payload?**
  Four placements are compared.
- **Working-group citations added**: `draft-mih-sokolov-scitt-payload-binding`,
  `draft-noa-scitt-ai-agent-receipt`, `draft-emirdag-scitt-ai-agent-execution`,
  and KEYTRANS, which was the most conspicuous omission - an active IETF group
  doing log-derived state, absent from a draft surveying log-derived state.
- **The truncation threat has its own section**, and it is now the section
  that motivates the placement question. A prefix of a valid signed sequence
  is a valid signed sequence; signatures do not help when the presenter holds
  the keys; what helps is an external dated attestation, because a presenter
  can obtain a fresh one but not a backdated one.
- **Real implementation experience replaces the thin version.** Ten rounds of
  adversarial review produced four findings sharing one shape - *a
  verification check whose trust anchor was supplied by the party being
  checked* - and two of those findings were introduced by the fix for the one
  before. That is content of a kind these drafts are short of, and it bears
  directly on the placement question: a commitment in a payload is supplied by
  the sequence's author.
- **The scope question is stated rather than dodged.** RFC 9943 describes
  single-issuer transparency; custody-transfer examples involve several. Two
  readings are offered and neither is asserted.
- **The self-limiting statement is kept**, in the reviewers' own framing, and
  the acknowledgements credit them for the classification.

### What would make it submittable

A reason to exist that comes from someone else. Post the question in step 3,
and if anyone says "yes, we have this problem too", the draft has standing it
does not currently have. If nobody does, the honest conclusion is that this is
implementation experience worth writing down and not a specification anyone
needs, which is a fine outcome and cheaper than finding out after submission.


## Round 11: the -01 is also not ready, for different reasons

**2026-08-28. Two reviewers, NO-GO on all three documents.** Every point below
was verified against the primary source rather than taken on the reviewers'
word.

- **The RFC 3161 claim in section "What repeated review found" is wrong.**
  "an RFC 3161 token carries its signing certificate" is not a property of the
  protocol: certReq is DEFAULT FALSE (RFC 3161 s2.4.1) and when absent the
  certificates field MUST NOT be present. True of our tokens because we ask
  for it. Corrected in the implementation; the draft still states it.
- **The four placements are not a taxonomy.** A CWT claim *is* carried in the
  protected header, so options 2 and 3 are one structural location. A
  "distinct registered statement type" still carries its commitment in a
  payload, so option 4 is a form of option 1. And the Receipt extension - which
  this file itself named as one of the four alternatives - is missing from the
  draft entirely.
- **The central security argument is wrong.** Placement does not determine who
  supplied a commitment: the issuer supplies it in a payload, a header and a
  CWT claim alike, and a Service that copies a value does not become its
  source. The real distinction is issuer assertion / Service observation /
  Service validation, and only the third is what the draft wants - which a
  payload-blind Service cannot provide.
- **"A single field cannot bind multiple artifacts" is false.** One digest can
  commit to a canonical document holding any number of heads. Our own
  checkpoint already does exactly that.
- **Two cited drafts already do what the draft says is unaddressed.**
  `draft-noa-scitt-ai-agent-receipt-01` defines highestSeq and headHash with
  answered/unanswered/unusable checkpoint states, and says truncation is
  detectable only against an authenticated checkpoint.
  `draft-emirdag-scitt-ai-agent-execution-00` puts chain_hash,
  prev_chain_hash and sequence_number in the protected header, has the Service
  validate continuity, and echoes them in a Receipt.
- **RFC 9943 already addresses completeness** via a shared `sub`: relying
  parties can use it to identify all Transparent Statements for a Subject and
  assess completeness and non-equivocation. The truncation framing needs the
  offline-subset threat model stated explicitly or it overstates the problem.
- **KEYTRANS is mischaracterised**, and "trust anchor" is used for a state
  commitment, which is hazardous in an IETF document where the term has a
  settled meaning.
- **The COSE interop result omits its limitation**: pycose verified the
  deprecated alg -8 path; the default -19 was rejected before signature
  verification. Stating the result without that invites the wrong inference.

### What this means

The -01 does not need community signal. It needs its central model rebuilt,
and after reading the two drafts properly there may be nothing left to
propose that they do not already do. That is a real possible outcome.

**The honest next step is not a -02.** It is the one artefact that survived
round 11 intact: the jcs-n vectors and the exclusion-scope question, which is
new, checkable, and about the specification rather than about us. See
`SCITT_JCS_N_OFFER.md` in the workspace root.
