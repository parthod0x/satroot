# SATROOT-1 v0.1 Release Checklist

Before publishing `v0.1-genesis`:

- [ ] Confirm this repo contains no private keys, seed phrases, API tokens, or wallet files.
- [ ] Confirm `root_id` values in examples are demo placeholders unless replaced with an intentional real outpoint.
- [ ] Run `python scripts/run_pytest_chunked.py` from the repo root for the full suite, or use `python -m satroot_test` / `satroot-test` after `pip install -e .`.
- [ ] After `pip install -e .`, run `python -c "import satroot1, satroot_collection_lint, satroot_test"` to confirm the installed modules resolve outside the repo-local pytest `pythonpath` shortcut.
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
