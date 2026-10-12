"""업무 요청 내용을 보고 업무유형, 긴급도, 담당부서를 추천하는 기능."""
from app import config


def _find_keywords(text, keywords):
    return [kw for kw in keywords if kw in text]


def recommend_by_rules(title, content):
    """키워드 규칙으로 추천한다. 외부로 아무것도 보내지 않는다."""
    text = f"{title} {content}".lower()

    # 업무유형: 키워드가 가장 많이 맞은 유형 (같으면 설정 파일 순서가 앞선 유형)
    best_type, best_hits = config.DEFAULT_TYPE, []
    for name, info in config.TASK_TYPES.items():
        hits = _find_keywords(text, info["keywords"])
        if len(hits) > len(best_hits):
            best_type, best_hits = name, hits

    # 긴급도: 높은 단계부터 확인해서 처음 맞은 단계
    urgency, urgency_hits = config.DEFAULT_URGENCY, []
    for level in config.URGENCY_LEVELS:
        hits = _find_keywords(text, config.URGENCY_KEYWORDS.get(level, []))
        if hits:
            urgency, urgency_hits = level, hits
            break

    department = config.TASK_TYPES[best_type]["department"]

    if best_hits:
        type_reason = f"'{', '.join(best_hits[:3])}' 단어가 있어 {best_type}"
    else:
        type_reason = f"맞는 키워드가 없어 {best_type}"
    if urgency_hits:
        urgency_reason = f"'{', '.join(urgency_hits[:3])}' 표현이 있어 긴급도 {urgency}"
    else:
        urgency_reason = f"긴급 표현이 없어 긴급도 {urgency}"

    return {
        "type": best_type,
        "urgency": urgency,
        "department": department,
        "reason": f"{type_reason}, {urgency_reason}으로 추천했습니다.",
        "method": "rule",
    }


def validate_recommendation(raw, fallback):
    """추천 결과의 각 값이 설정 목록 안에 있는지 확인한다.

    목록 밖의 값이나 빈 값은 fallback(규칙 기반 추천)의 값으로 바꾸고, 이유에 그 사실을 적는다.
    """
    allowed = {
        "type": config.TASK_TYPES,
        "urgency": config.URGENCY_LEVELS,
        "department": config.DEPARTMENTS,
    }
    labels = {"type": "업무유형", "urgency": "긴급도", "department": "담당부서"}
    if not isinstance(raw, dict):
        return dict(fallback)

    result, replaced = {}, []
    for key, values in allowed.items():
        value = raw.get(key)
        value = value.strip() if isinstance(value, str) else None
        if value in values:
            result[key] = value
        else:
            result[key] = fallback[key]
            replaced.append(labels[key])

    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = fallback["reason"]
    if replaced:
        reason += f" (목록에 없는 {', '.join(replaced)} 값은 규칙 기반 추천으로 바꿨습니다.)"
    result["reason"] = reason
    result["method"] = raw.get("method") or fallback["method"]
    return result


def recommend(title, content, ai_func=None):
    """화면에서 쓰는 추천 진입점.

    ai_func: 외부 AI 추천 함수. 사용 승인 전이므로 기본값은 None이고, 이때는 규칙 기반만 쓴다.
    ai_func가 오류를 내거나 이상한 값을 돌려주면 규칙 기반 추천으로 대신한다.
    """
    fallback = recommend_by_rules(title, content)
    if ai_func is None:
        return fallback
    try:
        raw = ai_func(title, content)
    except Exception:
        result = dict(fallback)
        result["reason"] += " (AI 추천 중 오류가 나서 규칙 기반으로 추천했습니다.)"
        return result
    return validate_recommendation(raw, fallback)
