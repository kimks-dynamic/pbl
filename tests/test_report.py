from app import report


def make_row(i, type_, urgency, department, created_at="2026-10-12 10:00:00"):
    return {
        "id": i, "created_at": created_at, "title": f"제목{i}", "content": "내용",
        "ai_type": type_, "ai_urgency": urgency, "ai_department": department, "ai_reason": "", "ai_method": "rule",
        "final_type": type_, "final_urgency": urgency, "final_department": department,
    }


ROWS = [
    make_row(1, "IT지원", "높음", "IT팀"),
    make_row(2, "IT지원", "보통", "IT팀"),
    make_row(3, "인사", "낮음", "인사팀"),
]


def test_to_dataframe_uses_korean_columns_and_final_values():
    df = report.to_dataframe(ROWS)
    assert list(df.columns) == ["번호", "저장 시각", "제목", "내용", "업무유형", "긴급도", "담당부서"]
    assert len(df) == 3


def test_to_dataframe_empty():
    df = report.to_dataframe([])
    assert df.empty
    assert "업무유형" in df.columns


def test_filter_none_selected_returns_all():
    assert len(report.filter_df(report.to_dataframe(ROWS))) == 3


def test_filter_by_type_and_urgency():
    df = report.to_dataframe(ROWS)
    assert list(report.filter_df(df, types=["IT지원"])["번호"]) == [1, 2]
    assert list(report.filter_df(df, types=["IT지원"], urgencies=["보통"])["번호"]) == [2]
    assert list(report.filter_df(df, departments=["인사팀", "IT팀"])["번호"]) == [1, 2, 3]


def test_count_by_keeps_order_and_zero():
    df = report.to_dataframe(ROWS)
    counts = report.count_by(df, "긴급도", ["높음", "보통", "낮음"])
    assert list(counts["긴급도"]) == ["높음", "보통", "낮음"]
    assert list(counts["건수"]) == [1, 1, 1]
    counts = report.count_by(df, "업무유형", ["IT지원", "인사", "기타"])
    assert list(counts["건수"]) == [2, 1, 0]


def test_count_by_empty():
    counts = report.count_by(report.to_dataframe([]), "긴급도", ["높음", "보통", "낮음"])
    assert list(counts["건수"]) == [0, 0, 0]


def test_filter_period():
    from datetime import datetime

    rows = [
        make_row(1, "IT지원", "높음", "IT팀", "2026-10-12 09:00:00"),  # 월요일(오늘)
        make_row(2, "IT지원", "높음", "IT팀", "2026-10-11 18:00:00"),  # 지난주 일요일
        make_row(3, "IT지원", "높음", "IT팀", "2026-10-01 10:00:00"),
    ]
    df = report.to_dataframe(rows)
    monday = datetime(2026, 10, 12, 15, 0)
    assert list(report.filter_period(df, "오늘", monday)["번호"]) == [1]
    assert list(report.filter_period(df, "이번 주", monday)["번호"]) == [1]
    assert list(report.filter_period(df, "전체", monday)["번호"]) == [1, 2, 3]

    thursday = datetime(2026, 10, 15, 9, 0)
    assert list(report.filter_period(df, "오늘", thursday)["번호"]) == []
    assert list(report.filter_period(df, "이번 주", thursday)["번호"]) == [1]


def test_filter_period_empty():
    assert report.filter_period(report.to_dataframe([]), "오늘").empty
