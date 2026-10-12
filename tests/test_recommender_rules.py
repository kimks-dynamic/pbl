import pytest

from app import config
from app.recommender import recommend_by_rules


@pytest.mark.parametrize(
    "title,content,expected_type,expected_department",
    [
        ("프린터 고장", "3층 프린터가 안 됩니다", "IT지원", "IT팀"),
        ("연차 신청", "다음 주 연차 사용 방법 문의", "인사", "인사팀"),
        ("회의실 에어컨", "에어컨이 너무 시끄러워요", "총무·시설", "총무팀"),
        ("경비 정산", "법인카드 경비 정산 요청드립니다", "회계·구매", "재무팀"),
        ("안녕하세요", "점심 메뉴 추천 부탁", "기타", "경영지원팀"),
    ],
)
def test_type_and_department(title, content, expected_type, expected_department):
    result = recommend_by_rules(title, content)
    assert result["type"] == expected_type
    assert result["department"] == expected_department


@pytest.mark.parametrize(
    "content,expected",
    [
        ("서버가 먹통입니다. 긴급!", "높음"),
        ("인터넷이 안돼요", "높음"),
        ("접속이 되지 않습니다", "높음"),
        ("시간 날 때 모니터 교체 부탁드려요", "낮음"),
        ("모니터 교체 부탁드려요", "보통"),
    ],
)
def test_urgency(content, expected):
    assert recommend_by_rules("", content)["urgency"] == expected


def test_high_urgency_wins_over_low():
    # "문의"(낮음)와 "긴급"(높음)이 함께 있으면 높음
    assert recommend_by_rules("긴급 문의", "")["urgency"] == "높음"


def test_case_insensitive_english_keyword():
    assert recommend_by_rules("VPN 접속", "")["type"] == "IT지원"


def test_more_keyword_hits_wins():
    # 총무(고장) 1개 vs IT(컴퓨터, 모니터) 2개
    assert recommend_by_rules("컴퓨터 모니터 고장", "")["type"] == "IT지원"


def test_result_values_are_always_in_config_lists():
    for text in ["", "아무 말", "프린터 긴급", "연차 천천히"]:
        r = recommend_by_rules(text, text)
        assert r["type"] in config.TASK_TYPES
        assert r["urgency"] in config.URGENCY_LEVELS
        assert r["department"] in config.DEPARTMENTS
        assert r["method"] == "rule"
        assert r["reason"]


def test_reason_mentions_matched_keyword():
    assert "프린터" in recommend_by_rules("프린터 고장", "")["reason"]
