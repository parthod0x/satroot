# Verifying this export

You need only the open-source SATROOT package:

```
pip install "satroot[crypto,validation]"
python verify_export.py .
```

`verify_export.py` is included here, is Apache-2.0, and imports nothing from
satledger. It is the same code the service runs, not a reimplementation.

## What a plain run proves

The signed events form a valid chain, replaying them yields the state hash
the bundle claims, the action log is a valid hash chain with no reordering or
edits, the two are bound to each other, every file was checked rather than
carried, and every anchor pins a ledger prefix this export reproduces.

## What it does not prove, and how to fix that

**Completeness.** A prefix of a valid signed chain is a valid signed chain,
and satledger holds the signing keys. A plain run reports
`action_log_continuity_checked: false` and
`ledger_completeness_checked: false`, and it means both.

Keep the `head_hash` from `action_log_head.json` each time you export. On the
next export, pass it back:

```
python verify_export.py . --expect-action-head sha256:<the head you kept>
```

That turns "this is a valid chain" into "this is a valid chain that still
contains what I saw last time", which is the only check that detects
action-log deletion. Keep your anchors too: each carries a timestamp whose
signature this verifier checks and whose `genTime` it reports. An operator
can always get a *fresh* timestamp; it cannot get one dated last week.

## Trusting the timestamps

**Do not take the authority's fingerprint from this export.** An earlier
version of this file told you to read `signer_sha256` off a first run and pin
it. If the export were forged, that first run would be the forgery, and you
would pin the forger's own certificate. A reviewer demonstrated exactly that.

The verifier has freetsa.org's fingerprint compiled in, so an honest export
reports `third_party_timestamp_verified: true` with no flags. If an export's
anchors are signed by anyone else, the verifier **fails** rather than passing
with a warning — our tokens carry their signing certificate, so an operator
can mint both, and a signature check alone cannot tell them apart.

To trust a different authority, get its certificate fingerprint **from that
authority** and pass it:

```
python verify_export.py . --trust-tsa-sha256 <fingerprint from the authority>
```

`--allow-untrusted-tsa` accepts internal consistency only, and says so.

See the vendor's `docs/THREAT_MODEL.md` for the full account of what is and
is not guaranteed.
