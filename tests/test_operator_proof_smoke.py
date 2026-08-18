from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot_operator_proof_smoke import run_operator_proof_smoke


def test_run_operator_proof_smoke_builds_all_top_level_operator_surfaces(tmp_path):
    report = run_operator_proof_smoke(tmp_path / "operator_proof_smoke")

    assert report["ok"] is True
    assert report["surface_count"] == 3
    assert set(report["surfaces"]) == {
        "publication_ladder",
        "singleton_publication_ladder",
        "profile_federation",
    }
    assert report["surfaces"]["publication_ladder"]["layer_count"] == 3
    assert report["surfaces"]["singleton_publication_ladder"]["layer_count"] == 3
    assert report["surfaces"]["profile_federation"]["profile_count"] == 5
    assert report["surfaces"]["profile_federation"]["publication_registry_artifact_count"] == 15
    assert Path(report["surfaces"]["publication_ladder"]["report_path"]).is_file()
    assert Path(report["surfaces"]["singleton_publication_ladder"]["report_path"]).is_file()
    assert Path(report["surfaces"]["profile_federation"]["report_path"]).is_file()
    assert Path(report["report_path"]).is_file()


def test_repo_local_operator_proof_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_operator_proof_smoke.py",
            "--output-dir",
            str(tmp_path / "wrapper_run"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"ok": true' in result.stdout


def test_module_entrypoint_operator_proof_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_operator_proof_smoke",
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
