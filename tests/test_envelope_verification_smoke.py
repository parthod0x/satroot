from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from satroot1 import SatRootError
from satroot_anchored_demo_smoke import PLACEHOLDER_ROOT_ID
from satroot_envelope_verification_smoke import (
    build_demo_transaction,
    parse_raw_transaction,
    run_envelope_verification_smoke,
)
from satroot_onchain_envelope_smoke import (
    CONTENT_TYPE,
    PLACEHOLDER_STATE_HASH,
    build_envelope_payload,
    build_envelope_script,
)


def test_run_envelope_verification_smoke_synthetic(tmp_path):
    report = run_envelope_verification_smoke(tmp_path / "envelope_verification_smoke")

    assert report["ok"] is True
    assert report["synthetic_transaction"] is True
    assert report["root_id"] == PLACEHOLDER_ROOT_ID
    assert report["root_is_placeholder"] is True
    assert report["envelope_output_index"] == 0
    assert all(report["checks"].values())
    assert Path(report["report_path"]).is_file()


def test_run_envelope_verification_smoke_with_supplied_raw_tx(tmp_path):
    root = "d" * 64 + ":0"
    state_hash = "sha256:" + "cd" * 32
    script = build_envelope_script(CONTENT_TYPE, build_envelope_payload(root, state_hash))
    raw = build_demo_transaction(script)
    txid = parse_raw_transaction(raw)["txid"]

    report = run_envelope_verification_smoke(
        tmp_path / "envelope_verification_smoke_supplied",
        raw_tx_hex=raw.hex(),
        root_id=root,
        state_hash=state_hash,
        expected_txid=txid,
    )

    assert report["ok"] is True
    assert report["synthetic_transaction"] is False
    assert report["computed_txid"] == txid
    assert report["checks"]["txid_matches_expected"] is True


def test_run_envelope_verification_smoke_detects_wrong_commitment(tmp_path):
    script = build_envelope_script(
        CONTENT_TYPE, build_envelope_payload("e" * 64 + ":0", PLACEHOLDER_STATE_HASH)
    )
    raw = build_demo_transaction(script)

    report = run_envelope_verification_smoke(
        tmp_path / "envelope_verification_smoke_wrong",
        raw_tx_hex=raw.hex(),
        root_id=PLACEHOLDER_ROOT_ID,
        state_hash=PLACEHOLDER_STATE_HASH,
    )

    assert report["ok"] is False
    assert report["checks"]["commitment_matches"] is False
    assert report["checks"]["script_byte_identical_to_rebuild"] is False


def test_run_envelope_verification_smoke_detects_wrong_txid(tmp_path):
    report = run_envelope_verification_smoke(
        tmp_path / "envelope_verification_smoke_badtxid",
        raw_tx_hex=build_demo_transaction(
            build_envelope_script(
                CONTENT_TYPE,
                build_envelope_payload(PLACEHOLDER_ROOT_ID, PLACEHOLDER_STATE_HASH),
            )
        ).hex(),
        expected_txid="ab" * 32,
    )

    assert report["ok"] is False
    assert report["checks"]["txid_matches_expected"] is False


def test_parse_raw_transaction_rejects_malformed_bytes():
    with pytest.raises(SatRootError):
        parse_raw_transaction(bytes(3))
    with pytest.raises(SatRootError):
        parse_raw_transaction(bytes.fromhex("0100000001"))
    valid = build_demo_transaction(
        build_envelope_script(
            CONTENT_TYPE, build_envelope_payload(PLACEHOLDER_ROOT_ID, PLACEHOLDER_STATE_HASH)
        )
    )
    with pytest.raises(SatRootError):
        parse_raw_transaction(valid + b"\x00")


def test_repo_local_envelope_verification_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_envelope_verification_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_envelope_verification_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_envelope_verification_smoke",
            "--output-dir",
            str(tmp_path / "module_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(repo_root / "src"),
        },
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout
