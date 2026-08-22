# Testing SATROOT

How to run the suite and each individual lane. See `README.md` for the
project overview and `INTEGRATION.md` for building on the package.

## Running the tests

For a quick local smoke run, pick one lane:

```bash
python -m pytest tests/test_stable_profile_smoke.py
```

Running bare `python -m pytest` collects the entire suite (1,600+ tests generating full publication workspaces) and is slow; prefer the chunked helper below for full runs.

For the full suite, prefer the chunked helper:

```bash
python scripts/run_pytest_chunked.py
```

For a stable-profile end-to-end smoke pass that replays the checked-in `USDROOT1` example and generates a full `SATROOT-STABLE-1` publication registry workspace:

```bash
python scripts/run_stable_profile_smoke.py
```

By default that writes into `.tmp_stable_profile_smoke_run/` so the generated workspace stays clearly disposable.

For the matching machine-credit lane, there is now an end-to-end smoke pass that replays `APICREDIT1` and generates a full `SATROOT-MACHINE-1` publication registry workspace:

```bash
python scripts/run_machine_profile_smoke.py
```

That one writes into `.tmp_machine_profile_smoke_run/` by default.

For the lower operator layer above individual bundles, there are now stable and machine bundle-index smoke passes that stage two checked-in presets, generate reusable signed bundle collections, and build one bundle index above each lane:

```bash
python scripts/run_machine_demo_bundle_index_smoke.py
python scripts/run_stable_demo_bundle_index_smoke.py
```

Those write into `.tmp_machine_demo_bundle_index_smoke_run/` and `.tmp_stable_demo_bundle_index_smoke_run/` by default.

For the higher-level machine release-catalog operator lane, there is also a smoke pass that stages two machine-only catalog presets from the checked-in compute example, generates a signed multi-release collection, and bootstraps a signed machine release catalog publication:

```bash
python scripts/run_machine_demo_release_catalog_smoke.py
```

That one writes into `.tmp_machine_demo_release_catalog_smoke_run/` by default.

For the matching stable release-catalog operator lane, there is a parallel smoke pass built from the checked-in stable reference catalog preset:

```bash
python scripts/run_stable_demo_release_catalog_smoke.py
```

That one writes into `.tmp_stable_demo_release_catalog_smoke_run/` by default.

For the release-catalog index layer above those same stable and machine operator lanes, there are matching smokes that stage two checked-in presets, generate signed collections, bootstrap release catalog publications, and then bootstrap signed release catalog index publications:

```bash
python scripts/run_machine_demo_release_catalog_index_smoke.py
python scripts/run_stable_demo_release_catalog_index_smoke.py
```

Those write into `.tmp_machine_demo_release_catalog_index_smoke_run/` and `.tmp_stable_demo_release_catalog_index_smoke_run/` by default.

For the receipt-object lane, there is now a matching end-to-end smoke pass that replays `RECEIPT1` and materializes a full `SATROOT-RECEIPT-1` singleton publication registry workspace from the checked-in receipt preset:

```bash
python scripts/run_receipt_profile_smoke.py
```

That one writes into `.tmp_receipt_profile_smoke_run/` by default.

For the lower singleton operator layer above individual receipt, identity, and license bundles, there are now matching bundle-index smoke passes that stage two checked-in presets, generate reusable signed bundle collections, and build one bundle index above each lane:

```bash
python scripts/run_receipt_demo_bundle_index_smoke.py
python scripts/run_identity_demo_bundle_index_smoke.py
python scripts/run_license_demo_bundle_index_smoke.py
```

Those write into `.tmp_receipt_demo_bundle_index_smoke_run/`, `.tmp_identity_demo_bundle_index_smoke_run/`, and `.tmp_license_demo_bundle_index_smoke_run/` by default.

For the identity-object lane, there is now a matching end-to-end smoke pass that replays `IDENTITY1` and materializes a full `SATROOT-IDENTITY-1` singleton publication registry workspace from the checked-in identity preset:

```bash
python scripts/run_identity_profile_smoke.py
```

That one writes into `.tmp_identity_profile_smoke_run/` by default.

For the license-object lane, there is now a matching end-to-end smoke pass that replays `LICENSE1` and materializes a full `SATROOT-LICENSE-1` singleton publication registry workspace from the checked-in license preset:

```bash
python scripts/run_license_profile_smoke.py
```

That one writes into `.tmp_license_profile_smoke_run/` by default.

After `pip install -e .`, the packaged entrypoints are available too:

```bash
python -m satroot_test
```

or:

```bash
satroot-test
```

For the preferred local pre-tag release gate above the individual verification surfaces, use:

```bash
python -m satroot_release_gate_smoke
```

or:

```bash
satroot-release-gate-smoke
```

That one writes into `.tmp_release_gate_smoke_run/` by default and runs installed-module import smoke, the top-level operator proof, and chunked pytest together into one consolidated release-gate report.

The GitHub Actions test workflow now uses this same release-gate wrapper as its single umbrella check after installed-module import smoke: the operator proof inside the gate re-runs the ladder, federation, registry, and anchored surfaces, and chunked pytest covers every per-lane smoke test, so CI does not repeat the narrower smoke workflows as separate steps.

The preferred top-level verification for the currently released operator surface is:

```bash
python -m satroot_operator_proof_smoke
```

or:

```bash
satroot-operator-proof-smoke
```

That one writes into `.tmp_operator_proof_smoke_run/` by default and runs the stable/machine publication ladder, the singleton publication ladder, the mixed-profile federation smoke, and the collection-backed federated registry publication round trip, plus the four anchored surfaces — anchored demo, anchored publication, on-chain envelope, and envelope verification — for eight surfaces total in one consolidated proof report, with the two ed25519 surfaces skipping gracefully without the `[crypto]` extra.

If you only want the released per-profile verification surface beneath that top-level proof, use:

```bash
python -m satroot_profile_matrix_smoke
```

or:

```bash
satroot-profile-matrix-smoke
```

That one writes into `.tmp_profile_matrix_smoke_run/` by default and runs the stable, machine, receipt, identity, and license profile smoke workflows into one consolidated report.

For the matching lower singleton operator layer, there is also:

```bash
python -m satroot_singleton_demo_bundle_index_matrix_smoke
```

or:

```bash
satroot-singleton-demo-bundle-index-matrix-smoke
```

That one writes into `.tmp_singleton_demo_bundle_index_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo bundle-index smoke workflows into one consolidated report.

For the next singleton operator layer above those bundle indexes, there is also:

```bash
python -m satroot_singleton_demo_release_catalog_matrix_smoke
```

or:

```bash
satroot-singleton-demo-release-catalog-matrix-smoke
```

That one writes into `.tmp_singleton_demo_release_catalog_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo release-catalog smoke workflows into one consolidated report.

For the next singleton operator layer above those per-profile catalogs, there is also:

```bash
python -m satroot_singleton_demo_release_catalog_index_matrix_smoke
```

or:

```bash
satroot-singleton-demo-release-catalog-index-matrix-smoke
```

That one writes into `.tmp_singleton_demo_release_catalog_index_matrix_smoke_run/` by default and runs the receipt, identity, and license singleton demo release-catalog-index smoke workflows into one consolidated report.

If you want the full singleton operator ladder in one pass, there is also:

```bash
python -m satroot_singleton_publication_ladder_smoke
```

or:

```bash
satroot-singleton-publication-ladder-smoke
```

That one writes into `.tmp_singleton_publication_ladder_smoke_run/` by default and runs the singleton bundle-index, release-catalog, and release-catalog-index matrix smokes together into one consolidated ladder report.

For the lowest multi-bundle operator layer above those direct profile smokes, there is also:

```bash
python -m satroot_demo_bundle_index_matrix_smoke
```

or:

```bash
satroot-demo-bundle-index-matrix-smoke
```

That one writes into `.tmp_demo_bundle_index_matrix_smoke_run/` by default and runs the stable and machine demo bundle-index smoke workflows into one consolidated report.

For the lower operator layer above single releases but beneath the profile federation proof, there is also:

```bash
python -m satroot_demo_release_catalog_matrix_smoke
```

or:

```bash
satroot-demo-release-catalog-matrix-smoke
```

That one writes into `.tmp_demo_release_catalog_matrix_smoke_run/` by default and runs the stable and machine demo release-catalog smoke workflows into one consolidated report.

For the next layer up in that same operator ladder, there is also:

```bash
python -m satroot_demo_release_catalog_index_matrix_smoke
```

or:

```bash
satroot-demo-release-catalog-index-matrix-smoke
```

That one writes into `.tmp_demo_release_catalog_index_matrix_smoke_run/` by default and runs the stable and machine demo release-catalog-index smoke workflows into one consolidated report.

If you want that full stable/machine operator ladder in one pass, there is also:

```bash
python -m satroot_publication_ladder_smoke
```

or:

```bash
satroot-publication-ladder-smoke
```

That one writes into `.tmp_publication_ladder_smoke_run/` by default and runs the stable/machine bundle-index, release-catalog, and release-catalog-index matrix smokes together into one consolidated ladder report.

For the first operator-facing federation check above those released lanes, there is also:

```bash
python -m satroot_profile_federation_smoke
```

or:

```bash
satroot-profile-federation-smoke
```

That one writes into `.tmp_profile_federation_smoke_run/` by default, reuses the released profile matrix, freezes the resulting per-profile demo-catalog, publication-stack, publication-network, publication-catalog-workspace, and publication-registry-workspace outputs into explicit collections, builds one shared mixed-profile publication catalog workspace plus publication registry workspace above the federated network, snapshots those mixed top-level workspaces into their own explicit collections too, and round-trips the federated catalog workspace, stack, network, and top-level registry workspace back through exported nested presets.

If you want the next higher proof layer above that federated workspace surface, there is also:

```bash
python -m satroot_federated_registry_collection_smoke
```

or:

```bash
satroot-federated-registry-collection-smoke
```

That one writes into `.tmp_federated_registry_collection_smoke_run/` by default, reruns the mixed-profile federation smoke, reuses the generated top-level `publication_registry_workspace_collection`, bootstraps a top-level publication-registry publication from that collection-backed preset, exports the generated publication back into a preset, and bootstraps the publication again to prove the collection-backed registry publication round trip.

There is also a packaged stable-profile smoke entrypoint:

```bash
python -m satroot_stable_profile_smoke
```

or:

```bash
satroot-stable-profile-smoke
```

And the machine-credit lane has the same packaged entrypoints:

```bash
python -m satroot_machine_profile_smoke
```

or:

```bash
satroot-machine-profile-smoke
```

The singleton receipt lane also has lower publication-ladder wrappers:

```bash
python scripts/run_receipt_demo_release_catalog_smoke.py
python scripts/run_receipt_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_receipt_demo_release_catalog_smoke
python -m satroot_receipt_demo_release_catalog_index_smoke
```

The singleton identity lane exposes the same local and packaged flows:

```bash
python scripts/run_identity_demo_release_catalog_smoke.py
python scripts/run_identity_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_identity_demo_release_catalog_smoke
python -m satroot_identity_demo_release_catalog_index_smoke
```

The singleton license lane exposes the same local and packaged flows:

```bash
python scripts/run_license_demo_release_catalog_smoke.py
python scripts/run_license_demo_release_catalog_index_smoke.py
```

or:

```bash
python -m satroot_license_demo_release_catalog_smoke
python -m satroot_license_demo_release_catalog_index_smoke
```

And the stable and machine demo release-catalog operator lanes have packaged entrypoints too:

```bash
python -m satroot_stable_demo_release_catalog_smoke
python -m satroot_machine_demo_release_catalog_smoke
```

or:

```bash
satroot-stable-demo-release-catalog-smoke
satroot-machine-demo-release-catalog-smoke
```

And the matching index-layer operator lanes have packaged entrypoints too:

```bash
python -m satroot_stable_demo_release_catalog_index_smoke
python -m satroot_machine_demo_release_catalog_index_smoke
```

or:

```bash
satroot-stable-demo-release-catalog-index-smoke
satroot-machine-demo-release-catalog-index-smoke
```

The receipt lane has the same packaged entrypoints:

```bash
python -m satroot_receipt_profile_smoke
```

or:

```bash
satroot-receipt-profile-smoke
```

The identity lane has the same packaged entrypoints:

```bash
python -m satroot_identity_profile_smoke
```

or:

```bash
satroot-identity-profile-smoke
```

The license lane has the same packaged entrypoints:

```bash
python -m satroot_license_profile_smoke
```

or:

```bash
satroot-license-profile-smoke
```

The three chunked-runner forms (`scripts/run_pytest_chunked.py`, `python -m satroot_test`, `satroot-test`) collect from the full `tests/` tree by default.

You can also resume from a later point or reduce chunk size:

```bash
python scripts/run_pytest_chunked.py --chunk-size 50 --start 1001
```

or:

```bash
python -m satroot_test --chunk-size 50 --start 1001
```

or:

```bash
satroot-test --chunk-size 50 --start 1001
```

Current suite note:

```text
the tests/ tree is large enough that chunked execution is the preferred full-suite path
```

