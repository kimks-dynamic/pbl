"""저장된 요청을 표로 바꾸고 필터링·집계하는 기능. 목록과 대시보드는 확정값(final_*) 기준이다."""
from datetime import datetime, timedelta

import pandas as pd

COLUMNS = {
    "id": "번호",
    "created_at": "저장 시각",
    "title": "제목",
    "content": "내용",
    "final_type": "업무유형",
    "final_urgency": "긴급도",
    "final_department": "담당부서",
}


def to_dataframe(rows):
    """저장된 요청 목록(dict)을 화면에 보여 줄 표로 바꾼다."""
    df = pd.DataFrame(rows, columns=list(COLUMNS))
    return df.rename(columns=COLUMNS)


def filter_df(df, types=None, urgencies=None, departments=None):
    """선택한 값만 남긴다. 아무것도 선택하지 않은 항목은 전체를 보여 준다."""
    for column, selected in (("업무유형", types), ("긴급도", urgencies), ("담당부서", departments)):
        if selected:
            df = df[df[column].isin(selected)]
    return df


def count_by(df, column, order):
    """항목별 건수를 설정 순서대로 센다. 0건인 항목도 포함한다."""
    counts = df[column].value_counts().reindex(order, fill_value=0)
    return counts.rename_axis(column).reset_index(name="건수")


PERIODS = ["오늘", "이번 주", "전체"]


def filter_period(df, period, now=None):
    """기간으로 거른다. '이번 주'는 이번 주 월요일 0시부터."""
    if period == "전체" or df.empty:
        return df
    now = now or datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "이번 주":
        start -= timedelta(days=start.weekday())
    created = pd.to_datetime(df["저장 시각"])
    return df[created >= start]
