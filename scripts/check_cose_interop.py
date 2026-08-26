"""Verify a SATROOT Signed Statement with pycose, an independent COSE library.

Every "two implementations agree" claim in this repository shares one author.
This script is the check against software written by someone else: it signs a
statement with `satroot_cose` and asks pycose to verify it.

    pip install pycose "cbor2<6"
    PYTHONPATH=src python scripts/check_cose_interop.py

The `cbor2<6` pin is not incidental. pycose 1.1.0 cannot decode its own output
under cbor2 6.x, because 6.x returns a tuple for a tag's array value and
`CoseMessage.decode` tests `isinstance(cose_obj, list)`. The control below runs
first for exactly that reason: without it, a pycose failure looks like a defect
in SATROOT's encoding when it is not.

Measured results are recorded in docs/COSE_INTEROP.md.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from pycose.keys import OKPKey
        from pycose.keys.curves import Ed25519
        from pycose.messages import Sign1Message
    except ImportError:
        print('pycose is not installed. Run: pip install pycose "cbor2<6"')
        return 2

    import satroot1 as sr
    import satroot_cose as sc

    if not sr.ed25519_available():
        print("ed25519 unavailable; install satroot[crypto]")
        return 2

    # --- control: can pycose round-trip a message pycose itself produced? ---
    from pycose.algorithms import EdDSA
    from pycose.headers import KID, Algorithm

    control_key = OKPKey.generate_key(crv=Ed25519)
    control = Sign1Message(phdr={Algorithm: EdDSA, KID: b"k"}, payload=b"control")
    control.key = control_key
    control_bytes = control.encode()
    try:
        Sign1Message.decode(control_bytes)
    except Exception as exc:
        print(f"CONTROL FAILED: pycose cannot decode its own output: {exc}")
        print('This is a pycose/cbor2 version problem. Try: pip install "cbor2<6"')
        return 2
    print("control: pycose round-trips its own message  OK")

    # --- the actual check ---
    demo = sr.bootstrap_machine_credit_demo_ledger(symbol="INTEROP", name="interop")
    bundle = sr.bootstrap_signed_ledger_bundle(demo["events"], scheme="ed25519")

    failures = 0
    for alg, label in (
        (sc.ALG_EDDSA_DEPRECATED, "alg  -8  (RFC 9053 polymorphic EdDSA)"),
        (sc.ALG_ED25519, "alg -19  (RFC 9864 Ed25519)"),
    ):
        statement = sc.encode_ledger(
            bundle["signed_events"],
            issuer="https://satroot.com/interop",
            private_keys=bundle["material"]["private_keys"],
            signer_key_ids=bundle["material"]["signer_key_map"],
            alg=alg,
        )[0]
        parsed = sc.parse_statement(statement)
        public = bundle["material"]["public_keys"][parsed["kid"]]

        print(f"\n{label}   first byte 0x{statement[0]:02x}")
        try:
            message = Sign1Message.decode(statement)
        except Exception as exc:
            print(f"   pycose decode : {type(exc).__name__}: {exc}")
            if alg == sc.ALG_ED25519:
                print("   (expected with pycose 1.1.0, which predates RFC 9864)")
            else:
                failures += 1
            continue
        message.key = OKPKey(crv=Ed25519, x=bytes.fromhex(public))
        verified = message.verify_signature()
        print(f"   pycose decode : OK ({len(message.payload)} byte payload)")
        print(f"   signature verified by pycose: {verified}")
        if not verified:
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
