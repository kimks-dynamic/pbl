from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import storage

MAIN = str(Path(__file__).resolve().parent.parent / "app" / "main.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    # 실제 data/requests.db 대신 임시 파일 사용
    monkeypatch.setenv("REQUESTS_DB_PATH", str(tmp_path / "test.db"))
    return AppTest.from_file(MAIN).run()


def test_app_runs_without_error(app):
    assert not app.exception
    assert app.title[0].value == "업무 요청 분류 도우미"


@pytest.mark.parametrize("menu", ["요청 입력", "요청 목록", "대시보드"])
def test_each_menu_opens(app, menu):
    app.sidebar.radio[0].set_value(menu).run()
    assert not app.exception
    assert app.header[0].value == menu


def test_input_page_has_form(app):
    assert app.text_input(key="title").label == "요청 제목"
    assert app.text_area(key="content").label == "요청 내용"
    assert app.button(key="recommend_button").label == "AI 추천 받기"


def fill_and_recommend(app, title="프린터 고장", content="3층 프린터가 안 됩니다"):
    app.text_input(key="title").set_value(title)
    app.text_area(key="content").set_value(content)
    app.button(key="recommend_button").click().run()
    return app


def test_recommend_shows_result(app):
    fill_and_recommend(app)
    assert not app.exception
    values = {m.label: m.value for m in app.metric}
    assert values == {"업무유형": "IT지원", "긴급도": "높음", "담당부서": "IT팀"}
    assert "프린터" in app.info[0].value


def test_save_with_recommended_values(app, tmp_path):
    fill_and_recommend(app)
    app.button(key="save_button").click().run()
    assert not app.exception
    assert "1번 요청을 저장했습니다" in app.success[0].value
    assert app.text_input(key="title").value == ""
    assert app.text_area(key="content").value == ""
    row = storage.list_requests(tmp_path / "test.db")[0]
    assert (row["final_type"], row["final_urgency"], row["final_department"]) == ("IT지원", "높음", "IT팀")


def test_save_with_user_changed_values(app, tmp_path):
    fill_and_recommend(app)
    app.selectbox(key="final_urgency_1").set_value("낮음")
    app.selectbox(key="final_department_1").set_value("총무팀")
    app.button(key="save_button").click().run()
    row = storage.list_requests(tmp_path / "test.db")[0]
    assert row["ai_urgency"] == "높음"
    assert row["final_urgency"] == "낮음"
    assert row["final_department"] == "총무팀"


def test_new_recommendation_resets_dropdowns(app):
    fill_and_recommend(app)
    app.selectbox(key="final_type_1").set_value("인사").run()
    # 사용자가 첫 추천에서 "인사"로 바꿨어도, 새 추천을 받으면 새 추천값(IT지원)으로 돌아와야 한다
    fill_and_recommend(app, "모니터 교체", "시간 날 때 모니터 교체 부탁")
    assert app.selectbox(key="final_type_2").value == "IT지원"
    assert app.selectbox(key="final_urgency_2").value == "낮음"


@pytest.mark.parametrize("title,content", [("", "내용"), ("제목", ""), ("   ", "   ")])
def test_empty_input_shows_warning(app, title, content):
    fill_and_recommend(app, title, content)
    assert not app.exception
    assert "모두 입력해 주세요" in app.warning[0].value
    assert len(app.metric) == 0


def test_changed_text_after_recommend_blocks_save(app):
    fill_and_recommend(app)
    app.text_area(key="content").set_value("다른 내용으로 수정").run()
    assert "다시 눌러 주세요" in app.warning[0].value
    assert "save_button" not in [b.key for b in app.button]


def test_save_failure_shows_error_without_crash(app, monkeypatch):
    fill_and_recommend(app)

    def broken_save(*args, **kwargs):
        raise OSError("disk locked")

    monkeypatch.setattr(storage, "save_request", broken_save)
    app.button(key="save_button").click().run()
    assert not app.exception
    assert "저장하지 못했습니다" in app.error[0].value


def open_menu(app, menu):
    app.sidebar.radio[0].set_value(menu).run()
    return app


def test_list_page_empty_message(app):
    open_menu(app, "요청 목록")
    assert "아직 저장된 요청이 없습니다" in app.info[0].value


def test_list_page_shows_saved_and_filters(app):
    fill_and_recommend(app)
    app.button(key="save_button").click().run()
    fill_and_recommend(app, "연차 신청", "다음 주 연차 문의")
    app.button(key="save_button").click().run()

    open_menu(app, "요청 목록")
    assert not app.exception
    assert len(app.dataframe[0].value) == 2
    app.multiselect(key="filter_type").set_value(["인사"]).run()
    df = app.dataframe[0].value
    assert list(df["제목"]) == ["연차 신청"]
    assert "전체 2건 중 1건" in app.caption[0].value


def save_sample(app, title, content):
    fill_and_recommend(app, title, content)
    app.button(key="save_button").click().run()


def test_dashboard_empty_message(app):
    open_menu(app, "대시보드")
    assert "아직 저장된 요청이 없습니다" in app.info[0].value


def test_dashboard_total_count(app):
    save_sample(app, "프린터 고장", "3층 프린터가 안 됩니다")
    save_sample(app, "연차 신청", "다음 주 연차 문의")
    open_menu(app, "대시보드")
    assert not app.exception
    assert app.metric[0].label == "전체 요청"
    assert app.metric[0].value == "2건"


def test_dashboard_shows_three_charts(app):
    save_sample(app, "프린터 고장", "3층 프린터가 안 됩니다")
    open_menu(app, "대시보드")
    assert not app.exception
    assert [h.value for h in app.subheader] == ["업무유형별", "긴급도별", "담당부서별"]
    assert len(app.get("vega_lite_chart")) == 3


def test_dashboard_period_filter(app):
    save_sample(app, "프린터 고장", "3층 프린터가 안 됩니다")
    open_menu(app, "대시보드")
    app.segmented_control(key="period").set_value("오늘").run()
    assert not app.exception
    assert app.metric[0].label == "오늘 요청"
    assert app.metric[0].value == "1건"


def test_dashboard_period_deselected_means_all(app):
    save_sample(app, "프린터 고장", "3층 프린터가 안 됩니다")
    open_menu(app, "대시보드")
    app.segmented_control(key="period").set_value(None).run()
    assert not app.exception
    assert app.metric[0].label == "전체 요청"
