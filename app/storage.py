"""업무 요청을 SQLite 파일에 저장하고 불러오는 기능."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "requests.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS requests (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT NOT NULL,
    title            TEXT NOT NULL,
    content          TEXT NOT NULL,
    ai_type          TEXT,
    ai_urgency       TEXT,
    ai_department    TEXT,
    ai_reason        TEXT,
    ai_method        TEXT,
    final_type       TEXT NOT NULL,
    final_urgency    TEXT NOT NULL,
    final_department TEXT NOT NULL
)
"""


@contextmanager
def connect(db_path=DEFAULT_DB_PATH):
    """연결을 열고, 끝나면 저장(commit)한 뒤 반드시 닫는다. (Windows 파일 잠김 방지)"""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(db_path=DEFAULT_DB_PATH):
    """저장 파일과 테이블이 없으면 만든다. 이미 있으면 그대로 둔다."""
    with connect(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)


def save_request(title, content, recommendation, final, db_path=DEFAULT_DB_PATH):
    """요청 1건을 저장하고 저장된 번호(id)를 돌려준다.

    recommendation: AI 추천 결과 (type, urgency, department, reason, method)
    final: 사용자가 확정한 값 (type, urgency, department)
    """
    title, content = title.strip(), content.strip()
    if not title or not content:
        raise ValueError("요청 제목과 내용을 모두 입력해 주세요.")
    for key in ("type", "urgency", "department"):
        if not final.get(key):
            raise ValueError("업무유형, 긴급도, 담당부서를 모두 선택해 주세요.")

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    init_db(db_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO requests (
                created_at, title, content,
                ai_type, ai_urgency, ai_department, ai_reason, ai_method,
                final_type, final_urgency, final_department
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at, title, content,
                recommendation.get("type"), recommendation.get("urgency"),
                recommendation.get("department"), recommendation.get("reason"),
                recommendation.get("method"),
                final["type"], final["urgency"], final["department"],
            ),
        )
        return cur.lastrowid


def list_requests(db_path=DEFAULT_DB_PATH):
    """저장된 요청 전체를 최근 순으로 돌려준다. (각 요청은 dict)"""
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]
