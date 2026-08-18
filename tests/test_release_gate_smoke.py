from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from satroot_release_gate_smoke import run_release_gate_smoke


def _write_smoke_test_tree(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "test_alpha.py").write_text(
        "def test_alpha():\n"
        "    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )
    (root / "test_beta.py").write_text(
        "def test_beta():\n"
        "    assert 'satroot'.upper() == 'SATROOT'\n",
        encoding="utf-8",
    )


def _prepare_repo_local_smoke_test_tree(tmp_path: Path) -> tuple[Path, str]:
    repo_root = Path(__file__).resolve().parents[1]
    relative_path = Path(".tmp_release_gate_smoke_test_inputs") / tmp_path.name
    smoke_tests = repo_root / relative_path
    if smoke_tests.exists():
        shutil.rmtree(smoke_tests)
    _write_smoke_test_tree(smoke_tests)
    return smoke_tests, str(relative_path)


def test_run_release_gate_smoke_executes_import_and_chunked_pytest_on_custom_paths(tmp_path):
    smoke_tests, relative_path = _prepare_repo_local_smoke_test_tree(tmp_path)
    try:
        report = run_release_gate_smoke(
            tmp_path / "release_gate_smoke",
            pytest_paths=[relative_path],
            chunk_size=1,
            run_operator_proof=False,
        )

        assert report["ok"] is True
        assert report["import_smoke"]["ok"] is True
        assert report["operator_proof"]["skipped"] is True
        assert report["chunked_pytest"]["ok"] is True
        assert report["chunked_pytest"]["chunk_size"] == 1
        assert report["chunked_pytest"]["pytest_paths"] == [relative_path]
        assert Path(report["chunked_pytest"]["log_path"]).is_file()
        assert Path(report["report_path"]).is_file()
    finally:
        shutil.rmtree(smoke_tests, ignore_errors=True)


def test_repo_local_release_gate_smoke_wrapper_runs_without_editable_install(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    smoke_tests, relative_path = _prepare_repo_local_smoke_test_tree(tmp_path)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_release_gate_smoke.py",
                "--output-dir",
                str(tmp_path / "wrapper_run"),
                "--pytest-path",
                relative_path,
                "--chunk-size",
                "1",
                "--skip-operator-proof",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert '"ok": true' in result.stdout
    finally:
        shutil.rmtree(smoke_tests, ignore_errors=True)


def test_module_entrypoint_release_gate_smoke_runs_with_repo_pythonpath(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    smoke_tests, relative_path = _prepare_repo_local_smoke_test_tree(tmp_path)
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "satroot_release_gate_smoke",
                "--output-dir",
                str(tmp_path / "module_run"),
                "--pytest-path",
                relative_path,
                "--chunk-size",
                "1",
                "--skip-operator-proof",
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
    finally:
        shutil.rmtree(smoke_tests, ignore_errors=True)
