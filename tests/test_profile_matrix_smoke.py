from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_profile_matrix_smoke import run_profile_matrix_smoke


def test_run_profile_matrix_smoke_builds_all_released_profile_workspaces(tmp_path):
    report = run_profile_matrix_smoke(tmp_path / "profile_matrix_smoke")

    assert report["ok"] is True
    assert report["profile_count"] == 5
    assert set(report["profiles"]) == {"stable", "machine", "receipt", "identity", "license"}
    assert report["profiles"]["stable"]["profile"] == "SATROOT-STABLE-1"
    assert report["profiles"]["machine"]["profile"] == "SATROOT-MACHINE-1"
    assert report["profiles"]["receipt"]["profile"] == "SATROOT-RECEIPT-1"
    assert report["profiles"]["identity"]["profile"] == "SATROOT-IDENTITY-1"
    assert report["profiles"]["license"]["profile"] == "SATROOT-LICENSE-1"
    assert Path(report["profiles"]["stable"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["profiles"]["machine"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["profiles"]["receipt"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["profiles"]["identity"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["profiles"]["license"]["publication_registry_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_profile_matrix_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_profile_matrix_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_profile_matrix_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_profile_matrix_smoke",
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
