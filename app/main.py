import os
import sys
from pathlib import Path

import streamlit as st

# "streamlit run app/main.py"로 실행해도 app 패키지를 불러올 수 있게 프로젝트 폴더를 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, report, storage  # noqa: E402
from app.recommender import recommend  # noqa: E402

# 테스트에서는 환경변수로 임시 저장 파일을 지정한다
DB_PATH = os.environ.get("REQUESTS_DB_PATH", storage.DEFAULT_DB_PATH)

MENU_INPUT = "요청 입력"
MENU_LIST = "요청 목록"
MENU_DASHBOARD = "대시보드"

# 차트 색 (건수 막대는 한 가지 색만 사용)
CHART_COLOR = "#2a78d6"

METHOD_LABELS = {"rule": "규칙 기반 (키워드)", "api": "외부 AI"}


def page_input():
    st.header(MENU_INPUT)
    st.text_input("요청 제목", key="title", placeholder="예: 3층 프린터 고장")
    st.text_area("요청 내용", key="content", height=150,
                 placeholder="예: 3층 복합기가 오늘 아침부터 인쇄가 안 됩니다. 급히 확인 부탁드립니다.")
    if st.button("AI 추천 받기", type="primary", key="recommend_button"):
        title, content = st.session_state.title.strip(), st.session_state.content.strip()
        if not title or not content:
            st.session_state.pop("recommendation", None)
            st.warning("요청 제목과 내용을 모두 입력해 주세요.")
        else:
            st.session_state.recommendation = recommend(title, content)
            st.session_state.recommended_text = (title, content)
            st.session_state.rec_count = st.session_state.get("rec_count", 0) + 1

    if "saved_message" in st.session_state:
        st.success(st.session_state.pop("saved_message"))
    if "error_message" in st.session_state:
        st.error(st.session_state.pop("error_message"))

    rec = st.session_state.get("recommendation")
    if not rec:
        return

    current_text = (st.session_state.title.strip(), st.session_state.content.strip())
    if current_text != st.session_state.recommended_text:
        st.warning("추천을 받은 뒤 요청 내용이 바뀌었습니다. 'AI 추천 받기'를 다시 눌러 주세요.")
        return

    st.subheader("추천 결과")
    col1, col2, col3 = st.columns(3)
    col1.metric("업무유형", rec["type"])
    col2.metric("긴급도", rec["urgency"])
    col3.metric("담당부서", rec["department"])
    st.info(f"추천 이유: {rec['reason']}")
    st.caption(f"추천 방식: {METHOD_LABELS.get(rec['method'], rec['method'])}")

    st.subheader("확인 후 저장")
    st.write("추천이 맞지 않으면 바꾼 뒤 저장하세요.")
    # 새 추천을 받을 때마다 드롭다운이 새 추천값으로 초기화되도록 키에 번호를 붙인다
    n = st.session_state.rec_count
    col1, col2, col3 = st.columns(3)
    col1.selectbox("업무유형", list(config.TASK_TYPES), key=f"final_type_{n}",
                   index=list(config.TASK_TYPES).index(rec["type"]))
    col2.selectbox("긴급도", config.URGENCY_LEVELS, key=f"final_urgency_{n}",
                   index=config.URGENCY_LEVELS.index(rec["urgency"]))
    col3.selectbox("담당부서", config.DEPARTMENTS, key=f"final_department_{n}",
                   index=config.DEPARTMENTS.index(rec["department"]))
    st.button("저장", key="save_button", on_click=save_current_request)


def save_current_request():
    """저장 버튼을 누르면 실행된다. 저장 후 입력칸과 추천 결과를 비운다."""
    s = st.session_state
    n = s.rec_count
    final = {
        "type": s[f"final_type_{n}"],
        "urgency": s[f"final_urgency_{n}"],
        "department": s[f"final_department_{n}"],
    }
    try:
        new_id = storage.save_request(s.title, s.content, s.recommendation, final, DB_PATH)
    except ValueError as e:
        s.error_message = str(e)
        return
    except Exception:
        s.error_message = "저장하지 못했습니다. 저장 파일(data/requests.db)이 다른 프로그램에서 열려 있는지 확인한 뒤 다시 시도해 주세요."
        return
    s.saved_message = f"{new_id}번 요청을 저장했습니다."
    s.title = ""
    s.content = ""
    del s.recommendation


def page_list():
    st.header(MENU_LIST)
    df = report.to_dataframe(storage.list_requests(DB_PATH))
    if df.empty:
        st.info("아직 저장된 요청이 없습니다. '요청 입력' 메뉴에서 요청을 저장해 보세요.")
        return

    st.write("필터를 비워 두면 전체가 보입니다.")
    col1, col2, col3 = st.columns(3)
    types = col1.multiselect("업무유형", list(config.TASK_TYPES), key="filter_type")
    urgencies = col2.multiselect("긴급도", config.URGENCY_LEVELS, key="filter_urgency")
    departments = col3.multiselect("담당부서", config.DEPARTMENTS, key="filter_department")

    filtered = report.filter_df(df, types, urgencies, departments)
    st.caption(f"전체 {len(df)}건 중 {len(filtered)}건")
    st.dataframe(filtered, hide_index=True)


def page_dashboard():
    st.header(MENU_DASHBOARD)
    df = report.to_dataframe(storage.list_requests(DB_PATH))
    if df.empty:
        st.info("아직 저장된 요청이 없습니다. '요청 입력' 메뉴에서 요청을 저장해 보세요.")
        return

    # 선택을 해제하면 None이 되므로 전체로 본다
    period = st.segmented_control("기간", report.PERIODS, default="전체", key="period") or "전체"
    df = report.filter_period(df, period)
    if df.empty:
        st.info(f"{period}에 저장된 요청이 없습니다.")
        return

    st.metric(f"{period} 요청" if period != "전체" else "전체 요청", f"{len(df)}건")

    charts = [
        ("업무유형별", "업무유형", list(config.TASK_TYPES)),
        ("긴급도별", "긴급도", config.URGENCY_LEVELS),
        ("담당부서별", "담당부서", config.DEPARTMENTS),
    ]
    for col, (title, column, order) in zip(st.columns(len(charts)), charts):
        with col:
            st.subheader(title)
            st.bar_chart(report.count_by(df, column, order), x=column, y="건수",
                         x_label="", y_label="건수", horizontal=True, sort=False, color=CHART_COLOR)


st.set_page_config(page_title="업무 요청 분류 도우미", page_icon="📋", layout="wide")
st.title("업무 요청 분류 도우미")

menu = st.sidebar.radio("메뉴", [MENU_INPUT, MENU_LIST, MENU_DASHBOARD])
{MENU_INPUT: page_input, MENU_LIST: page_list, MENU_DASHBOARD: page_dashboard}[menu]()
