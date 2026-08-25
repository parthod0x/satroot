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

1. **Run a cross-implementation canonicalisation comparison** against the
   payload-binding draft's JCS implementations on a shared record, and report
   the result - agreement or disagreement, both are useful. That draft credits
   contributors by name. Costs an afternoon, requires no standing, and is
   unambiguously not self-promotion.
2. **Review an existing draft** - `draft-fassbender-scitt-time-anchor` is
   directly adjacent to the anchoring work already implemented here.
3. **Post a short technical question** to the list about whether there is
   interest in a common application-sequencing convention across the existing
   profiles, proposing a specific answer.
4. **Then** write a real specification, if there is interest.

The implementation experience section is genuine content of a kind these
drafts are short of. The self-limiting statement - that two implementations by
one author demonstrate the specification is implementable but are not
independent validation - was singled out by both reviewers as the strongest
line in the document. Keep it.
