# SATROOT-1 adversarial review

Record of internal adversarial passes over the frozen kernel. Each pass
lists what was attacked, what held, and what was fixed. Findings are
fixed and pinned by tests before the pass is recorded here.

This is self-review by the author, not an independent audit. An external
review of the canonicalization, signature, and replay surfaces is a
funded milestone on the roadmap; until it happens, treat this document as
evidence of diligence, not as third-party assurance.

## Pass 1 — 2026-08-22

Surfaces attacked: amount and numeric parsing, canonical serialization,
signature verification, scheme negotiation, hash-chain integrity, and the
documented signer-key-binding boundary.

### Finding 1 — amounts were host-dependent (fixed)

**Severity: high for a protocol whose central promise is deterministic
replay.**

`parse_amount` validated `^[0-9]+$` and then delegated to `int()`.
CPython limits integer-from-string conversion (default 4300 digits,
configurable at runtime, floor 640). Two consequences:

1. A digit string longer than the limit raised a bare `ValueError`
   instead of `SatRootError`, so a hostile ledger crashed a verifier
   rather than being cleanly rejected. Downstream this surfaces as a
   500 rather than a validation error.
2. Worse, the accept/reject decision depended on **interpreter
   configuration**. The same ledger could replay on one host and fail on
   another, and implementations with unbounded integers (JavaScript
   `BigInt`, for example) accepted values the reference rejected. That
   contradicts the deterministic-replay guarantee the protocol exists to
   provide.

The JSON schema did not bound these fields either — the pattern was a
bare `^[0-9]+$` with no `maxLength` — so the gap was in the
specification, not only the engine.

**Fix.** Amounts now carry an explicit protocol bound of **512 digits**
(`MAX_AMOUNT_DIGITS`), enforced identically in the engine, the JSON
schema, and the TypeScript verifier, and specified in `SPEC.md` §6.1a.
512 sits below CPython's configurable floor of 640, so `int()` can never
raise on a value the protocol accepts, on any host. The ceiling is far
beyond any realistic supply. Two conformance vectors
(`reject-amount-exceeds-digit-bound`,
`reject-genesis-balance-exceeds-digit-bound`) and two regression tests
pin it, and both implementations must agree.

### Finding 2 — the key-binding boundary is narrower than stated (documented)

> **Withdrawn 2026-11-01 (see Pass 3).** This finding was wrong. It assumed
> an attacker re-signs one record and leaves the rest alone. An attacker who
> holds any registered key re-signs every record, and the chain is then
> intact. The boundary was a high-severity defect, fixed in 3.0.0 by binding
> keys to accounts. The text below is kept as written.

**Severity: none — a documentation precision issue, not a defect.**

`BOUNDARIES.md` stated that any registered key can sign as any account.
True of a single record, but incomplete for a stored ledger: every event
is bound into its successor's `prev_event_id`, so re-signing an interior
event under a different key breaks the chain and is rejected. Only the
**final** event, which has no successor, is actually exposed.

`BOUNDARIES.md` now says this precisely, and
`test_key_substitution_is_chain_blocked_except_at_the_tip` pins both
halves — interior substitution rejected, tip substitution accepted — so
the boundary cannot drift silently.

### What held

Every other attack attempted was correctly rejected:

| Attack | Result |
|---|---|
| Signature lifted from one event and pasted onto another | rejected — payload differs |
| Ed25519 ledger downgraded to the `demo` scheme (metadata stripped) | rejected under both the real and the test-only verifier |
| Forged stated `event_id` | rejected — recomputed and compared |
| Forged stated `state_hash` | rejected — recomputed and compared |
| Duplicate JSON keys smuggling a second `amount` | rejected |
| `signer` field swapped to another account | rejected |
| Interior event re-signed under a different registered key | rejected by the chain |
| Unicode digits, leading zeros, negative, zero, empty amounts | rejected |
| Boolean smuggled where an integer is required (`sequence`, `decimals`) | rejected |
| Sequence gaps, reordering, duplicate events, second genesis | rejected |

### Notes for a future external reviewer

Highest-value places to look next, in the author's judgement:

- **Unicode in account names and symbols.** Canonical JSON does not
  normalize; visually identical names in different normal forms are
  distinct accounts with distinct hashes. Deterministic and consistent
  across implementations, but a plausible source of confusion attacks at
  the application layer.
- **Key sorting above the BMP.** Python sorts dictionary keys by code
  point; JavaScript's default sort compares UTF-16 code units. These
  diverge for keys containing astral-plane characters. No protocol field
  currently permits them, so this is latent rather than live.
  *(Wrong, corrected in Pass 3: account names are keys of `initial_balances`
  and may be astral, so the two implementations hashed real ledgers
  differently.)*
- **The publication ladder** (bundles, releases, catalogs, registries),
  which this pass did not attack — it focused on the kernel.

## Pass 3 — 2026-11-01 (external review)

An outside reviewer, reading the code cold, wrote 24 hostile inputs in an
afternoon and reproduced the top findings in both implementations. Every
finding below was reproduced again here before it was fixed, and every fix
is a conformance vector that both implementations now agree on.

### Finding 5 — any registered key could sign as any account (fixed, 3.0.0)

**Severity: high.** The verifier selected a key by `signature_key_id` and
checked only that `signer` named the right account, so a holder of any
registered key could transfer the issuer's balance, mint as the issuer,
rotate the authority, or sign a genesis. Finding 2 called this a tip-only
exposure; re-signing every record defeats that argument, and a reviewer's
script re-signed a whole ledger with one key and replayed it clean.

Fixed by ledger version `0.2` (SPEC sections 5 and 6.7): genesis declares
`account_keys`, every record must be signed with its signer's bound key,
`bind-key` changes a binding (by the authority for an unbound account, by
the account itself otherwise), and the bindings are committed in the state
hash. A whole-ledger rewrite from a forger's own genesis remains valid, as a
different ledger; the defence is pinning the genesis `event_id`, which
`replay` and `verify-bundle` now accept and report.

### Finding 6 — the two implementations disagreed outside the corpus (fixed)

**Severity: high.** Of 23 hostile vectors, 18 split Python from TypeScript:
astral account names and frozen-account order (UTF-16 versus code-point
sort), `__proto__` members, floats, integers past 2^53, NaN, lone
surrogates, an explicit `null` scheme, uppercase or leading-zero `root_id`,
control-character and byte-order-mark account names (`strip` versus `trim`),
signature hex with trailing junk or spaces, and several inputs that crashed
Python instead of rejecting. Fixed by an input profile both implementations
enforce on the text and the values (SPEC section 2.6a), one name rule, exact
encodings, code-point sorting and prototype-free objects in TypeScript, and
a guarantee that malformed input is a rejection, never a crash. All of them
are in the corpus, with six more for the per-profile rules the TypeScript
verifier skipped (115 vectors in all, with Findings 10 and 11), and both implementations agree on every one.

### Finding 7 — anyone could change a ledger's hash without a key (fixed)

**Severity: medium.** Both implementations decoded signature hex leniently,
so upper-casing a valid signature changed the record's `event_id` and every
state hash after it while still verifying. Signatures and keys now have one
accepted spelling each.

### Finding 8 — `verify-bundle` trusted the bundle's own keys (fixed)

**Severity: medium.** The bundle manifest and its key file are unsigned, and
`verify-bundle` read its keys from them. It now takes `--public-keys-json`
(or `--secrets-json`) and `--expect-genesis`, and reports `keys_pinned` and
`genesis_pinned` so a result never implies a check it did not make.

### Finding 9 — pinned keys were dropped for a bundle claiming hmac (fixed)

**Severity: high.** Found by a second, cold review of the 3.0.0 fixes. The
manifest is unsigned, and `verify_signed_ledger_bundle` chose its verifier
from the manifest's `scheme`. A forged bundle claiming `hmac-sha256` was
checked with its own secret, and the ed25519 keys the caller had pinned were
ignored: a genesis re-signed to credit the issuer 999,999 passed with
`--public-keys-json`. Pinned key material now decides the scheme, and a
bundle claiming any other is refused.

### Finding 10 — the authority could take funds from unbound accounts (fixed)

**Severity: medium.** `bind-key` lets the authority bind an account with no
key, and genesis or a transfer could credit such an account, so the
authority could bind it to its own key and empty it. Both implementations
accepted that with the same hash. In a bound ledger, value now sits only in
bound accounts (SPEC section 6.7 rule 5).

### Finding 11 — deep nesting split the implementations (fixed)

**Severity: medium.** A deeply nested metadata value was rejected by Python
(or crashed it) and accepted by TypeScript. The input profile now limits
nesting to 64 levels in both.

### Also fixed

- The JSON schema required `rules_hash`, which SPEC section 5 makes
  optional, so it rejected every valid ledger in the corpus.
- The conformance scripts imported the installed package rather than `src/`,
  so the corpus was being generated and checked by a stale engine.
- `mint_authority`, `symbol`, `name`, `initial_balances` and `profile` were
  used before their types were checked.

The lesson is the one Pass 2 recorded and this pass repeats: a corpus of
honest ledgers proves agreement on honest ledgers. Determinism needs the
inputs an adversary would choose.
