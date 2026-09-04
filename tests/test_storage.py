import sqlite3
from pathlib import Path

import pytest

from photobooth.config.settings import StorageConfig
from photobooth.core.session import CaptureSession
from photobooth.storage.database import PhotoDatabase
from photobooth.storage.session_store import SessionStore


def make_session(mode="single") -> CaptureSession:
    return CaptureSession(mode=mode, target_shot_count=1)


# -- PhotoDatabase ----------------------------------------------------------


def test_record_and_read_back_a_result_photo(tmp_path: Path):
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    result_path = tmp_path / "result.jpg"
    result_path.write_bytes(b"fake-jpeg")

    db.record_session(session)
    db.record_photo(session.id, result_path, "result")

    assert db.recent_results() == [result_path]
    db.close()


def test_recent_results_filters_out_deleted_files(tmp_path: Path):
    """The DB is just an index -- the filesystem is the source of truth, so
    a row pointing at a file that no longer exists must be silently
    skipped, not returned as a broken path or raise."""
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    missing_path = tmp_path / "gone.jpg"  # never written to disk

    db.record_session(session)
    db.record_photo(session.id, missing_path, "result")

    assert db.recent_results() == []
    db.close()


def test_recent_results_respects_limit_and_ordering(tmp_path: Path):
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    db.record_session(session)

    paths = []
    for i in range(5):
        p = tmp_path / f"result_{i}.jpg"
        p.write_bytes(b"x")
        db.record_photo(session.id, p, "result")
        paths.append(p)

    results = db.recent_results(limit=3)
    assert len(results) == 3
    # most-recently-inserted first
    assert results[0] == paths[-1]
    db.close()


def test_photo_kind_constraint_rejects_invalid_kind(tmp_path: Path):
    """Regression guard for the schema's CHECK (kind IN ('shot', 'result'))
    -- confirms the constraint is actually enforced, not just documented."""
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    db.record_session(session)

    with pytest.raises(sqlite3.IntegrityError):
        db.record_photo(session.id, tmp_path / "x.jpg", "not-a-real-kind")
    db.close()


def test_all_results_returns_every_result_newest_first(tmp_path: Path):
    """Backs the Gallery screen -- unlike recent_results, this must return
    everything on record, not just a capped window for the idle slideshow."""
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    db.record_session(session)

    paths = []
    for i in range(40):  # comfortably past recent_results' default cap of 30
        p = tmp_path / f"result_{i}.jpg"
        p.write_bytes(b"x")
        db.record_photo(session.id, p, "result")
        paths.append(p)

    results = db.all_results()
    assert len(results) == 40
    assert results[0] == paths[-1]  # newest first
    assert results[-1] == paths[0]
    db.close()


def test_all_results_filters_out_deleted_files(tmp_path: Path):
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    missing_path = tmp_path / "gone.jpg"

    db.record_session(session)
    db.record_photo(session.id, missing_path, "result")

    assert db.all_results() == []
    db.close()


def test_all_results_excludes_individual_shots(tmp_path: Path):
    db = PhotoDatabase(tmp_path / "photobooth.sqlite3")
    session = make_session()
    shot_path = tmp_path / "shot.jpg"
    shot_path.write_bytes(b"x")
    result_path = tmp_path / "result.jpg"
    result_path.write_bytes(b"x")

    db.record_session(session)
    db.record_photo(session.id, shot_path, "shot")
    db.record_photo(session.id, result_path, "result")

    assert db.all_results() == [result_path]
    db.close()


def test_database_survives_close_and_reopen(tmp_path: Path):
    db_path = tmp_path / "photobooth.sqlite3"
    db = PhotoDatabase(db_path)
    session = make_session()
    result_path = tmp_path / "result.jpg"
    result_path.write_bytes(b"x")
    db.record_session(session)
    db.record_photo(session.id, result_path, "result")
    db.close()

    reopened = PhotoDatabase(db_path)
    assert reopened.recent_results() == [result_path]
    reopened.close()


# -- SessionStore -------------------------------------------------------


def test_shot_path_and_result_path_are_distinct_and_predictable(tmp_path: Path):
    store = SessionStore(tmp_path, StorageConfig(basedir="photos", basename="booth"))
    session = make_session()

    shot0 = store.shot_path(session, 0, "jpg")
    shot1 = store.shot_path(session, 1, "jpg")
    result = store.result_path(session, "jpg")

    assert shot0 != shot1 != result
    assert shot0.name == f"booth_{session.id}_00.jpg"
    assert result.name == f"booth_{session.id}.jpg"
    # basedir is treated as a strftime pattern under the photos root
    assert shot0.parent == tmp_path / "photos"


def test_write_creates_parent_dirs_and_returns_the_path(tmp_path: Path):
    store = SessionStore(tmp_path, StorageConfig())
    target = tmp_path / "nested" / "dir" / "file.bin"

    result = store.write(target, b"hello")

    assert result == target
    assert target.read_bytes() == b"hello"


def test_keep_individual_shots_reflects_config(tmp_path: Path):
    store = SessionStore(tmp_path, StorageConfig(keep_pictures=False))
    assert store.keep_individual_shots is False
