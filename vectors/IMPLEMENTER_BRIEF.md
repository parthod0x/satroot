# Brief: writing an independent SATROOT-1 implementation

**What is being asked:** write your own program that replays a SATROOT-1
ledger, from the specification alone, and run it against the 57 conformance
vectors in this directory. Report what happens.

**Roughly a day**, more if the specification fights you. Any language.

---

## 1. Why this is worth your time, stated honestly

SATROOT has two implementations — Python and TypeScript — 1,751 tests, and a
57-vector conformance corpus. All of it was written by one person. So the
corpus demonstrates that the specification is implementable *by its author*,
which is not the interesting claim.

**A run that fails is a better outcome than one that passes.** Every place
the specification is ambiguous, incomplete or wrong is a real defect, and
you are the only instrument that can detect it — the tests cannot, because
they were written against the code, and the vectors cannot, because they are
generated from it.

This is not hypothetical. One implementation has been written from this
specification, on 29 August 2026. It scored 33/33 against the corpus as it then
stood, and found **eleven defects**, two of which would have stopped a careful reader outright:

- §5 listed `rules_hash` and `nonce` as *required* genesis fields. Nothing
  has ever carried either. An implementation enforcing §5 literally rejects
  every valid ledger at its first event, and a second attempt that day was
  blocked on exactly this.
- The reference **accepted** the amount `"0400"` while the corpus asserted
  it must be rejected and the specification said nothing. Two
  implementations disagreeing about an accept/reject decision — which is
  the entire thing this corpus exists to detect, and it had been invisible.

All eleven are fixed or recorded in `INDEPENDENT_RUNS.md`, and the corpus
grew from 33 vectors to 57 across two rounds, closing the gaps that run exposed. **Assume more
remain.** The last run found eleven; the corpus was thought to be in good
shape before it.

---

## 2. The one rule that makes this worth anything

**Do not read these three files:**

- `src/satroot1.py`
- `verifiers/typescript/src/satroot.ts`
- `scripts/generate_conformance_vectors.py`

If you read them you will produce a port, it will agree with the reference,
and it will prove nothing. The value here is entirely in whether `SPEC.md`
is sufficient on its own.

**If the specification is unclear, that is the finding — report it, don't go
looking in the code.** You will not be wasting anyone's time; that report is
worth as much as the run.

Everything else is fair game: `SPEC.md`, `vectors/README.md`, this file, the
vector JSON files, `example_adapter.py` and
`../verifiers/typescript/src/adapter.ts` (both are input/output plumbing with
no protocol logic in them).

---

## 3. Setup

```bash
git clone https://github.com/parthod0x/satroot.git
cd satroot/vectors
python3 run.py            # expect: 57 vectors, 0 failures
git rev-parse --short HEAD
```

That confirms the corpus and harness work on your machine before your code
is involved. Python 3.8+, no dependencies, nothing to install.

Then read **`SPEC.md`** (all of it — it is 400 lines) and **§"Fixed
verification material"** in `vectors/README.md`, which has the ed25519
private keys and HMAC secrets the corpus is signed with.

---

## 4. The interface your program must satisfy

Invoked once per vector, with the vector's path as its single argument:

```
your-program /path/to/valid-mint-demo.json
```

Print **one line** to stdout:

```
ACCEPT <state_hash> <event_count> <account>=<balance> <account>=<balance> ...
REJECT
```

Accounts in any order. Exit status ignored. stderr is free for debugging.

In Python that wrapper is:

```python
import json, sys

vector = json.load(open(sys.argv[1], encoding="utf-8"))

try:
    state = replay(vector["events"], vector["scheme"])   # your work
except ProtocolRejection:
    print("REJECT")
else:
    terms = " ".join(f"{a}={b}" for a, b in sorted(state.balances.items()) if b != 0)
    print(f"ACCEPT {state.state_hash} {len(vector['events'])} {terms}".rstrip())
```

### The trap worth avoiding on day one

**Only a genuine protocol rejection may print `REJECT`.** If you catch broad
`Exception` and print `REJECT`, then a crash — a missing key, a bad cast —
becomes a *passing* rejection vector. You will score well while your code is
broken, and the harness cannot tell the difference. Use a dedicated
exception type for protocol rejections from the start.

---

## 5. Running it

```bash
cd satroot/vectors
python3 run.py --impl "python3 ~/my-satroot/verify.py"
```

Substitute however your program is launched — `"node ~/my/verify.js"`,
`"~/my/target/release/verify"`, `"java -jar ~/my/verify.jar"`. The runner
appends the vector path as one extra argument.

For the discrepancy list:

```bash
python3 run.py --impl "<your command>" --emit > mine.txt
diff mine.txt EXPECTED.txt
```

---

## 6. Start with a stub

Before any protocol code, write a program that ignores the vector and always
prints `REJECT`:

```python
import json, sys
vector = json.load(open(sys.argv[1], encoding="utf-8"))
print("REJECT")
```

Run it. You should see **42 ok, 15 FAIL** — the 42 rejection vectors pass,
the 15 acceptance vectors fail. That is the correct starting score and it
means your plumbing works.

Those 42 will not all stay passing. Some are decided by rules you have not
written yet, and a few may flip to FAIL as you go before flipping back. The
number to watch is the acceptance count.

If you instead see `printed nothing to stdout`, it is a path or quoting
problem, not a protocol one.

---

## 7. What to build, and in what order

| build | read | passing |
|---|---|---|
| stub above | — | **42** |
| canonical JSON, `event_id`, genesis, `demo` verifier, state hash | §2.6, §2.7, §5, §5.1, §6.6, §7 | 45 |
| transfer | §6.2, §6.1a | 48 |
| mint | §6.1 | 50 |
| burn | §6.3 | 51 |
| freeze / unfreeze | §6.5 | 53 |
| rotate-authority | §6.4 | 55 |
| `hmac-sha256` verifier | §6.6.1 | 56 |
| `ed25519` verifier | §6.6.1 | **57** |

Cross-check the rejection conditions in §8 throughout.

**42 → 45 is by far the hardest step.** It means your canonical JSON, event
ids and state commitment are all byte-exact. Everything after it is one
action at a time.

`valid-genesis-only-demo.json` is a single genesis event, so it isolates the
serialiser: if it fails, the runner's `expected:` / `got:` lines tell you
whether your hash is wrong (hash differs) or your replay is (balances or
count differ).

51 of the 57 vectors use the `demo` scheme, so real cryptography can wait
until the very end.

---

## 8. Reporting

**https://github.com/parthod0x/satroot/issues/new/choose** → *Independent
implementation run* → fill the form.

It asks for your implementation and language, the result, your OS and
runtime, the SATROOT commit you tested against, anything you could not
check, and — the field that matters most — **where the specification was
ambiguous, wrong, or hard to implement**.

Please fill that last box generously, including for things you worked out in
the end. Every place you had to guess, or had to re-read a section three
times, is a defect in the document regardless of whether your guess was
right.

Tick the attribution box only if you are willing to be named in
`INDEPENDENT_RUNS.md`. Anonymous reports are equally welcome and equally
acted on; they just cannot be cited.

If you get stuck on something `SPEC.md` does not answer, report it and stop
— the specification gets fixed and you continue. That is a successful
outcome, not a failed one.
