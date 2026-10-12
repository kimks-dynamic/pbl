import sqlite3

import pytest

from app import storage

REC = {"type": "IT지원", "urgency": "높음", "department": "IT팀", "reason": "키워드: 프린터", "method": "rule"}
FINAL = {"type": "IT지원", "urgency": "보통", "department": "IT팀"}


@pytest.fixture
def db(tmp_path):
    return tmp_path / "data" / "test.db"


def test_init_db_creates_table_and_is_repeatable(db):
    storage.init_db(db)
    storage.init_db(db)
    conn = sqlite3.connect(db)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(requests)")]
    conn.close()
    assert cols[:4] == ["id", "created_at", "title", "content"]
    assert len(cols) == 12


def test_save_and_list_roundtrip(db):
    new_id = storage.save_request("  프린터 고장 ", "3층 프린터가 안 됩니다", REC, FINAL, db)
    rows = storage.list_requests(db)
    assert new_id == 1
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "프린터 고장"  # 앞뒤 공백 제거
    assert row["ai_urgency"] == "높음"
    assert row["final_urgency"] == "보통"
    assert row["ai_method"] == "rule"
    assert row["created_at"]


def test_list_returns_newest_first(db):
    storage.save_request("첫번째", "내용", REC, FINAL, db)
    storage.save_request("두번째", "내용", REC, FINAL, db)
    assert [r["title"] for r in storage.list_requests(db)] == ["두번째", "첫번째"]


def test_list_empty_db(db):
    assert storage.list_requests(db) == []


@pytest.mark.parametrize("title,content", [("", "내용"), ("제목", "   ")])
def test_save_rejects_empty_title_or_content(db, title, content):
    with pytest.raises(ValueError):
        storage.save_request(title, content, REC, FINAL, db)
    assert storage.list_requests(db) == []


def test_save_rejects_missing_final_value(db):
    with pytest.raises(ValueError):
        storage.save_request("제목", "내용", REC, {**FINAL, "department": ""}, db)


def test_save_allows_empty_recommendation(db):
    storage.save_request("제목", "내용", {}, FINAL, db)
    assert storage.list_requests(db)[0]["ai_type"] is None


def test_data_persists_after_reconnect(db):
    storage.save_request("제목", "내용", REC, FINAL, db)
    # 새로 불러와도 남아 있어야 한다 (앱을 껐다 켠 상황)
    assert len(storage.list_requests(db)) == 1
    assert db.exists()
