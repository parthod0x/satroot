# SATROOT-1 TypeScript verifier

An independent implementation of the SATROOT-1 replay rules, written to
validate the **specification** rather than the Python reference: it
reproduces canonical JSON, event ids, and state hashes byte for byte, and
makes the same accept/reject decision on every vector in `../../vectors`.

Zero third-party dependencies at runtime — Node's built-in `crypto` only.
All three signature schemes are implemented (`demo`, `hmac-sha256`,
`ed25519`).

## Run it

```bash
npm install
npm test
```

Expected output ends with `57 vectors, 0 failures`.

## Running it through the corpus's adapter contract

`npm test` checks the corpus internally. `src/adapter.ts` does the other
thing - one vector per invocation, one line of stdout - so this
implementation goes through exactly the same harness an external
implementer would use:

```bash
npm install && npm run build
cd ../../vectors
python3 run.py --impl "node ../verifiers/typescript/dist/adapter.js"
python3 run.py --impl "node ../verifiers/typescript/dist/adapter.js" --emit > ts.txt
diff ts.txt EXPECTED.txt
```

The build step is required: `dist/` is not checked in.

That this passes is a statement about the *harness*, not about the
verifier - `npm test` already covered the verifier. It demonstrates the
adapter contract works from Node and not only from Python, which is what
an implementer in a third language needs before trusting the interface.
Both implementations here share an author, so neither run is independent.

## What implementing this surfaced

These are the details a second implementer must get exactly right; they
are the reason the corpus exists.

| Detail | Requirement |
|---|---|
| Canonical JSON | Keys sorted at **every** level, separators `,` and `:` with no spaces, non-ASCII emitted raw (Python's `ensure_ascii=False`). `JSON.stringify` escapes strings compatibly, but never sorts keys — you must serialize manually. |
| `event_id` | SHA-256 over canonical JSON of the event **minus** `event_id` and `state_hash`. |
| Signing payload | Same, but also **minus** `signature`. |
| State hash | SHA-256 over the canonical commitment snapshot: balances as decimal strings with **zero balances omitted** and accounts sorted, `frozen_accounts` sorted, `supply` and `max_supply` as strings, `max_supply` null when unset. |
| Amounts | Unsigned ASCII digit strings only — no numbers, no `+`/`-`, no Unicode digits, no leading zeros beyond `"0"` itself. Use arbitrary-precision integers (`BigInt`); balances can exceed 2^53. |
| HMAC secrets | The shared secret is used as the **literal UTF-8 bytes of the hex string**, not the decoded hex bytes. |
| Ed25519 keys | Raw 32-byte public keys in lowercase hex. Node needs them wrapped in an SPKI envelope (`302a300506032b6570032100` + key). Signatures are `ed25519:<128 hex chars>`. |
| `demo` scheme | `signature` is the literal string `"demo"`, and `signature_key_id` must be **absent**. |
| Optional commitments | `event_id` and `state_hash` are optional on a record, but when present they must match — they are checked, never trusted. |

## Layout

- `src/satroot.ts` — the verifier: canonicalization, schemes, replay.
- `src/run-vectors.ts` — corpus runner.
