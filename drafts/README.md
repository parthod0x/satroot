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
