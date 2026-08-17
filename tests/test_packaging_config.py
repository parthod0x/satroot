from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = pytest.importorskip("tomli")


def test_pyproject_includes_all_top_level_runtime_modules():
    repo_root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    py_modules = pyproject["tool"]["setuptools"]["py-modules"]

    assert "satroot1" in py_modules
    assert "satroot_collection_lint" in py_modules
    assert "satroot_test" in py_modules
    assert "satroot_stable_profile_smoke" in py_modules
    assert "satroot_machine_profile_smoke" in py_modules
    assert "satroot_receipt_profile_smoke" in py_modules
    assert "satroot_identity_profile_smoke" in py_modules
    assert "satroot_license_profile_smoke" in py_modules
