from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from satroot1 import ed25519_available
from satroot_operator_proof_smoke import run_operator_proof_smoke


def test_run_operator_proof_smoke_builds_all_top_level_operator_surfaces(tmp_path):
    report = run_operator_proof_smoke(tmp_path / "operator_proof_smoke")

    assert report["ok"] is True
    assert report["surface_count"] == 8
    assert set(report["surfaces"]) == {
        "publication_ladder",
        "singleton_publication_ladder",
        "profile_federation",
        "federated_registry_collection",
        "anchored_demo",
        "anchored_publication",
        "onchain_envelope",
        "envelope_verification",
    }
    assert report["surfaces"]["publication_ladder"]["layer_count"] == 3
    assert report["surfaces"]["singleton_publication_ladder"]["layer_count"] == 3
    assert report["surfaces"]["profile_federation"]["profile_count"] == 6
    assert report["surfaces"]["profile_federation"]["publication_registry_artifact_count"] == 18
    assert report["surfaces"]["federated_registry_collection"]["workspace_count"] == 1
    assert report["surfaces"]["federated_registry_collection"]["publication_registry_component_count"] == 3
    assert (
        report["surfaces"]["federated_registry_collection"]["roundtrip_publication_registry_component_count"]
        == 3
    )
    assert Path(report["surfaces"]["publication_ladder"]["report_path"]).is_file()
    assert Path(report["surfaces"]["singleton_publication_ladder"]["report_path"]).is_file()
    assert Path(report["surfaces"]["profile_federation"]["report_path"]).is_file()
    assert Path(report["surfaces"]["federated_registry_collection"]["report_path"]).is_file()
    for anchored_surface in ("anchored_demo", "anchored_publication"):
        surface = report["surfaces"][anchored_surface]
        assert surface["ok"] is True
        if surface.get("skipped") is True:
            assert ed25519_available() is False
        else:
            assert surface["root_is_placeholder"] is True
            assert Path(surface["report_path"]).is_file()
    for offline_surface in ("onchain_envelope", "envelope_verification"):
        surface = report["surfaces"][offline_surface]
        assert surface["ok"] is True
        assert all(surface["checks"].values())
        assert Path(surface["report_path"]).is_file()
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
