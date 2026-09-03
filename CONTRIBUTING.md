# Contributing to SATROOT

The most valuable thing you can send this project is **a disagreement**.

Not a feature, not a refactor: a case where your reading of `SPEC.md` and this
implementation's behaviour do not match. Every serious defect found so far came
from exactly that, and none of them were reachable from inside.

## The single most useful thing

Implement the specification and run the conformance corpus against your
implementation:

```bash
python vectors/run.py --impl your_verifier.py
```

68 vectors: 19 that must replay, 49 that must be rejected. If your verifier
disagrees with `EXPECTED.txt` on any of them, **open an issue** — the
[independent implementation](.github/ISSUE_TEMPLATE/independent-implementation.yml)
template is for this.

You do not need to be right for it to be worth reporting. Half the value is in
finding out which of us is wrong, and the specification loses that argument
more often than you would expect.

`vectors/IMPLEMENTER_BRIEF.md` is the standalone brief: what to build, what to
run, what counts as a pass.

## Why this is the ask

Twelve rounds of adversarial review, 1,751 tests and two implementations
missed a defect that made **the root of every ledger forgeable**: the genesis
record was never authenticated, so a forged or absent signature replayed clean
under every scheme.

It was found by one person implementing the spec from scratch, reading only
the document. Seven rounds of that produced twenty-six specification defects
and grew the corpus from 33 vectors to 68.

Every test in this repository is written against the code, which is why none
of them could see it. That is a structural limit, not an oversight, and the
only known way past it is a reader who owes the code nothing.

## What is welcome

- **Conformance disagreements.** Above all else.
- **Spec ambiguities.** A sentence two competent readers implement differently
  is a defect, even where both implementations happen to agree today.
- **New vectors**, especially rejection cases. If you found a way to construct
  something that replays as valid and should not, that is the best possible
  contribution.
- **Documentation fixes.** Typos, broken links, a paragraph that misled you.
- **Security findings.** See `SECURITY.md`. Spec defects count as security
  findings here — the worst one this project has had was not a code bug.

## What to expect from a pull request

**The `SATROOT-1` kernel rules are frozen.** Event shape, replay semantics,
the state commitment and the signature schemes do not change except to fix a
defect, and fixing one is a major version because state hashes move. A PR that
changes kernel behaviour needs to argue that current behaviour is wrong, not
that different behaviour would be nicer.

Outside the kernel — profiles, tooling, docs, tests, the publication ladder —
the bar is ordinary: it should do something the project needs and not break
the release gate.

Before opening a PR:

```bash
python scripts/run_release_gate_smoke.py
```

That is the same gate used before tagging: import smoke, the operator proof,
and the full suite. If it does not pass locally it will not pass here.

Please do not send large refactors unannounced. Open an issue first — not for
ceremony, but because a big diff nobody asked for is expensive to review and
usually gets declined for reasons that could have been stated in a paragraph.

## Practical notes

- **No CLA.** Apache-2.0 in, Apache-2.0 out.
- **One maintainer**, so replies take days rather than hours. Persistence is
  fine; nothing here is being ignored deliberately.
- **Credit** goes in the changelog and release notes unless you would rather
  it did not.
- Shell scripts are pinned to LF in `.gitattributes`. Leave that alone — CRLF
  in a script fails on the server with an error naming bash rather than the
  line endings.

## If you are wondering whether it is worth reporting

It is. The corpus grew by a third because somebody thought a vector looked
wrong and said so.
