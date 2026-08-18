from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from satroot1 import SatRootError, ed25519_available
from satroot_anchored_demo_smoke import (
    PLACEHOLDER_ROOT_ID,
    run_anchored_demo_smoke,
)


requires_ed25519 = pytest.mark.skipif(
    not ed25519_available(), reason="cryptography package is not installed"
)


@requires_ed25519
def test_run_anchored_demo_smoke_with_placeholder_root(tmp_path):
    report = run_anchored_demo_smoke(tmp_path / "anchored_demo_smoke")

    assert report["ok"] is True
    assert report["profile"] == "SATROOT-IDENTITY-1"
    assert report["bundle_scheme"] == "ed25519"
    assert report["root_id"] == PLACEHOLDER_ROOT_ID
    assert report["root_is_placeholder"] is True
    assert report["checks"]["root_id_bound_to_state"] is True
    assert report["checks"]["ed25519_bundle_verified"] is True
    assert report["checks"]["replay_deterministic"] is True
    assert report["checks"]["foreign_root_rejected"] is True
    assert report["checks"]["no_custody_event_kinds"] is True
    assert report["foreign_root_error"] == "root_id mismatch"
    assert report["final_state_hash"].startswith("sha256:")
    assert Path(report["signed_events_path"]).is_file()
    assert Path(report["public_keys_path"]).is_file()
    assert Path(report["report_path"]).is_file()


@requires_ed25519
def test_run_anchored_demo_smoke_with_explicit_root_id(tmp_path):
    explicit_root = "a" * 64 + ":1"
    report = run_anchored_demo_smoke(
        tmp_path / "anchored_demo_smoke_explicit", root_id=explicit_root
    )

    assert report["ok"] is True
    assert report["root_id"] == explicit_root
    assert report["root_is_placeholder"] is False
    assert report["checks"]["root_id_bound_to_state"] is True


@requires_ed25519
def test_run_anchored_demo_smoke_rejects_invalid_root_id(tmp_path):
    with pytest.raises(SatRootError):
        run_anchored_demo_smoke(
            tmp_path / "anchored_demo_smoke_invalid", root_id="not-an-outpoint"
        )


@requires_ed25519
def test_repo_local_anchored_demo_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_anchored_demo_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


@requires_ed25519
def test_module_entrypoint_anchored_demo_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_anchored_demo_smoke",
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
