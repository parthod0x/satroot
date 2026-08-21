"""Pin the conformance vector corpus to the reference implementation.

Every vector must check out against the engine, and the checked-in
corpus must be exactly what the generator produces — so a kernel change
that shifts any state hash, or a hand-edited vector, fails loudly here.
"""

import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = REPO_ROOT / "vectors"


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConformanceVectorTest(unittest.TestCase):
    def test_all_vectors_pass_against_reference(self):
        runner = _load_script("run_conformance_vectors")
        vector_paths = sorted(VECTORS_DIR.glob("*.json"))
        self.assertGreaterEqual(len(vector_paths), 14)
        for path in vector_paths:
            vector = json.loads(path.read_text(encoding="utf-8"))
            problems = runner.check_vector(vector)
            self.assertEqual(problems, [], f"{vector['name']}: {problems}")

    def test_corpus_matches_generator_output(self):
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in VECTORS_DIR.glob("*.json")
        }
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "generate_conformance_vectors.py")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in VECTORS_DIR.glob("*.json")
        }
        self.assertEqual(before, after, "checked-in vectors differ from generator output")


if __name__ == "__main__":
    unittest.main()
