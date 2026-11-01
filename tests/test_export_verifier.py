"""satroot_export: the export verifier runs from the package, never from the export.

The fixture under tests/fixtures/export_v01 is a real export with one action
and no anchors, written before key binding (ledger version 0.1).
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import satroot_export as sx  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "export_v01"


@pytest.fixture()
def export(tmp_path):
    target = tmp_path / "export"
    shutil.copytree(FIXTURE, target)
    return target


def test_a_legacy_export_verifies_and_says_its_keys_are_unbound(export):
    result = sx.verify_export(export)
    assert result["keys_bound"] is False
    assert result["keys_pinned"] is False and result["genesis_pinned"] is False


def test_a_legacy_export_is_refused_when_bound_keys_are_required(export):
    with pytest.raises(Exception, match="binds no signing key"):
        sx.verify_export(export, allow_unbound_keys=False)


def test_the_genesis_pin_is_checked_and_reported(export):
    genesis = json.loads((export / "bundle" / "signed_events.json").read_text(encoding="utf-8"))[0]
    good = sx.sr.event_id(genesis)
    assert sx.verify_export(export, expected_genesis_event_id=good)["genesis_pinned"] is True
    with pytest.raises(Exception, match="pinned genesis"):
        sx.verify_export(export, expected_genesis_event_id="sha256:" + "0" * 64)


def test_pinned_keys_are_used_instead_of_the_exports_own(export):
    keys = json.loads((export / "bundle" / "public_keys.json").read_text(encoding="utf-8"))
    assert sx.verify_export(export, public_keys=keys)["keys_pinned"] is True
    wrong = {key_id: "00" * 32 for key_id in keys}
    with pytest.raises(Exception):
        sx.verify_export(export, public_keys=wrong)


def test_any_module_loaded_from_inside_the_export_is_refused(export):
    """The guard used to check satroot1 alone; an export-supplied tokenverify.py
    holding the trusted authority list was imported and the export passed."""
    planted = export / "planted_helper.py"
    planted.write_text("VALUE = 1\n", encoding="utf-8")
    spec = importlib.util.spec_from_file_location("planted_helper", planted)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["planted_helper"] = module
    try:
        with pytest.raises(sx.VerificationError, match="inside the export"):
            sx.verify_export(export)
    finally:
        del sys.modules["planted_helper"]


def test_run_isolated_from_inside_the_export_planted_code_never_runs(export):
    """`python -I -m satroot_export` keeps the current directory off the import
    path, so an export carrying satroot1.py, satroot_tsa.py or satroot_export.py
    of its own cannot have them executed - even run from inside it."""
    for name in ("satroot1.py", "satroot_tsa.py", "satroot_export.py", "satroot_commitment.py"):
        (export / name).write_text("raise SystemExit('PLANTED CODE RAN')\n", encoding="utf-8")
    code = ("import sys, runpy; sys.path.insert(0, %r); sys.argv = ['satroot_export', %r]; "
            "runpy.run_module('satroot_export', run_name='__main__')" % (str(SRC), str(export)))
    run = subprocess.run([sys.executable, "-I", "-c", code], cwd=export, capture_output=True, text=True)
    assert "PLANTED" not in run.stdout + run.stderr
    assert run.returncode == 0, run.stdout + run.stderr


def test_exports_no_longer_need_to_carry_code():
    assert not (FIXTURE / "verify_export.py").exists() and not (FIXTURE / "tokenverify.py").exists()


# ---- 3.0.2: the order of anchor records is reported, not enforced ---------------------------

def _offline_anchor(export, entries):
    """An unpublished anchor at event 1 attesting the first `entries` action-log entries."""
    import satroot1 as sr
    from satroot_onchain_envelope_smoke import CONTENT_TYPE, build_envelope_payload, build_envelope_script

    events = json.loads((export / "bundle" / "signed_events.json").read_text(encoding="utf-8"))
    keys = json.loads((export / "bundle" / "public_keys.json").read_text(encoding="utf-8"))
    state_hash = sr.replay(events[:1], verifier=sr.make_ed25519_verifier(keys), allow_unbound_keys=True).state_hash()
    log = [json.loads(line) for line in (export / "action_log.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    payload = build_envelope_payload(events[0]["root_id"], state_hash)
    return {"content_type": CONTENT_TYPE, "root_id": events[0]["root_id"], "state_hash": state_hash,
            "envelope_script_hex": build_envelope_script(CONTENT_TYPE, payload).hex(),
            "payload_json": payload.decode("utf-8"), "event_count": 1, "published": False,
            "action_log_entries": entries, "action_log_head": log[entries - 1]["entry_hash"] if entries else "genesis"}


def _write_anchors(export, anchors):
    (export / "anchor_commitments.json").write_text(json.dumps(anchors, indent=2) + "\n", encoding="utf-8")


def test_anchors_at_one_event_count_verify_when_only_the_action_log_moved(export):
    """Found on a production ledger: an action recorded between two anchors gives a new
    checkpoint at the same event_count, and the strictly-rising rule refused the export for good."""
    _write_anchors(export, [_offline_anchor(export, 0), _offline_anchor(export, 1)])
    result = sx.verify_export(export)
    assert result["anchors"]["count"] == 2
    assert result["anchors"]["in_file_order"] is True and result["anchors"]["repeated_checkpoints"] == 0
    assert result["anchors_present_pin_to_event"] == 1


def test_repeated_and_reordered_anchor_records_are_reported_not_refused(export):
    first, second = _offline_anchor(export, 0), _offline_anchor(export, 1)
    _write_anchors(export, [second, second, first])
    result = sx.verify_export(export)
    assert result["anchors"]["repeated_checkpoints"] == 1
    assert result["anchors"]["in_file_order"] is False


def test_order_does_not_rescue_a_rewritten_anchor(export):
    forged = _offline_anchor(export, 1)
    forged["state_hash"] = "sha256:" + "99" * 32
    _write_anchors(export, [_offline_anchor(export, 0), forged])
    with pytest.raises(sx.VerificationError):
        sx.verify_export(export)


def test_an_anchor_event_count_must_be_a_positive_integer(export):
    bad = _offline_anchor(export, 0)
    bad["event_count"] = 0
    _write_anchors(export, [bad])
    with pytest.raises(sx.VerificationError, match="positive integer"):
        sx.verify_export(export)
