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
- **The publication ladder** (bundles, releases, catalogs, registries),
  which this pass did not attack — it focused on the kernel.
