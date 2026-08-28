"""Historical `jcs-n` vectors, pinned so they cannot drift.

`jcs-n` was withdrawn in draft-mih-sokolov-scitt-payload-binding-02
(2026-08-24), which registers plain `jcs` in its place. These vectors record
an implementation of the -01 text; they are not an interoperability
contribution and are not offered to anyone.

They are kept, and pinned, because the implementation still ships `jcs_n` and
a silent change to what it computes would be worse than deleting it.
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


def test_the_scope_vector_records_both_readings_and_which_one_won():
    """-01 left exclusion scope open; -02 section 4.1 settles it.

    The vector must carry both candidate readings, not just the one this
    implementation chose, or the ambiguity it documents is invisible. The
    reading -02 made normative is the one that was chosen here - which is
    worth recording precisely because it was a guess at the time.
    """
    unsettled = [v for v in CORPUS["vectors"] if not v["settled_by_01_text"]]
    assert [v["name"] for v in unsettled] == ["exclusion-scope-resolved-in-02"]

    readings = unsettled[0]["readings"]
    assert readings["top_level_member_names"]["specified_by_02"] is True
    assert readings["recursive_member_names"]["specified_by_02"] is False
    # The two readings must actually differ, or the vector shows nothing.
    assert readings["top_level_member_names"]["digest"] != readings[
        "recursive_member_names"
    ]["digest"]


def test_the_corpus_declares_itself_historical():
    """Nobody should mistake these for current interoperability vectors."""
    assert "HISTORICAL" in CORPUS["status"]
    assert "withdrawn" in CORPUS["algorithm"]


def test_the_array_element_vector_keeps_the_emptied_object():
    """RFC 8259: members live in objects, elements live in arrays."""
    vector = next(
        v for v in CORPUS["vectors"] if v["name"] == "emptied-object-inside-an-array"
    )
    assert vector["cases"][0]["after_exclusion_and_normalisation"] == {"a": [{}]}
