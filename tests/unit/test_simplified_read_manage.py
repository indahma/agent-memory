import pytest
from agent_memory.cli.main import main
from agent_memory.core.context import build
from agent_memory.core.errors import ValidationError
from agent_memory.core.recall import Recall
from agent_memory.core.record import MemoryRecord
from agent_memory.core.store import Store
from agent_memory.mcp.tools import dispatch


def test_memory_only_recall_and_explicit_limit(store):
    store.archive.append_session("old", ["user: orphaned raw keyword"])
    store.sync_index()
    assert Recall(store).recall("orphaned raw keyword", limit=20) == []
    with pytest.raises(TypeError):
        Recall(store).recall("orphaned", deep=True)
    with pytest.raises(TypeError):
        build(store, "orphaned", deep=True)


def test_validity_is_derived_from_interval():
    record = MemoryRecord(
        name="example", abstract="Example", type="decision", author="agent",
        created="2026-01-01T00:00:00Z", updated="2026-01-01T00:00:00Z",
    )
    assert record.is_active()
    record.invalid_at = "2026-02-01T00:00:00Z"
    assert not record.is_active()
    assert "status:" not in record.to_text()


def test_legacy_status_and_index_load_without_store_reset(store):
    written = store.record(type="fact", name="legacy", abstract="Legacy fact")
    path = written.path
    path.write_text(
        path.read_text().replace("invalid_at: null", "status: invalid\ninvalid_at: null")
    )
    with store._database.connect() as connection:
        connection.execute("ALTER TABLE records ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    reopened = Store(store.root)
    reopened.rebuild_index()
    assert reopened.find("legacy").invalid_at == written.updated
    with reopened._database.connect() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(records)")}
        assert "status" not in columns


def test_stale_manage_rewrite_is_rejected(store):
    store.record(type="fact", name="shared", abstract="Original")
    stale = store.find("shared")
    Store(store.root).correct("shared", body="Updated by another writer")
    stale.abstract = "Stale replacement"
    with pytest.raises(ValidationError, match="changed since it was read"):
        store.write(stale)
    assert store.find("shared").body == "Updated by another writer"


def test_projection_failure_restores_canonical_memory(store, monkeypatch):
    written = store.record(type="fact", name="rollback", abstract="Before")
    before = written.path.read_bytes()
    project = store._project
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("projection failed")
        return project()

    monkeypatch.setattr(store, "_project", fail_once)
    with pytest.raises(RuntimeError, match="projection failed"):
        store.correct("rollback", abstract="After")
    assert written.path.read_bytes() == before
    assert Recall(store).recall("After") == []


def test_adapters_reject_deep_and_share_direct_management(store, capsys):
    store.record(type="fact", name="old", abstract="Old aquarium price")
    store.record(type="fact", name="new", abstract="New aquarium price")
    with pytest.raises(ValidationError):
        dispatch(store, "memory_recall", {"query": "aquarium", "deep": True})
    with pytest.raises(SystemExit) as rejected:
        main(["--store", str(store.root), "recall", "aquarium", "--deep"])
    assert rejected.value.code == 2
    capsys.readouterr()
    assert main(["--store", str(store.root), "supersede", "old", "new"]) == 0
    assert [hit.name for hit in Recall(store).recall("aquarium")] == ["new"]
    assert dispatch(store, "memory_delete", {"name": "new"})["invalid_at"]
    assert Recall(store).recall("aquarium") == []


def test_direct_merge_preserves_history_and_provenance(store, clock):
    store.archive.append_session("merge-source", ["user: Two related aquarium plans."])
    left = store.record(
        type="fact", name="left-plan", abstract="First aquarium plan",
        provenance=["sessions/merge-source#0-0"],
    )
    right = store.record(type="fact", name="right-plan", abstract="Second aquarium plan")
    before = clock.timestamp()
    clock.advance(days=1)
    result = dispatch(store, "memory_merge", {
        "names": [left.name, right.name], "name": "combined-plan",
        "abstract": "Combined aquarium plan", "body": "Both plans together",
    })
    assert result["name"] == "combined-plan"
    assert {hit.name for hit in Recall(store).recall("aquarium")} == {"combined-plan"}
    assert {hit.name for hit in Recall(store).recall("aquarium", as_of=before)} == {
        left.name, right.name,
    }
    assert store.trace("combined-plan")[0].index == 0
    read = dispatch(store, "memory_read", {"name": "combined-plan"})
    assert read["provenance"] == ["sessions/merge-source#0-0"]
    traced = dispatch(store, "memory_trace", {"name": "combined-plan"})
    assert traced["messages"][0]["index"] == 0
    store.rebuild_index()
    assert {hit.name for hit in Recall(store).recall("aquarium")} == {"combined-plan"}


def test_merge_rejects_missing_source_without_partial_write(store):
    first = store.record(type="fact", name="first", abstract="First plan")
    before = first.path.read_bytes()
    with pytest.raises(ValidationError):
        store.merge(["first", "missing"], "Combined", "Body")
    assert first.path.read_bytes() == before
    assert store.find("first-merged") is None


def test_failed_merge_rolls_back_all_files(store, monkeypatch):
    first = store.record(type="fact", name="first", abstract="First plan")
    second = store.record(type="fact", name="second", abstract="Second plan")
    before = {record.name: record.path.read_bytes() for record in (first, second)}
    project = store._project
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("index failed")
        return project()

    monkeypatch.setattr(store, "_project", fail_once)
    with pytest.raises(RuntimeError, match="index failed"):
        store.merge(["first", "second"], "Combined plan", "Combined body")
    assert {name: store.find(name).path.read_bytes() for name in before} == before
    assert store.find("first-merged") is None


def test_legacy_raw_config_knobs_load_as_ignored_compatibility(store):
    config = store.root / "config.toml"
    config.write_text(config.read_text().replace(
        "[recall]", "[recall]\ndeep_limit_multiplier = 2\nraw_enabled = true\n"
        "raw_relevance_factor = 0.4\n"
    ))
    reopened = Store(store.root)
    assert reopened.config.recall.default_limit == store.config.recall.default_limit
