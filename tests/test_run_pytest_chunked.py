from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from satroot_test import build_pytest_command, select_nodeids


def test_select_nodeids_returns_requested_1_based_slice():
    selected, total, start_index = select_nodeids(
        ["test_a", "test_b", "test_c", "test_d"],
        start=2,
        stop=3,
    )

    assert selected == ["test_b", "test_c"]
    assert total == 4
    assert start_index == 1


def test_select_nodeids_uses_tail_when_stop_is_not_provided():
    selected, total, start_index = select_nodeids(
        ["test_a", "test_b", "test_c", "test_d"],
        start=3,
        stop=None,
    )

    assert selected == ["test_c", "test_d"]
    assert total == 4
    assert start_index == 2


def test_select_nodeids_rejects_out_of_range_start():
    with pytest.raises(ValueError, match="beyond collected test count 2"):
        select_nodeids(["test_a", "test_b"], start=3, stop=None)


def test_select_nodeids_rejects_non_positive_start():
    with pytest.raises(ValueError, match="--start must be >= 1"):
        select_nodeids(["test_a", "test_b"], start=0, stop=None)


def test_select_nodeids_rejects_stop_before_start():
    with pytest.raises(ValueError, match="--stop must be >= --start"):
        select_nodeids(["test_a", "test_b"], start=2, stop=1)


def test_build_pytest_command_includes_quiet_mode_extra_args_and_nodeids():
    command = build_pytest_command(
        extra_args=["-k", "machine"],
        nodeids=["tests/test_satroot1.py::test_alpha", "tests/test_satroot1.py::test_beta"],
    )

    assert command[:4] == [sys.executable, "-m", "pytest", "-q"]
    assert command[4:] == [
        "-k",
        "machine",
        "tests/test_satroot1.py::test_alpha",
        "tests/test_satroot1.py::test_beta",
    ]


def test_repo_local_wrapper_runs_without_editable_install():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "scripts/run_pytest_chunked.py",
            "tests/test_run_pytest_chunked.py",
            "--chunk-size",
            "1",
            "--stop",
            "1",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "all chunks passed" in result.stdout


def test_module_entrypoint_runs_with_repo_pythonpath():
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "satroot_test",
            "tests/test_run_pytest_chunked.py",
            "--chunk-size",
            "1",
            "--stop",
            "1",
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
    assert "all chunks passed" in result.stdout
