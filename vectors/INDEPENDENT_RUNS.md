# Independent runs of the SATROOT-1 conformance corpus

A run is *independent* if the person who did it is not the author of this
repository and did not have the author walk them through it.

## Runs recorded so far

| date | who | implementation | language | result | report |
|---|---|---|---|---|---|
| 2026-08-29 | anonymous, **AI-assisted** | ~540-line replay written from `SPEC.md` alone | Python 3.12 | 33/33 then, 64/64 at `074de10` — **and twenty-four specification defects across six rounds** | below |

**The passing score is the least important thing in that row**, and the
implementer said so first, asking that it not be recorded as a clean result
without the findings attached. It is recorded as AI-assisted at their own
request; it is not a named human implementer, and it should not be described
as one.

What makes it the first genuinely independent run is not the 33/33. It is
that the implementation was written from the specification by someone who
never opened `src/satroot1.py`, `verifiers/typescript/src/satroot.ts`, or
`scripts/generate_conformance_vectors.py` — and that it disagreed with the
reference about an accept/reject decision, which no previous run could have
surfaced.

A **second attempt the same day was blocked** before writing protocol logic,
by finding 1 below. That report is also a result: the specification was
unusable as written, and stopping was the correct response to it.

### What it found, all independently verified before being accepted

| # | finding | verified | status |
|---|---|---|---|
| 1 | §5 listed `rules_hash` and `nonce` as **required** genesis fields. No vector carries either; an implementation enforcing §5 literally rejects every valid ledger at its first event. §5 also omitted `sequence`, which *is* required. | 0 of 33 genesis records carry `rules_hash` | **fixed** |
| 2 | Leading-zero amounts: the reference **accepted** `"0400"` while the corpus asserted rejection via `reject-leading-zero-amount`, and the spec said nothing. Three-way inconsistency. | `parse_amount` matched `[0-9]+`; rechained vector accepted by the reference | **fixed** — canonical form now required in §6.1a and enforced |
| 3 | Seven rejection vectors are decided by a stale `event_id`, not by the rule they are named for. The generator edited a field of a signed record without recomputing the id. | all seven confirmed stale at the tampered event | **fixed** — all seven rechained; `_rechain` in the generator stops it recurring |
| 4 | Consequently ten protocol checks can be deleted at once and the corpus still reports 33/33, including five of §8's ten MUST conditions (8.2, 8.4, 8.5, 8.8, 8.9). | mechanism confirmed via 3 | **fixed** — 11 vectors added; §8.2 and §8.1 also had isolation gaps not in the original report |
| 5 | **§2.6's "non-ASCII emitted raw, not backslash-u escapes" is unexercised.** Serialising with `ensure_ascii=True` — violating the rule — still scores 33/33. It is the rule most likely to fork across languages, since Python escapes by default and JavaScript does not. | reproduced: 0 failures with the rule violated | **fixed** — `valid-non-ascii-metadata-demo` now fails under `ensure_ascii=True` |
| 6 | HMAC key encoding is underspecified and the natural reading is wrong. §6.6.1 says `hex(HMAC-SHA256(key, ...))` and the README calls the secrets "(hex)", but the MAC key is the 64-character ASCII hex **text**, not the 32 decoded bytes. | confirmed: text matches the corpus signature, decoded bytes do not | **fixed** — stated in §6.6.1 |
| 7 | §8.9 (`state_hash`) and §8.10 (profiles) are never exercised — no event carries a `state_hash`, no vector carries a profile. `max_supply: null` never appears. | 0 events, 0 vectors, 0 genesis respectively | **fixed** — `state_hash` and `max_supply: null` vectors added; profiles remain unexercised |
| 8 | `reject-overspend` is a **burn**, so §8.3 is untested for transfers. | confirmed | **fixed** — `reject-transfer-overspend` added |
| 9 | §7 commits to `profile`/`profile_mode`, which §5 never defines. Absent to `null` was a guess; "omit the key" would change every state hash. | — | **fixed** — §7 now defines both, and absent commits as `null` |
| 10 | `supply` is committed by §7 and defined nowhere — circulating or cumulative-minted. No vector distinguishes them, so two implementations can disagree and both score 33/33. | confirmed `supply == sum(balances)` in every valid vector | **fixed** — §7 defines it as circulating |
| 11 | Smaller: §8 omits mint- and freeze-by-non-authority; "a ledger must begin with genesis" is only implied; §8.1 reads as permitting a second genesis under a different `root_id`; `decimals` typing was unstated, so `true` passing as an integer is a corpus-only rule. | — | **fixed** — `decimals` typed, §8 gaps closed by the new vectors |

**Ten of the eleven are closed, the corpus grew from 33 vectors to 44, and
both implementations gained a rule they were missing.** Profiles (§8.10)
remain unexercised — there is no profile vector — and that is the one item
from this report still genuinely open.

## Round two, same day: the genesis record was never authenticated

Two further independent runs against `b947519` (44 vectors). Both passed
44/44 unmodified — one of them a **separate clean-room implementation**, so
three independent implementations now agree — and both flagged the same
thing.

**`replay` called `apply_genesis` without passing the verifier at all.** A
genesis with a forged, empty or entirely absent signature replayed clean
under `demo`, `hmac-sha256` and `ed25519` alike. Reproduced here before
acting on it.

Genesis is the record that fixes `mint_authority`, `max_supply` and the
whole initial allocation, so every downstream event was being authenticated
against a root anyone could author — a chain that was sound above a hinge
that was not. `reject-forged-signature-demo` forges a *transfer*; nothing in
44 vectors touched a genesis signature.

**The TypeScript verifier had the identical hole**, with the same signature
and the same omission at the call site. Two implementations, written months
apart, both read §2.5 the same way — which is why this is a specification
defect first: §2.5 scoped its `signer`/`signature` requirement to
*non-genesis* events, and §5's field list named neither. Nothing in the
document ever said a genesis was signed, while §8.7 rejects when "a required
signature check fails" and every corpus genesis carries a real signature.
Both readings were defensible. That is exactly why no vector caught it.

Resolved toward **genesis MUST be signed** — new §5.1, with §8.7 naming it.
Both implementations fixed, seven vectors added.

| also found | status |
|---|---|
| `reject-broken-prev-event-id` still carried a stale `event_id` — one survivor of the earlier sweep, so the chain check was still not load-bearing | **fixed** — rechained |
| No vector had `signer != from`, so an implementation letting anyone move anyone's balance scored full marks | **fixed** — transfer and burn arms both covered |
| Both digit-bound vectors also overspend, so the bound was never the deciding check | **fixed** — isolated using `max_supply: null` |
| No vector carried a `signature_scheme` the verifier rejects, which is how the genesis hole stayed hidden | **fixed** |
| A `demo` genesis carrying `signature_key_id` was accepted (§6 says it must be absent) | **fixed** |
| §8.10 profiles — the last open item from round one | **closed**, see below |

### Profiles: the last finding, closed by agreement

The second implementation wrote four profile vectors against
`protocol/satroot1.profile-registry.json` and reported a **byte-identical
state hash** to ours for a `SATROOT-STABLE-1` reference-only genesis. All
four were re-checked here and agree.

Adding them immediately found a third divergence: **the TypeScript verifier
performed no profile validation at all** — unknown profiles, wrong modes and
missing required fields were all accepted, because the committed
`profile`/`profile_mode` members had always been `null` and nothing
exercised the registry. Now implemented at registry level.

The residual he flagged is closed too: §7 referred to the profile fields
"carried by the genesis record (section 5)" while §5 named neither, so the
forward reference dangled and the field names had to be inferred from §7's
own table. That guess was right, and it was still a guess. Now **§5.2**.

## Round three: a stop, and arbitrary JSON in the state hash

Two more runs against `e26ef0b` (57 vectors).

**One stopped before implementing**, on §5.1: the sentence said a genesis
carries `signature_scheme` "where the scheme is not `demo`", while all 15
valid genesis records in the corpus carry one and §6.6.1 selects the
verifier by it. No vector distinguished the readings. Reproduced: the
reference *accepts* a demo genesis with the field absent, defaulting to
`demo`, so the field is optional and the sentence was simply wrong. Stopping
was the correct response, and §5.1 now states the metadata rules explicitly.

The same report found §6.6.1's `signature_key_id` sentence contradicted §6:
it said a missing key id is always rejected, while `demo` requires it
absent. Now split into the two cases it always was.

**The other passed 57/57 and found the significant one:**

**A `profile_mode` with no `profile` was validated against nothing and
committed verbatim into the §7 state hash.** Confirmed here: `"reference-only"`,
`"total garbage"`, `12345` and `{"a": 1}` were all accepted, each producing a
different state hash, with the raw value committed rather than `null`.
Arbitrary JSON — including a nested object — reached the state commitment,
so two ledgers identical but for an orphan mode replayed as valid with
different hashes. That is the leading-zero defect again: one logical state
with many spellings. Both implementations now reject it, and §5.2 states the
pair rule.

| also found | status |
|---|---|
| The reference rejects a whitespace-only profile field while §5.2 said "non-empty", so the two would diverge on a real ledger and no vector separated them | **fixed** — §5.2 now says non-blank, and a `"   "` vector pins it |
| `reject-profile-missing-genesis-field` deletes a field, so nothing exercised one present-but-invalid — which let an implementation checking presence only score 57/57 | **fixed** — empty, blank and non-string vectors added |
| `reject-genesis-balance-exceeds-digit-bound` uses a 513-digit balance, so §6.1a decides it and the genesis supply rule was never the deciding check | **fixed** — isolated with a 2,000,000 allocation against a 1,000,000 cap |
| §§6.2–6.3 said "signer controls sender account" without defining control; two implementations independently guessed string equality and the corpus agreed, but the text did not say so | **fixed** — §6.7 |
| `reject-genesis-scheme-mismatch` is still not isolated | **won't fix, documented** — see below |

### The scheme-match check cannot be isolated, and §6.6.1 now says so

Both attempts to isolate it — ours and the contributed one — trip a
different rule first. That is not a corpus defect. **A verifier that ignored
`signature_scheme` entirely would still fail to verify a signature produced
under a different scheme**, because the bytes differ and every scheme
prefixes its own name. The check is defence in depth, not an independently
observable rule, and §6.6.1 now states that rather than leaving a vector
that appears to test something it does not.

### An implementer's own defect the corpus missed

Worth recording because it cuts both ways: the second implementation passed
57/57 while violating §5.2, having checked only that required profile fields
were *present*. Empty strings, `null`, `42` and `[]` all passed. Nothing in
the corpus had a present-but-empty field, so the corpus could not see it,
and it was found only by probing the new specification text against both
implementations. The vectors above close that hole.

## Round four: the corpus caught an implementer, and the spec was wrong about itself

Two runs against `e758309` (63 vectors). One reported **62/63 on the first
attempt** — the failure was theirs, `reject-profile-field-blank`, and it was
the exact ambiguity they had flagged the round before and guessed wrong on.
§5.2 resolved it as non-blank, the new vector found their literal reading
immediately, and they fixed it to 63/63. **That is the first time the corpus
has caught a defect in an independent implementation**, and it is the loop
working in the intended direction rather than only inward.

The other reported a clean **63/63**, byte-identical under
`PYTHONHASHSEED=1` and `999`.

### The §6.6.1 rationale was wrong, and dangerously so

Last round I wrote that the scheme-match check was "defence in depth rather
than an independently observable rule" and that "no conformance vector can
isolate it". The argument was that a verifier ignoring `signature_scheme`
would still fail on a signature made under another scheme, since the bytes
differ.

**That covers only half the cases.** It misses a signature that is valid for
the verifier in use while the declared scheme lies — a `demo` record with
`signature: "demo"` but `signature_scheme: "ed25519"` presents bytes the demo
verifier would otherwise accept, and only the scheme check rejects it.

Verified here by ablation: an implementation whose demo verifier ignores
`signature_scheme` fails exactly one vector out of 64, and it is the shipped
`reject-genesis-scheme-mismatch`. So the rule is observable, the corpus does
pin it, and the paragraph asserting otherwise was telling implementers a
rule was unobservable and therefore skippable. Replaced with the real reason
it is easy to miss.

**The report's own claim was also wrong**, in the other direction: it said
the shipped vector does not isolate the check and that deleting the check
still scores 63/63. It does not — deleting it fails that vector. Their
contributed replacement, which drops `signature_key_id`, is decided by
`signature_key_id is required for ed25519` rather than by scheme-match, so
it is not the isolation it was offered as, and it is not merged. The finding
that mattered — that my justification was false — stands and is fixed.

### A specified rule nothing exercised

§5.1 permits a `demo` genesis to omit `signature_scheme`, defaulting to
`demo`. Every genesis in the corpus stated it explicitly, so the default was
portable by luck. `valid-genesis-implicit-demo-scheme` closes it: an
implementation that requires the field instead of defaulting it fails that
vector alone. Both implementations already defaulted correctly.

## Round five: the same vector, third time, and the reason it kept recurring

Two runs against `1beacfa` (64 vectors). Both passed **64/64** unchanged.

**The §6.6.1 prose was fixed last round; the vector was not.** The report
was blunt about the pattern, and correctly: `reject-genesis-scheme-mismatch`
was generated with two defects at once — it declared a mismatched scheme
*and* carried a `signature_key_id` — and three rounds of discussion went to
the rule rather than to how the vector was built. The rule was never in
doubt; both implementations had it right throughout.

My claim last round that the vector already pinned the rule was measured
against an **incoherent ablation**: I removed the check from the verifier
while leaving scheme-*dependent* metadata validation in place, which is not
an implementation anyone would write. Measured properly — an implementation
that never reads `signature_scheme`, and so cannot apply scheme-dependent
`signature_key_id` rules either — the shipped vector rejected via the
demo/key-id rule and detected nothing.

Verified both ways before changing anything:

| | shipped vector | with `signature_key_id` removed |
|---|---|---|
| conforming reference | REJECT | REJECT |
| scheme-blind implementation | REJECT (wrong reason) | **ACCEPT** |

So the one-field edit is the fix, and it is now in the generator. Adopted as
a replacement rather than a second near-identical vector, as the report
suggested.

**Two consecutive rounds of mine were wrong about this same rule**, in
opposite directions — first that no vector could isolate it, then that one
already did. Both were prose written to close a round, and neither was
checked by anything until someone else measured it.

### A stale sentence introduced by the previous fix

Adding `valid-genesis-implicit-demo-scheme` made §5.1's "every genesis in
the conformance corpus states it explicitly" false the moment it shipped.
Corrected to describe both forms, with the historical note scoped to the
then-current corpus.

## Round six: no defects, and a caveat on every number quoted above

Two runs against `074de10`. Both **64/64** unchanged. The one-field vector
fix is confirmed working from both sides: an ablation removing only the
declared-scheme/verifier-scheme comparison now fails
`reject-genesis-scheme-mismatch` and nothing else. Third round on that
vector, closed.

### The ablation counts were never as objective as they were presented

The implementer volunteered a correction against their own headline number,
and it is the most useful thing in this round:

> my ablation deletes one named check at a time from my implementation's
> structure. It was never a model of a plausible independent
> implementation... The same caveat applies retroactively to every ablation
> number I've quoted, including the headline "ten checks deletable" from
> round 1. Those measure my decomposition of the rules, not an
> implementation-independent notion of coverage.

**That is right, and this file has been quoting those counts as though they
were objective.** The 10 → 6 → 3 → 2 → 1 progression measures one
implementation's decomposition of the rules, not coverage in any absolute
sense. The direction was real and every step produced a merged vector, but
the numbers describe a relationship between two specific implementations.
Recorded here rather than corrected away, because the temptation to keep
quoting a clean-looking series is exactly how an unchecked claim survives.

### The more important observation: convergence weakens the signal

> an independent implementation that has converged with yours is no longer
> generating much information about the spec, because I'm now reading it the
> way you do... I'd treat a clean result from me as weaker evidence now than
> it was in round 1.

This is the sharpest point anyone has made across six rounds, and it should
govern what happens next. The findings that mattered most — a forgeable
genesis, arbitrary JSON in the state hash, leading zeros — came from
*unconstrained first guesses*, before the implementer had absorbed the
document's assumptions. Those are spent.

**A clean pass from a converged implementation is close to no evidence.**
What would produce signal is an implementation that has not converged: a
different language, a different structure, someone reaching for a JSON
library that orders keys differently or a bignum type that normalises digit
strings. That is the argument for the human implementer run, and it is why
one is worth more than another round here.

### Two coverage gaps closed, neither a defect

Both raised by the implementer as gaps rather than findings:

- **58 of 64 vectors ran on `demo`**, so the real signature paths were the
  thinnest-covered area in the corpus. Added a second full lifecycle under
  each of `hmac-sha256` and `ed25519`; real-scheme vectors 6 → 8.
- **No ledger exceeded five events**, so sequence and `prev_event_id` were
  only ever exercised at trivial depth. `valid-long-chain-demo` runs 21
  events; longest ledger 5 → 21.

### Two wording defects in the specification

Both in prose, neither affecting any implementation:

- §5.1 said every corpus genesis carries "a real signature". 13 of 16 valid
  genesis records carry the placeholder `demo`; across the whole corpus 112
  of 133 signatures are the literal string. Now "a `signature` field its
  selected verifier accepts".
- §6.6.1 said every scheme carries its result "as a prefixed lowercase-hex
  string". `demo` carries the literal `demo`. Now stated per scheme.

### The contributed vectors

14 hardened vectors came with the report: the seven above rechained so the
named rule is the deciding check, plus new cases for transfer-overspend,
mint-over-max-supply, foreign `root_id`, frozen mint and transfer
recipients, and a per-event `state_hash`.

**All 14 were re-checked against this project's own reference before being
accepted, and all 14 are rejected for the reason in their name** — one of
them only after finding 2 was fixed, which is how that divergence surfaced.
They are therefore validated by two implementations that share no author,
which is true of nothing else in this repository.

### Reproduction runs

Independent operator, our implementation. None recorded yet.

| date | who | OS / runtime | result |
|---|---|---|---|
| — | — | — | — |

A row goes in this table only when someone outside the project ran it and is
willing to be named. A run reported anonymously is still welcome and still
gets acted on; it just cannot be cited, so it belongs in the issue tracker
rather than here.

## Two different things, and only one of them is the point

**Running our code on your machine** proves the corpus and the harness are
portable and reproducible - that a stranger can clone the repository and get
the documented result on a different OS. That is worth something, and worth
recording, but it exercises no implementation but ours. `run.py` with no
`--impl`, or with the bundled `example_adapter.py` or the bundled TypeScript
adapter, is this and only this. The runner now says so on the way past.

**Running your own implementation** is the thing this corpus exists for, and
the thing the project has never had. It is what the table above records.

The distinction is easy to blur and expensive to get wrong. A reproduction
run described as an independent verification would be a claim whose trust
anchor is supplied by the party being checked, which is the exact defect
class this repository's review history is a record of catching.

### Reproduction runs

Independent operator, our implementation. None recorded yet.

| date | who | OS / runtime | result |
|---|---|---|---|
| — | — | — | — |

## What a run report should contain

Enough that a reader can repeat it and get the same answer:

- **What you ran** — your implementation, its version or commit, and the
  SATROOT commit you tested against (`git rev-parse HEAD`).
- **Your environment** — OS, and the language runtime version.
- **The result** — how many of the 33 matched, and the full text of any that
  did not.
- **What you could not check**, said plainly. A partial run is worth
  reporting; a partial run described as a complete one is not.

`python3 run.py --impl "<your command>" --emit > mine.txt` produces exactly
the artifact to attach, and `diff mine.txt EXPECTED.txt` produces exactly the
discrepancy list.

## Where to send it

- **A mismatch, or anything you think is a defect** →
  https://github.com/parthod0x/satroot/issues. Please open one even if you
  suspect the fault is yours; a vector that is easy to misread is a defect in
  the corpus regardless of who misread it.
- **A clean run you are willing to be named for** → open an issue, or a pull
  request adding your row to the table above. Either is fine.
- **Privately** → parthms.id@gmail.com.

## A note on what this page is for

The absence of any independent run is this project's most substantive
weakness, and it has been named in every review round it has been through.
A run that found nothing is genuinely useful here. A run that found something
is more useful still, and will be recorded as found rather than quietly
fixed — the repository's history already contains its own retractions, and
this page follows the same rule.
