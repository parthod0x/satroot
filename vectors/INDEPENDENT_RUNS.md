# Independent runs of the SATROOT-1 conformance corpus

A run is *independent* if the person who did it is not the author of this
repository and did not have the author walk them through it.

## Runs recorded so far

**None.**

That is the honest state as of 29 August 2026, and this page exists to stop
it being quietly restated as something else. The corpus has been run by two
implementations — the Python reference and `verifiers/typescript/` — and both
were written by the same person, so they demonstrate that the specification
is implementable from its text and nothing more.

| date | who | implementation | language | result | report |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

A row goes in this table only when someone outside the project ran it and is
willing to be named. A run reported anonymously is still welcome and still
gets acted on; it just cannot be cited, so it belongs in the issue tracker
rather than here.

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
