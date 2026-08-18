from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_singleton_demo_release_catalog_matrix_smoke import (
    run_singleton_demo_release_catalog_matrix_smoke,
)


def test_run_singleton_demo_release_catalog_matrix_smoke_builds_receipt_identity_license_catalogs(
    tmp_path,
):
    report = run_singleton_demo_release_catalog_matrix_smoke(
        tmp_path / "singleton_demo_release_catalog_matrix_smoke"
    )

    assert report["ok"] is True
    assert report["profile_count"] == 3
    assert set(report["profiles"]) == {"receipt", "identity", "license"}
    assert report["profiles"]["receipt"]["profile"] == "SATROOT-RECEIPT-1"
    assert report["profiles"]["identity"]["profile"] == "SATROOT-IDENTITY-1"
    assert report["profiles"]["license"]["profile"] == "SATROOT-LICENSE-1"
    assert report["profiles"]["receipt"]["generated_release_count"] == 2
    assert report["profiles"]["identity"]["generated_release_count"] == 2
    assert report["profiles"]["license"]["generated_release_count"] == 2
    assert Path(report["profiles"]["receipt"]["release_catalog_manifest_path"]).is_file()
    assert Path(report["profiles"]["identity"]["release_catalog_manifest_path"]).is_file()
    assert Path(report["profiles"]["license"]["release_catalog_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_singleton_demo_release_catalog_matrix_smoke_wrapper_runs_without_editable_install(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_singleton_demo_release_catalog_matrix_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_singleton_demo_release_catalog_matrix_smoke_runs_with_repo_pythonpath(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_singleton_demo_release_catalog_matrix_smoke",
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
