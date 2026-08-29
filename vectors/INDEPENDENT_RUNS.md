# Independent runs of the SATROOT-1 conformance corpus

A run is *independent* if the person who did it is not the author of this
repository and did not have the author walk them through it.

## Runs recorded so far

| date | who | implementation | language | result | report |
|---|---|---|---|---|---|
| 2026-08-29 | anonymous, **AI-assisted** | ~540-line replay written from `SPEC.md` alone | Python 3.12 | 33/33 against the corpus as it then stood — **and eleven specification defects** | below |

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
