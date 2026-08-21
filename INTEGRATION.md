# SATROOT-1 Integrator's Guide

Practical guidance for building an application on the `satroot` package,
distilled from building a real multi-agent credit-ledger service on the
published wheel. `SPEC.md` defines the rules; this document tells you
which functions to call, in what order, and which mistakes the kernel
will catch you on.

Everything below uses only the public API of the installed package:

```bash
pip install "satroot[crypto,validation]"
```

- `[crypto]` enables the `ed25519` scheme (`ed25519_available()` reports it).
- `[validation]` enables JSON-schema checks; **bundle verification
  (`verify_signed_ledger_bundle`) requires it** — without it you get a
  `SatRootError` telling you to install the extra.

```python
import satroot1 as sr
```

## 1. Provisioning a ledger

### Genesis

Scaffold, validate, then sign. Use the profile-field default constants
rather than hardcoding profile field names:

```python
fields = dict(sr.MACHINE_DEMO_CATALOG_FIELD_DEFAULTS)   # then override as needed
genesis = sr.scaffold_genesis_record(
    symbol="CRBOT1",                      # ^[A-Z0-9]{1,16}$ — no hyphens/underscores
    name="Bot One credits",
    root_id=sr.build_scaffold_root_id(),  # placeholder root; a real outpoint only
                                          # for intentional anchored runs (ANCHORS.md)
    mint_authority="issuer",
    decimals=0,
    initial_balance="1000",               # amounts are ASCII-digit strings
    profile=sr.MACHINE_DEMO_CATALOG_PROFILE,
    profile_fields=fields,
)
sr.validate_profile_genesis(genesis)
```

Pitfalls the kernel enforces here:

- **Symbols** match `^[A-Z0-9]{1,16}$`. `CR-BOT-1` fails schema
  validation later even if replay accepts it — validate early.
- **Amounts, balances, decimals-as-strings**: every quantity in the
  protocol is a canonical ASCII-digit string, never a JSON number.
  Compare `balances["issuer"] == "1000"`, not `== 1000`.

### Keys and signing the genesis

Generate keys per namespace and keep the signer→key-id map with them.
The reference convention is `<signer>-key`:

```python
key_ids = ["issuer-key", "bot-1-key"]
private_keys = sr.generate_ed25519_private_keys(key_ids)   # bare 64-hex values
public_keys = sr.derive_ed25519_public_keys(private_keys)
signer_key_ids = {"issuer": "issuer-key", "bot-1": "bot-1-key"}

signer = sr.make_ed25519_signer(private_keys)
verifier = sr.make_ed25519_verifier(public_keys)
```

**The genesis is signed directly** — `append_signed_event_to_ledger`
refuses an empty ledger by design, so the first record goes through
`sign_event_record`:

```python
signed_genesis = sr.sign_event_record(
    genesis, scheme="ed25519", key_id="issuer-key", signer=signer,
)
events = [signed_genesis]
sr.replay(events, verifier=verifier)   # cheap sanity check before persisting
```

## 2. Appending events

Every subsequent event: scaffold from the current ledger (so sequence
and `prev_event_id` are derived, not hand-built), then append through
the signing helper:

```python
event = sr.scaffold_event_from_ledger(
    events, action="transfer", signer="issuer",
    from_account="issuer", to_account="bot-1", amount="400",
    verifier=verifier,
)
events = sr.append_signed_event_to_ledger(
    events, event, scheme="ed25519",
    signer_key_ids=signer_key_ids, signer=signer, verifier=verifier,
)
```

Profile-specific scaffolds exist where semantics matter — e.g.
`scaffold_machine_credit_consumption_event(...)` for machine-credit
burns, and the `scaffold_singleton_object_*` family for
transfer/archive/retire on singleton-object profiles.

`append_signed_event_to_ledger` replays before returning: an event the
kernel rejects (overspend, bad sequence, wrong signer) raises
`SatRootError` and **returns without mutating your list** — persist the
returned list, not the input.

## 3. Reading state

```python
state = sr.replay(events, verifier=verifier)
snapshot = state.snapshot()        # balances (strings!), profile, metadata
state_hash = state.state_hash()    # "sha256:..." — the anchorable commitment
```

`replay` is the only source of truth. Do not maintain balances beside
the ledger; recompute.

## 4. Exporting verifiable bundles

A signed-ledger bundle directory is what you hand to someone who does
not trust you. If you manage your own persistent keys (an application
almost always does), build the bundle mapping yourself and let the
package build the manifest:

```python
state = sr.replay(events, verifier=verifier)
bundle = {
    "scheme": "ed25519",
    "material": {"public_keys": public_keys, "signer_key_map": signer_key_ids},
    "signed_events": events,
    "annotated_events": sr.annotate_ledger_events(events, verifier=verifier),
    "final_state_hash": state.state_hash(),
    "final_state_snapshot": state.snapshot(),
}
output_files = {
    "signer_key_map": "signer_key_map.json",
    "signed_events": "signed_events.json",
    "public_keys": "public_keys.json",                       # public-only scope
    "annotated_signed_events": "annotated_signed_events.json",
    "bundle_manifest": "bundle_manifest.json",
}
```

**The file-hash contract:** manifest hashes are computed over the
*rendered* JSON. Use `sr.rendered_json_sha256(payload)` for the hashes
and write each file byte-identically to that rendering —
`json.dumps(data, indent=2, ensure_ascii=False) + "\n"`, UTF-8, `\n`
newlines. Any other formatting makes verification fail with a file-hash
mismatch.

```python
payload_hashes = {k: sr.rendered_json_sha256(v) for k, v in payloads.items()}
manifest = sr.build_signed_ledger_bundle_manifest(
    bundle, output_files=output_files, output_file_hashes=payload_hashes,
)
```

Omitting `private_keys.json` from the files yields
`verification_material_scope: "public-only"` in the manifest — ship
that to customers. The consumer side is one call:

```python
sr.verify_signed_ledger_bundle("path/to/bundle")   # needs [validation]
```

It re-hashes every file, re-replays every event under the shipped
public keys, and cross-checks the manifest — raising `SatRootError` on
any byte out of place.

## 5. On-chain anchoring commitments

The envelope builder is deterministic and offline:

```python
from satroot_onchain_envelope_smoke import (
    CONTENT_TYPE, build_envelope_payload, build_envelope_script,
    parse_envelope_script,
)
payload = build_envelope_payload(root_id, state.state_hash())
script = build_envelope_script(CONTENT_TYPE, payload)      # OP_FALSE OP_RETURN ...
decoded = parse_envelope_script(script)                    # {"protocol_tag", "content_type", "payload"}
assert decoded["payload"]["state_hash"] == state.state_hash()
```

Note the parse result nests the commitment under `"payload"`. Attach
the script as a zero-value output of a funded transaction with any
wallet (broadcasting is out-of-band by design), then anyone verifies
from raw bytes:

```bash
python -m satroot_envelope_verification_smoke \
  --raw-tx-hex-file rawtx.hex --root-id <root> \
  --state-hash <hash> --expected-txid <txid>
```

## 6. Quick pitfall index

| Pitfall | Symptom | Fix |
|---|---|---|
| Signing genesis via `append_signed_event_to_ledger` | `SatRootError: empty ledger` | `sign_event_record` for the first record |
| Hyphens/lowercase in symbol | schema validation failure at export/verify | `^[A-Z0-9]{1,16}$` |
| Comparing balances to ints | assertions fail | balances are canonical digit strings |
| Custom JSON formatting in bundle files | file-hash mismatch on verify | `indent=2, ensure_ascii=False`, trailing `\n` |
| Missing `[validation]` extra | `SatRootError: jsonschema package is required` | install `satroot[validation]` |
| Reading `parse_envelope_script(...)["root_id"]` | `KeyError` | commitment fields live under `["payload"]` |
| Real outpoints in tests or fixtures | policy violation | placeholder roots via `build_scaffold_root_id()`; real outpoints only in `ANCHORS.md`-recorded runs |
