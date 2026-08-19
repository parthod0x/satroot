from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from satroot1 import SatRootError
from satroot_anchored_demo_smoke import PLACEHOLDER_ROOT_ID
from satroot_onchain_envelope_smoke import (
    CONTENT_TYPE,
    PLACEHOLDER_STATE_HASH,
    build_envelope_payload,
    build_envelope_script,
    encode_push,
    parse_envelope_script,
    run_onchain_envelope_smoke,
)


def test_run_onchain_envelope_smoke_with_placeholders(tmp_path):
    report = run_onchain_envelope_smoke(tmp_path / "onchain_envelope_smoke")

    assert report["ok"] is True
    assert report["content_type"] == "application/satroot1+json"
    assert report["root_id"] == PLACEHOLDER_ROOT_ID
    assert report["root_is_placeholder"] is True
    assert report["state_hash"] == PLACEHOLDER_STATE_HASH
    assert report["envelope_script_hex"].startswith("006a")
    assert all(report["checks"].values())
    assert Path(report["report_path"]).is_file()
    written_hex = (
        (tmp_path / "onchain_envelope_smoke" / "envelope_script.hex")
        .read_text(encoding="utf-8")
        .strip()
    )
    assert written_hex == report["envelope_script_hex"]


def test_run_onchain_envelope_smoke_with_explicit_commitment(tmp_path):
    root = "c" * 64 + ":0"
    state_hash = "sha256:" + "ab" * 32
    report = run_onchain_envelope_smoke(
        tmp_path / "onchain_envelope_smoke_explicit",
        root_id=root,
        state_hash=state_hash,
    )

    assert report["ok"] is True
    assert report["root_is_placeholder"] is False
    assert report["decoded_payload"] == {
        "protocol": "SATROOT-1",
        "root_id": root,
        "state_hash": state_hash,
    }


def test_envelope_build_is_deterministic():
    first = build_envelope_script(
        CONTENT_TYPE, build_envelope_payload(PLACEHOLDER_ROOT_ID, PLACEHOLDER_STATE_HASH)
    )
    second = build_envelope_script(
        CONTENT_TYPE, build_envelope_payload(PLACEHOLDER_ROOT_ID, PLACEHOLDER_STATE_HASH)
    )
    assert first == second


def test_envelope_rejects_invalid_inputs(tmp_path):
    with pytest.raises(SatRootError):
        build_envelope_payload("not-an-outpoint", PLACEHOLDER_STATE_HASH)
    with pytest.raises(SatRootError):
        build_envelope_payload(PLACEHOLDER_ROOT_ID, "sha256:short")
    with pytest.raises(SatRootError):
        parse_envelope_script(b"\x6a\x00")
    with pytest.raises(SatRootError):
        parse_envelope_script(
            b"\x00\x6a" + encode_push(b"NOTROOT1") + encode_push(b"x") + encode_push(b"{}")
        )


def test_encode_push_covers_pushdata_ranges():
    assert encode_push(b"a" * 0x4B)[0] == 0x4B
    assert encode_push(b"a" * 0x4C)[0] == 0x4C
    assert encode_push(b"a" * 0x100)[0] == 0x4D
    with pytest.raises(SatRootError):
        encode_push(b"")


def test_repo_local_onchain_envelope_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_onchain_envelope_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_onchain_envelope_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_onchain_envelope_smoke",
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
