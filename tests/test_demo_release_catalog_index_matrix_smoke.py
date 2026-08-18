from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_demo_release_catalog_index_matrix_smoke import (
    run_demo_release_catalog_index_matrix_smoke,
)


def test_run_demo_release_catalog_index_matrix_smoke_builds_stable_and_machine_indexes(
    tmp_path,
):
    report = run_demo_release_catalog_index_matrix_smoke(
        tmp_path / "demo_release_catalog_index_matrix_smoke"
    )

    assert report["ok"] is True
    assert report["profile_count"] == 2
    assert set(report["profiles"]) == {"stable", "machine"}
    assert report["profiles"]["stable"]["profile"] == "SATROOT-STABLE-1"
    assert report["profiles"]["machine"]["profile"] == "SATROOT-MACHINE-1"
    assert report["profiles"]["stable"]["generated_release_count"] == 2
    assert report["profiles"]["machine"]["generated_release_count"] == 2
    assert Path(report["profiles"]["stable"]["release_catalog_index_manifest_path"]).is_file()
    assert Path(report["profiles"]["machine"]["release_catalog_index_manifest_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_demo_release_catalog_index_matrix_smoke_wrapper_runs_without_editable_install(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_demo_release_catalog_index_matrix_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_demo_release_catalog_index_matrix_smoke_runs_with_repo_pythonpath(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_demo_release_catalog_index_matrix_smoke",
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
