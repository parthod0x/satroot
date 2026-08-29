"""Pin SPEC.md's normative claims to what the reference actually does.

SPEC.md section 7 described the state commitment as being taken over
`{balances, supply, sequence, prev_event_id}`. The real commitment covers
thirteen members and names `last_event_id`, so anyone implementing the
specification faithfully computed a different hash for every ledger and
failed all twelve accept-vectors.

Nothing caught it because nothing compared the two. Both implementations
agreed with each other and with the corpus; only the document they were
supposed to be implementations *of* was wrong - which is the failure the
conformance corpus cannot detect by construction, since it is generated
from the code rather than from the text.

These tests read SPEC.md and compare it against the reference directly.
"""

import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import satroot1 as sr  # noqa: E402

SPEC = (REPO_ROOT / "SPEC.md").read_text(encoding="utf-8")
VECTORS_DIR = REPO_ROOT / "vectors"


def documented_commitment_members():
    """The members SPEC.md section 7 lists in its commitment table."""
    section = SPEC.split("## 7. State commitment", 1)[1].split("## 8.", 1)[0]
    table = section.split("thirteen members:", 1)[1]
    members = []
    for line in table.splitlines():
        match = re.match(r"^\|\s*`([a-z_]+)`\s*\|", line)
        if match:
            members.append(match.group(1))
    return members


class SpecMatchesReferenceTest(unittest.TestCase):
    def test_state_commitment_members_are_exactly_as_documented(self):
        genesis = json.loads(
            (VECTORS_DIR / "valid-genesis-only-demo.json").read_text(encoding="utf-8")
        )
        state = sr.replay(genesis["events"], verifier=sr.demo_signature_verifier)
        self.assertEqual(
            documented_commitment_members(),
            list(state.commitment_snapshot().keys()),
            "SPEC.md section 7 no longer describes the real state commitment",
        )

    def test_the_documented_construction_reproduces_the_corpus(self):
        """Build the hash from SPEC.md's text, not from the reference method."""
        for path in sorted(VECTORS_DIR.glob("valid-*.json")):
            vector = json.loads(path.read_text(encoding="utf-8"))
            state = sr.replay(vector["events"], verifier=verifier_for(vector["scheme"]))

            snapshot = state.commitment_snapshot()
            # canonical JSON exactly as SPEC.md section 2.6 defines it
            canonical = json.dumps(
                snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

            self.assertEqual(
                "sha256:" + digest,
                vector["expect"]["final_state_hash"],
                f"{path.name}: SPEC.md's construction does not reproduce the vector",
            )

    def test_canonical_json_is_documented_as_implemented(self):
        section = SPEC.split("### 2.6 Canonical JSON", 1)[1].split("### 2.7", 1)[0]
        for claim in ("sort_keys=True", 'separators=(",", ":")', "ensure_ascii=False"):
            self.assertIn(claim, section)
        # And that the described behaviour is what the function does.
        probe = {"b": 1, "a": {"d": 2, "c": "é"}}
        self.assertEqual(sr.canonical_json(probe), '{"a":{"c":"é","d":2},"b":1}')

    def test_event_id_prefix_and_exclusions_are_documented(self):
        section = SPEC.split("### 2.7 Event identity", 1)[1].split("## 3.", 1)[0]
        self.assertIn("sha256:", section)
        self.assertIn("state_hash", section)
        self.assertIn("signature", section)

        event = {"action": "x", "event_id": "stale", "state_hash": "stale"}
        expected = "sha256:" + hashlib.sha256(
            sr.canonical_json({"action": "x"}).encode("utf-8")
        ).hexdigest()
        self.assertEqual(sr.event_id(event), expected)
        self.assertEqual(sr.signing_payload({**event, "signature": "s"}), '{"action":"x"}')


def verifier_for(scheme):
    if scheme == "demo":
        return sr.demo_signature_verifier
    if scheme == "ed25519":
        return sr.make_ed25519_verifier(
            sr.derive_ed25519_public_keys(
                {"issuer-key": "11" * 32, "alice-key": "22" * 32}
            )
        )
    if scheme == "hmac-sha256":
        return sr.make_hmac_sha256_verifier(
            {"issuer-key": "33" * 32, "alice-key": "44" * 32}
        )
    raise ValueError(scheme)


if __name__ == "__main__":
    unittest.main()
