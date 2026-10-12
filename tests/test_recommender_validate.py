import pytest

from app.recommender import recommend_by_rules, validate_recommendation


@pytest.fixture
def fallback():
    return recommend_by_rules("프린터 고장", "")


def test_valid_values_are_kept(fallback):
    raw = {"type": "인사", "urgency": "높음", "department": "인사팀", "reason": "AI 판단", "method": "api"}
    assert validate_recommendation(raw, fallback) == raw


def test_whitespace_is_trimmed(fallback):
    raw = {"type": " 인사 ", "urgency": "높음\n", "department": "인사팀", "reason": "AI 판단", "method": "api"}
    result = validate_recommendation(raw, fallback)
    assert (result["type"], result["urgency"]) == ("인사", "높음")


def test_unknown_value_is_replaced_and_reported(fallback):
    raw = {"type": "인사", "urgency": "높음", "department": "개발본부", "reason": "AI 판단", "method": "api"}
    result = validate_recommendation(raw, fallback)
    assert result["department"] == fallback["department"]
    assert "담당부서" in result["reason"]
    assert result["type"] == "인사"


@pytest.mark.parametrize("bad", [None, "", 3, ["IT지원"], {"x": 1}])
def test_non_text_values_are_replaced(fallback, bad):
    raw = {"type": bad, "urgency": bad, "department": bad, "reason": "AI 판단"}
    result = validate_recommendation(raw, fallback)
    for key in ("type", "urgency", "department"):
        assert result[key] == fallback[key]


@pytest.mark.parametrize("raw", [None, "문자열 응답", 42, []])
def test_non_dict_response_returns_fallback(fallback, raw):
    assert validate_recommendation(raw, fallback) == fallback


def test_missing_reason_uses_fallback_reason(fallback):
    raw = {"type": "인사", "urgency": "높음", "department": "인사팀", "method": "api"}
    assert validate_recommendation(raw, fallback)["reason"] == fallback["reason"]
