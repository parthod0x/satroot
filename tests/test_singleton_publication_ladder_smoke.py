from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_singleton_publication_ladder_smoke import run_singleton_publication_ladder_smoke


def test_run_singleton_publication_ladder_smoke_builds_all_singleton_operator_layers(tmp_path):
    report = run_singleton_publication_ladder_smoke(tmp_path / "singleton_publication_ladder_smoke")

    assert report["ok"] is True
    assert report["layer_count"] == 3
    assert set(report["layers"]) == {
        "bundle_index",
        "release_catalog",
        "release_catalog_index",
    }
    assert report["layers"]["bundle_index"]["profile_count"] == 3
    assert report["layers"]["release_catalog"]["profile_count"] == 3
    assert report["layers"]["release_catalog_index"]["profile_count"] == 3
    assert Path(report["layers"]["bundle_index"]["report_path"]).is_file()
    assert Path(report["layers"]["release_catalog"]["report_path"]).is_file()
    assert Path(report["layers"]["release_catalog_index"]["report_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_singleton_publication_ladder_smoke_wrapper_runs_without_editable_install(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_singleton_publication_ladder_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_singleton_publication_ladder_smoke_runs_with_repo_pythonpath(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_singleton_publication_ladder_smoke",
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
