# SATROOT-1 conformance vectors

A deterministic corpus of 31 vectors (12 that must replay, 19 that
must be rejected) for testing any SATROOT-1 implementation against the
reference. Every kernel action - transfer, mint, burn, freeze, and
rotate-authority - is exercised, across all three signature schemes.
Each `*.json` file is one vector:

```json
{
  "vector_format": "satroot1-conformance/1",
  "name": "...",
  "description": "...",
  "scheme": "demo | hmac-sha256 | ed25519",
  "events": [ ...the ledger to replay, exactly as stored... ],
  "expect": {
    "ok": true,
    "final_state_hash": "sha256:...",
    "balances": { "account": "digit-string", ... },
    "record_count": N
  }
}
```

Rejection vectors carry `"expect": {"ok": false, ...}` — a conforming
implementation must refuse to replay them. `reference_error` records the
reference implementation's message for orientation only; implementations
are not required to reproduce error text, only the accept/reject
decision. For accepted vectors, `final_state_hash`, `balances`, and
`record_count` must match exactly.

## Fixed verification material

Vectors are signed with fixed keys so the corpus is reproducible:

- ed25519 private keys (hex): `issuer-key` = `11`×32, `alice-key` = `22`×32
  (derive the public keys; RFC 8032 signing is deterministic)
- hmac-sha256 shared secrets (hex): `issuer-key` = `33`×32, `alice-key` = `44`×32
- `demo` scheme: the reference placeholder scheme, defined in `SPEC.md`

The corpus uses placeholder roots only, per the repository's anchoring
policy (`ANCHORS.md`).

## Running

Against the reference implementation:

```bash
python scripts/run_conformance_vectors.py
```

Regenerating (maintainers only — output is byte-stable):

```bash
python scripts/generate_conformance_vectors.py
```

A second implementation demonstrates conformance by loading each vector,
replaying `events` under `scheme` with the fixed material above, and
comparing the outcome with `expect`.
