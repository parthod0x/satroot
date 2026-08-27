# Cross-implementation check: pycose

Every "two implementations agree" claim in this repository has one weakness
that no amount of testing fixes: both implementations have the same author.
The TypeScript verifier shows the SPEC is implementable from its text; it is
not independent validation, and `COMPARISON.md` says so.

This is the first check against software written by someone else.

**Run on 2026-08-26 with pycose 1.1.0 and cbor2 5.9.0.**

## Result

| statement | first byte | pycose decode | signature |
|---|---|---|---|
| `alg = -8` (RFC 9053 polymorphic EdDSA) | `0xd2` | OK, 558-byte payload | **verified** |
| `alg = -19` (RFC 9864 Ed25519) | `0xd2` | `CoseException: Unknown COSE attribute with value: [CoseAlgorithm - -19]` | not reached |

pycose verified a signature produced by `satroot_cose`. That is the claim
"signatures are over the raw `Sig_structure`, so they interoperate with other
COSE implementations" tested rather than asserted — **with one clause the
result does not carry on its own: the verified path is not the default one.**
`satroot_cose` emits `-19` by default and pycose rejects it, so in its shipped
configuration the output does not interoperate with the only independent
library tested. Both are true; neither should be read without the other: the `Sig_structure`
construction (RFC 9052 s4.4), the protected-header encoding, the deterministic
CBOR and the `#6.18` tag are all confirmed by software that has never seen this
repository.

## Two findings worth reporting

**1. RFC 9864's fully-specified identifiers are ahead of deployed tooling.**
RFC 9864 (October 2025) registers Ed25519 as `-19` and marks the polymorphic
`-8` Deprecated, because `-8` alone does not say which curve is in use.
pycose 1.1.0 does not know `-19` and rejects the statement before reaching the
signature.

`satroot_cose` therefore emits `-19` by default, because that is what the RFC
says, and accepts `alg=ALG_EDDSA_DEPRECATED` for interoperability with
deployed libraries. Both are verified by `verify_statement`. Anyone
implementing a SCITT profile with EdDSA today has to make the same choice, and
should know the answer costs them either conformance or compatibility.

**2. pycose 1.1.0 cannot decode its own output under cbor2 6.x.**

Found while establishing a control. cbor2 6.x decodes a tag's array value as a
`tuple`; `CoseMessage.decode` tests `isinstance(cose_obj, list)` and raises
`TypeError: Bytes cannot be decoded as COSE message`. The control is the part
that matters methodologically: the first run of this check failed, and without
asking whether pycose could round-trip its own message it would have looked
like a defect in SATROOT's encoding. It was not.

Reproduce:

```
pip install pycose "cbor2<6"     # 6.x breaks pycose 1.1.0
PYTHONPATH=src python scripts/check_cose_interop.py
```

The script runs the control first, for the reason above.

## What this does not establish

- One library, one language. pycose is not the COSE ecosystem.
- The `-19` path is **unverified against any independent implementation**,
  because none tested here supports it.
- pycose validated the signature, not SCITT semantics. No Transparency
  Service, no Receipt, no inclusion proof is involved.
- `cbor2<6` is pinned to work around a pycose bug, so this is a check against
  one specific version pair, recorded above.
