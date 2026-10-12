from app.recommender import recommend, recommend_by_rules

TITLE, CONTENT = "프린터 고장", "3층 프린터가 안 됩니다"


def test_without_ai_uses_rules():
    assert recommend(TITLE, CONTENT) == recommend_by_rules(TITLE, CONTENT)


def test_ai_result_is_used_when_valid():
    def fake_ai(title, content):
        return {"type": "총무·시설", "urgency": "낮음", "department": "총무팀", "reason": "가짜 AI", "method": "api"}

    result = recommend(TITLE, CONTENT, ai_func=fake_ai)
    assert result["type"] == "총무·시설"
    assert result["method"] == "api"


def test_ai_error_falls_back_to_rules():
    def broken_ai(title, content):
        raise ConnectionError("네트워크 오류")

    result = recommend(TITLE, CONTENT, ai_func=broken_ai)
    rules = recommend_by_rules(TITLE, CONTENT)
    assert result["type"] == rules["type"]
    assert result["method"] == "rule"
    assert "오류" in result["reason"]


def test_ai_invalid_response_falls_back_to_rules():
    result = recommend(TITLE, CONTENT, ai_func=lambda t, c: "형식이 틀린 응답")
    assert result == recommend_by_rules(TITLE, CONTENT)
