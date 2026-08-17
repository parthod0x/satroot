# SATROOT Release Checklist

Before publishing a milestone tag such as `v0.1-genesis`, `v0.2-stable-profile`, or `v0.3-namespace-expansion`:

- [ ] Confirm this repo contains no private keys, seed phrases, API tokens, or wallet files.
- [ ] Confirm `root_id` values in examples are demo placeholders unless replaced with an intentional real outpoint.
- [ ] Run `python scripts/run_pytest_chunked.py` from the repo root for the full suite, or use `python -m satroot_test` / `satroot-test` after `pip install -e .`.
- [ ] Run `python scripts/run_profile_matrix_smoke.py` from the repo root, or use `python -m satroot_profile_matrix_smoke` / `satroot-profile-matrix-smoke` after `pip install -e .`, to verify all released profile lanes together and emit one consolidated smoke report.
- [ ] Run `python scripts/run_stable_profile_smoke.py` from the repo root, or use `python -m satroot_stable_profile_smoke` / `satroot-stable-profile-smoke` after `pip install -e .`, to confirm the checked-in SATROOT-STABLE-1 profile lane still replays `USDROOT1` and emits a lint-clean publication registry workspace.
- [ ] Run `python scripts/run_machine_profile_smoke.py` from the repo root, or use `python -m satroot_machine_profile_smoke` / `satroot-machine-profile-smoke` after `pip install -e .`, to confirm the checked-in SATROOT-MACHINE-1 profile lane still replays `APICREDIT1` and emits a lint-clean publication registry workspace.
- [ ] Run `python scripts/run_receipt_profile_smoke.py` from the repo root, or use `python -m satroot_receipt_profile_smoke` / `satroot-receipt-profile-smoke` after `pip install -e .`, to confirm the checked-in SATROOT-RECEIPT-1 profile lane still replays `RECEIPT1` and emits a lint-clean singleton publication registry workspace.
- [ ] Run `python scripts/run_identity_profile_smoke.py` from the repo root, or use `python -m satroot_identity_profile_smoke` / `satroot-identity-profile-smoke` after `pip install -e .`, to confirm the checked-in SATROOT-IDENTITY-1 profile lane still replays `IDENTITY1` and emits a lint-clean singleton publication registry workspace.
- [ ] Run `python scripts/run_license_profile_smoke.py` from the repo root, or use `python -m satroot_license_profile_smoke` / `satroot-license-profile-smoke` after `pip install -e .`, to confirm the checked-in SATROOT-LICENSE-1 profile lane still replays `LICENSE1` and emits a lint-clean singleton publication registry workspace.
- [ ] After `pip install -e .`, run `python -c "import satroot1, satroot_collection_lint, satroot_test, satroot_profile_matrix_smoke, satroot_stable_profile_smoke, satroot_machine_profile_smoke, satroot_receipt_profile_smoke, satroot_identity_profile_smoke, satroot_license_profile_smoke"` to confirm the installed modules resolve outside the repo-local pytest `pythonpath` shortcut.
- [ ] Optionally run `python -m pytest -q tests/test_run_pytest_chunked.py` as a quick smoke check on the chunked runner itself.
- [ ] Confirm no `__pycache__/`, `.pytest_cache/`, build artifacts, or local virtual environments are committed.
- [ ] Confirm README and SPEC use "anchor/root/witness" language, not "peg" language.
- [ ] Confirm README and SPEC do not claim subdivision below one satoshi.
- [ ] Confirm README and SPEC do not claim redemption, reserves, securities, e-money, investment returns, or wallet/exchange compatibility.
- [ ] Create git tag: `v0.1-genesis`.
- [ ] Preserve the release artifact hash after tagging.

Suggested tag message:

```text
SATROOT-1 v0.1 genesis: one satoshi as native floor, unbounded semantic state above.
```
