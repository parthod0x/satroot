"""Pin the standalone vector runner that external implementers use.

`vectors/run.py` and `vectors/EXPECTED.txt` are what a second implementer
touches first, so the failure that matters here is silent rot: a
regenerated corpus leaving EXPECTED.txt stale, or a runner that reports
success whatever the adapter prints.

The negative test is the load-bearing one. A conformance runner that
cannot fail is worse than none, because it manufactures agreement - which
is the exact defect class this corpus exists to catch.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = REPO_ROOT / "vectors"
RUNNER = VECTORS_DIR / "run.py"
EXPECTED = VECTORS_DIR / "EXPECTED.txt"
EXAMPLE_ADAPTER = VECTORS_DIR / "example_adapter.py"


def run_runner(*args):
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        capture_output=True,
        text=True,
        cwd=str(VECTORS_DIR),
    )


class VectorRunnerTest(unittest.TestCase):
    def test_expected_file_is_in_sync_with_the_corpus(self):
        """Regenerating from the vectors must reproduce EXPECTED.txt exactly."""
        before = EXPECTED.read_bytes()
        result = run_runner("--write-expected")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            before,
            EXPECTED.read_bytes(),
            "EXPECTED.txt is stale - regenerate with "
            "`python vectors/run.py --write-expected`",
        )

    def test_expected_file_uses_lf_endings(self):
        """CRLF here would make every line of an operator's first diff differ."""
        self.assertNotIn(b"\r\n", EXPECTED.read_bytes())

    def test_one_expected_line_per_vector(self):
        vector_count = len(list(VECTORS_DIR.glob("*.json")))
        lines = [ln for ln in EXPECTED.read_text(encoding="utf-8").splitlines() if ln]
        self.assertEqual(len(lines), vector_count)
        self.assertGreaterEqual(vector_count, 33)

    def test_reference_mode_agrees_with_declared_expectations(self):
        result = run_runner()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 failures", result.stdout)

    def test_example_adapter_satisfies_the_documented_contract(self):
        """The worked example must actually work, or it teaches the wrong shape."""
        result = run_runner("--impl", f'"{sys.executable}" "{EXAMPLE_ADAPTER}"')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 failures", result.stdout)

    def test_emit_output_is_byte_identical_to_expected(self):
        result = run_runner(
            "--impl", f'"{sys.executable}" "{EXAMPLE_ADAPTER}"', "--emit"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED.read_text(encoding="utf-8"))

    def test_a_wrong_adapter_actually_fails(self):
        """The runner must detect a mismatch, not rubber-stamp any output."""
        result = run_runner("--impl", f'"{sys.executable}" -c "print(\'REJECT\')"')
        self.assertNotEqual(result.returncode, 0, "runner passed a lying adapter")
        self.assertIn("FAIL", result.stdout)

    def test_a_silent_adapter_is_reported_not_ignored(self):
        result = run_runner("--impl", f'"{sys.executable}" -c "pass"')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("printed nothing to stdout", result.stdout)


if __name__ == "__main__":
    unittest.main()
