"""The published `jcs-n` vectors, pinned so they cannot drift.

`vectors/jcs_n/vectors.json` is offered to the authors of
draft-mih-sokolov-scitt-payload-binding-01, which publishes none of its own.
If these digests change, either the implementation changed or the vectors are
wrong - and an offered vector that quietly changed would be worse than no
vector at all.
"""

import json
import pathlib

import pytest

from satroot_jcs import jcs_n

VECTORS_PATH = pathlib.Path(__file__).parents[1] / "vectors" / "jcs_n" / "vectors.json"
CORPUS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "vector", CORPUS["vectors"], ids=[v["name"] for v in CORPUS["vectors"]]
)
def test_vector_reproduces(vector):
    for case in vector["cases"]:
        assert jcs_n(case["input"], vector["exclusion_set"]) == case["digest"]


def test_collapse_vector_really_collapses():
    """Absent, null, empty array and empty object share one digest."""
    vector = next(
        v for v in CORPUS["vectors"] if v["name"] == "absent-null-empty-collapse"
    )
    assert vector["all_inputs_share_one_digest"] is True
    assert len(vector["cases"]) == 4


def test_the_open_question_is_marked_as_such():
    """Exactly one vector records a reading the draft does not settle.

    If a future draft revision settles exclusion scope, this vector is the one
    to revisit - and it must stay flagged until then, so nobody mistakes our
    choice for the specification.
    """
    unsettled = [v for v in CORPUS["vectors"] if not v["settled_by_the_draft"]]
    assert [v["name"] for v in unsettled] == ["exclusion-scope-is-unspecified"]


def test_the_array_element_vector_keeps_the_emptied_object():
    """RFC 8259: members live in objects, elements live in arrays."""
    vector = next(
        v for v in CORPUS["vectors"] if v["name"] == "emptied-object-inside-an-array"
    )
    assert vector["cases"][0]["after_exclusion_and_normalisation"] == {"a": [{}]}
