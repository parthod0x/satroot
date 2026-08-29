#!/usr/bin/env python3
"""A worked example of the adapter contract in run.py.

    python3 run.py --impl "python3 example_adapter.py"

This one is backed by the reference implementation, so it proves nothing
about conformance - it exists only to show the shape. Yours does the same
three things in whatever language you like:

    1. read the vector JSON named on argv[1]
    2. replay its `events` under its `scheme`
    3. print ONE line: "REJECT", or
       "ACCEPT <state_hash> <record_count> <account>=<balance> ..."

That is the whole interface. Everything below is reading JSON and calling
a replay function.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import satroot1 as sr

ED25519_PRIVATE = {"issuer-key": "11" * 32, "alice-key": "22" * 32}
HMAC_SECRETS = {"issuer-key": "33" * 32, "alice-key": "44" * 32}


def main():
    vector = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    scheme = vector["scheme"]
    if scheme == "demo":
        verifier = sr.demo_signature_verifier
    elif scheme == "ed25519":
        verifier = sr.make_ed25519_verifier(
            sr.derive_ed25519_public_keys(ED25519_PRIVATE)
        )
    elif scheme == "hmac-sha256":
        verifier = sr.make_hmac_sha256_verifier(HMAC_SECRETS)
    else:
        sys.exit("unknown scheme: %s" % scheme)

    try:
        state = sr.replay(vector["events"], verifier=verifier)
    except sr.SatRootError:
        print("REJECT")
        return

    balances = state.snapshot()["balances"]
    print(
        "ACCEPT %s %d %s"
        % (
            state.state_hash(),
            len(vector["events"]),
            " ".join("%s=%s" % (k, balances[k]) for k in sorted(balances)),
        )
    )


if __name__ == "__main__":
    main()
