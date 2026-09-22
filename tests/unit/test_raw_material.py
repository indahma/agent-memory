"""Archived sessions remain intact while recall searches Memory only."""

import pytest
from agent_memory.core.recall import Recall


@pytest.fixture
def with_raw(store):
    store.record(
        abstract="Watches nature documentaries", type="preference",
        name="nature-documentaries",
    )
    store.archive.append_session(
        "session-alpha", "user: The aquarium ticket was 42 dollars.\n"
    )
    store.sync_index()
    return store


def test_raw_corpus_is_not_a_recall_surface(with_raw):
    assert Recall(with_raw).recall("aquarium ticket 42 dollars") == []


def test_raw_survives_rebuild_without_being_indexed(with_raw):
    path = with_raw.layout.sessions / "session-alpha.jsonl"
    before = path.read_bytes()
    with_raw.rebuild_index()
    assert path.read_bytes() == before
    assert Recall(with_raw).recall("aquarium ticket 42 dollars") == []


def test_explicit_limit_expands_memory_candidates(with_raw):
    for index in range(with_raw.config.recall.default_limit + 2):
        with_raw.record(
            abstract=f"Nature documentary note {index} about aquarium visits",
            type="fact", name=f"documentary-note-{index}",
        )
    query = "nature documentary aquarium"
    small = Recall(with_raw).recall(query, limit=3)
    large = Recall(with_raw).recall(query, limit=20)
    assert len(small) == 3
    assert len(large) > len(small)
    assert all(hit.source == "memory" for hit in large)
