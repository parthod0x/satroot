# SATROOT anchored-run record

This file is the only place in the repository where a real on-chain outpoint or
transaction id is recorded, and it records history, never input: every checked-in
example, preset, and default stays on placeholder roots, and the four anchored
lanes accept real outpoints and transaction ids exclusively through run-time
flags.

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

## v1.6-mainnet-anchor — first real anchor on BSV mainnet

The whole loop, repeated on **mainnet**. Everything above this section ran on
testnet; this section is the production-network record.

- Date: 2026-08-22
- Network: **BSV mainnet**
- Root outpoint (`root_id`): `38ff9da029e66ee9b6a1b175025388caf7fb6d3bb0273812737d7dd6b347c473:0`
- Root satoshi holder address: `1K47C4mQhZwfnnbvCCAFfjfkwwgcGdT2Br` (operator-controlled, fresh wallet)
- Explorer: https://whatsonchain.com/tx/38ff9da029e66ee9b6a1b175025388caf7fb6d3bb0273812737d7dd6b347c473
- Confirmed in block 963415.
- Semantic state hash of the anchored namespace:
  `sha256:34049329f152c388cad547440b32213d48be583c0fa16d93a94582f7399fde58`
- Lanes run against the real outpoint, all passing:
  - `satroot_anchored_demo_smoke` (profile `SATROOT-IDENTITY-1`, ed25519) — checks
    `root_id_bound_to_state`, `ed25519_bundle_verified`, `replay_deterministic`,
    `foreign_root_rejected`, `no_custody_event_kinds`.
  - `satroot_anchored_publication_smoke` — full ladder, lint-clean registry
    workspace, root bound in every generated bundle genesis. Published-artifact
    hashes:
    - `publication_registry_manifest`: `sha256:25e7ea384af6a7f222c90dc979d531b05c37b7a34da73edea67775a9dbecbcc0`
    - `publication_metadata_catalog_manifest`: `sha256:6e63a157d9c777fb9a8e986e9a1c7c22aabe7ca54bae57a643bff139180baca3`
- Envelope transaction id: `7f5946898440a96e18526440ed7140eda85e7dad7e753c7d0b88d09f008b1f83`
- Explorer: https://whatsonchain.com/tx/7f5946898440a96e18526440ed7140eda85e7dad7e753c7d0b88d09f008b1f83
- Envelope output: index 0, zero value, `OP_FALSE OP_RETURN "SATROOT1"
  "application/satroot1+json" <190-byte canonical JSON commitment>`.
- Offline verification of the broadcast bytes: **all seven checks passed** —
  `raw_transaction_parsed`, `txid_matches_expected`, `exactly_one_envelope_output`,
  `envelope_output_value_zero`, `envelope_decodes`, `commitment_matches`, and
  `script_byte_identical_to_rebuild`.

Reproduce the verification from the public chain — fetch the raw transaction hex
from any explorer, save it to a file, then:

```bash
python scripts/run_envelope_verification_smoke.py   --raw-tx-hex-file <path-to-raw-tx-hex>   --root-id 38ff9da029e66ee9b6a1b175025388caf7fb6d3bb0273812737d7dd6b347c473:0   --state-hash sha256:34049329f152c388cad547440b32213d48be583c0fa16d93a94582f7399fde58   --expected-txid 7f5946898440a96e18526440ed7140eda85e7dad7e753c7d0b88d09f008b1f83
```

No network access is required: the verifier works purely from the bytes.

## Root lifecycle statement

The recorded outpoints are one-satoshi UTXOs whose custody remains with the
operator's wallets (testnet for the v0.5 record, mainnet for v1.6). Nothing in this repository can move it, and moving it
on-chain would not alter the semantic state hash above: SATROOT state changes
only through valid protocol events, and no ledger event kind models root
custody. That separation is exactly what the anchored lane's report proves.
