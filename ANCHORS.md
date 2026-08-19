# SATROOT anchored-run record

This file is the only place in the repository where a real on-chain outpoint is
recorded, and it records history, never input: every checked-in example, preset,
and default stays on placeholder roots, and the anchored demo lane accepts a real
outpoint exclusively through its `--root-id` flag at run time.

## v0.5-root-anchoring — first real anchor

- Date: 2026-08-19
- Network: BSV testnet
- Root outpoint (`root_id`): `147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0`
- Root satoshi holder address: `n2xDA14uhX4Ym6tcXHEFZwstiDhi2YzA3e` (operator-controlled)
- Explorer: https://test.whatsonchain.com/tx/147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63
- Lane: `satroot_anchored_demo_smoke` (profile `SATROOT-IDENTITY-1`, bundle scheme `ed25519`)
- Semantic state hash of the anchored namespace:
  `sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3`
- Lane report checks, all passing: `root_id_bound_to_state`,
  `ed25519_bundle_verified`, `replay_deterministic`, `foreign_root_rejected`,
  `no_custody_event_kinds`.

Reproduce the verification at any time with:

```bash
python scripts/run_anchored_demo_smoke.py --root-id 147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0
```

The run is deterministic in structure but generates fresh ed25519 keys each
time, so signatures differ between runs while every check and the bound
`root_id` stay identical.

## v0.6-anchored-publication — anchored namespace published

- Date: 2026-08-19
- Root outpoint (`root_id`): `147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0` (same anchor as v0.5)
- Lane: `satroot_anchored_publication_smoke` (profile `SATROOT-IDENTITY-1`, ed25519 end to end)
- The anchored namespace was published through the full ladder — signed bundles, release, catalog, network, and registry workspace — with the real root bound in every generated bundle genesis and the registry workspace lint-clean.
- Published-artifact hashes:
  - `publication_registry_manifest`: `sha256:c039fc97e8f37c9cb12ae5a01658d149694fcaa76fa98d4d5aa0ae6b45bd46cf`
  - `publication_metadata_catalog_manifest`: `sha256:1455edaaea656eead88ad5441736c51d2e4ec1d20a744f3bcca578a79a8cf841`

Reproduce structure verification at any time with:

```bash
python scripts/run_anchored_publication_smoke.py --root-id 147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0
```

Each run generates fresh ed25519 keys, so signatures and therefore the manifest
hashes differ between runs; the hashes above identify the specific published
artifacts from the recorded run, while the checks and the bound `root_id` stay
identical on every rerun.

## v0.7-onchain-envelope — state commitment broadcast

- Date: 2026-08-19
- Root outpoint (`root_id`): `147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0` (same anchor as v0.5)
- Envelope transaction id: `6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0`
- Explorer: https://test.whatsonchain.com/tx/6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0
- Lane: `satroot_onchain_envelope_smoke` (SPEC section 4, content type `application/satroot1+json`)
- The envelope rides in output 0 as a zero-value `OP_FALSE OP_RETURN` data output carrying the `SATROOT1` tag, the content type, and the canonical JSON commitment of the anchored namespace's `root_id` and semantic state hash `sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3`.
- The broadcast spent only the operator's change output; the 1-satoshi anchor at the recorded outpoint was not an input and remains unspent.

Rebuild the exact envelope script at any time with:

```bash
python scripts/run_onchain_envelope_smoke.py \
  --root-id 147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0 \
  --state-hash sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3
```

The builder is fully deterministic, so the produced `envelope_script.hex` is
byte-identical to the script carried in the broadcast transaction's output 0.

## v0.8-envelope-verification — broadcast envelope verified offline

- Date: 2026-08-19
- Envelope transaction id: `6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0` (same envelope as v0.7)
- Lane: `satroot_envelope_verification_smoke`
- The operator fetched the raw transaction bytes out-of-band; the offline verifier parsed them, confirmed they hash to the recorded transaction id, located the single zero-value `SATROOT1` envelope output, and matched it byte for byte against the deterministically rebuilt commitment for the anchored namespace's `root_id` and state hash. Every check passed.

Reproduce at any time by saving the raw transaction hex to a file and running:

```bash
python scripts/run_envelope_verification_smoke.py \
  --raw-tx-hex-file <path-to-raw-tx-hex> \
  --root-id 147bbb9ee7ef860f2f70acfe5a9197011a66af81234d0b6aefffae4702d24b63:0 \
  --state-hash sha256:e1a2c685d3a3cf84a0ec81ad400ac1c66ecb9e9679338cbd13c4644e849fb4e3 \
  --expected-txid 6051ed98964b0b8e609fff3e6d38358de55c618d4a95bad696ef2ff5f86e47c0
```

## Root lifecycle statement

The recorded outpoint is a one-satoshi UTXO whose custody remains with the
operator's testnet wallet. Nothing in this repository can move it, and moving it
on-chain would not alter the semantic state hash above: SATROOT state changes
only through valid protocol events, and no ledger event kind models root
custody. That separation is exactly what the anchored lane's report proves.
