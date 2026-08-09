"""
Text2SQL Streamlit UI

사용자가 자연어로 쿼리 요청을 입력하면 스키마 필터링 → 프롬프트 생성 →
ChatGPT API 호출 → SQL 검증 → (선택) MariaDB 조회 결과를 표시합니다.
"""

import streamlit as st

from src.config import QUERY_PAGE_SIZE, SQL_DIALECT
from src.keyword_filter import format_query_with_highlighted_tokens
from src.pipeline import run_text2sql
from src.progress_bar import display_pipeline_progress
from src.streamlit_ui import apply_ui_customization
from src.sql_runner import (
    dataframe_to_excel_bytes,
    paginate_dataframe,
    run_query_from_generated_sql,
)

st.set_page_config(
    page_title="Text2SQL",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_ui_customization()

st.title("Text2SQL")
st.caption(
    "자연어 질의를 입력하면 스키마를 필터링해 ChatGPT로 SQL을 생성하고, "
    "파서로 검증한 뒤 결과를 반환합니다."
)

user_query = st.text_area(
    "만들고 싶은 쿼리를 설명해 주세요",
    height=140,
    placeholder="예: 부서별 사원 수와 평균 월급여를 보여줘",
)

# [기능: DB 계정 입력] 조회 시 .env의 USER/PASSWORD 대신 화면 입력값을 사용
cred_col1, cred_col2 = st.columns(2)
with cred_col1:
    db_user = st.text_input(
        "DB 사용자 ID",
        placeholder="예: root",
        key="db_user_input",
    )
with cred_col2:
    db_password = st.text_input(
        "DB 비밀번호",
        type="password",
        placeholder="비밀번호 입력",
        key="db_password_input",
    )

generate = st.button("SQL 생성", type="primary", use_container_width=False)
progress_placeholder = st.empty()


def render_query_result_section() -> None:
    """
    [기능: DB 조회 결과 UI]
    생성된 SQL과 스키마 미리보기 사이에 MariaDB 조회 결과를 그리드로 표시합니다.
    - 페이지당 최대 QUERY_PAGE_SIZE(기본 100)건
    - 우측 상단 Excel 다운로드 버튼
    """
    df = st.session_state.get("query_result_df")
    query_error = st.session_state.get("query_result_error")
    executed_sql = st.session_state.get("query_executed_sql", "")

    st.divider()
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.subheader("DB 조회 결과")
    with header_right:
        # [기능: Excel 추출] 결과가 있을 때만 다운로드 버튼 표시
        if df is not None and not df.empty:
            excel_bytes = dataframe_to_excel_bytes(df)
            st.download_button(
                label="Excel 추출",
                data=excel_bytes,
                file_name="query_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    if query_error:
        st.error(query_error)
        if executed_sql:
            with st.expander("실행 시도 SQL"):
                st.code(executed_sql, language="sql")
        return

    if df is None:
        st.info("조회 결과가 없습니다.")
        return

    if df.empty:
        st.info("조회 결과가 0건입니다.")
        if executed_sql:
            with st.expander("실행된 SQL"):
                st.code(executed_sql, language="sql")
        return

    # [기능: 페이징] 한 페이지에 최대 100건 표시
    total_rows = len(df)
    total_pages = max(1, (total_rows + QUERY_PAGE_SIZE - 1) // QUERY_PAGE_SIZE)
    page = st.session_state.get("query_result_page", 1)
    page = max(1, min(int(page), total_pages))

    page_df, total_pages, total_rows = paginate_dataframe(
        df, page, QUERY_PAGE_SIZE
    )

    st.caption(
        f"총 {total_rows}건 · {page}/{total_pages} 페이지 "
        f"(페이지당 최대 {QUERY_PAGE_SIZE}건)"
    )
    # [기능: 그리드 표시]
    st.dataframe(page_df, use_container_width=True, hide_index=True)

    nav_prev, nav_info, nav_next = st.columns([1, 2, 1])
    with nav_prev:
        if st.button("이전", disabled=page <= 1, use_container_width=True):
            st.session_state["query_result_page"] = page - 1
            st.rerun()
    with nav_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.4rem;'>{page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with nav_next:
        if st.button("다음", disabled=page >= total_pages, use_container_width=True):
            st.session_state["query_result_page"] = page + 1
            st.rerun()

    if executed_sql:
        with st.expander("실행된 SQL (MariaDB)"):
            st.code(executed_sql, language="sql")


def render_result_panels(result) -> None:
    """생성된 SQL · DB 조회 · 스키마/프롬프트 미리보기를 순서대로 표시합니다."""
    st.subheader("생성된 SQL")
    if result.success:
        st.success(result.validation_message)
        st.code(result.sql, language="sql")
    else:
        st.warning(result.validation_message or "검증 실패")
        if result.sql:
            st.code(result.sql, language="sql")
        if result.error:
            st.error(result.error)

    # [기능: 생성 SQL → MariaDB 조회 결과] (스키마 미리보기 위)
    if result.sql:
        render_query_result_section()

    st.divider()

    col_schema, col_prompt = st.columns(2, gap="large")

    with col_schema:
        st.markdown("#### 필터링된 스키마")
        with st.container(border=True):
            schema_text = result.filtered_schema_text or "(필터링된 스키마 없음)"
            st.code(schema_text, language="text", line_numbers=True)

    with col_prompt:
        st.markdown("#### 프롬프트 미리보기")
        with st.container(border=True):
            prompt_text = result.prompt_preview or "(프롬프트 없음)"
            st.code(prompt_text, language="markdown", line_numbers=True)


if generate:
    def _update_progress(completed_count: int) -> None:
        with progress_placeholder.container():
            display_pipeline_progress(completed_count)

    result = run_text2sql(user_query, on_progress=_update_progress)
    # [기능: 결과 세션 보관] 페이징·엑셀 버튼 클릭 후에도 결과가 유지되도록 저장
    st.session_state["last_result"] = result
    st.session_state["query_result_page"] = 1

    # [기능: MariaDB 조회] SQL이 있으면 화면에서 입력한 ID/PW로 접속해 실행
    if result.sql and not result.no_matching_tables:
        if not db_user.strip():
            st.session_state["query_result_df"] = None
            st.session_state["query_result_error"] = (
                "DB 조회를 위해 사용자 ID를 입력해 주세요."
            )
            st.session_state["query_executed_sql"] = ""
        else:
            query_result = run_query_from_generated_sql(
                result.sql,
                db_user=db_user,
                db_password=db_password,
                source_dialect=SQL_DIALECT,
            )
            st.session_state["query_result_df"] = query_result.dataframe
            st.session_state["query_result_error"] = query_result.error
            st.session_state["query_executed_sql"] = query_result.executed_sql
    else:
        st.session_state["query_result_df"] = None
        st.session_state["query_result_error"] = None
        st.session_state["query_executed_sql"] = ""

# 페이징/다운로드로 인한 rerun 시에도 마지막 결과 표시
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    if result.no_matching_tables:
        st.warning(result.error)
        st.markdown("#### 추출된 매칭 키워드")
        with st.container(border=True):
            if result.filter_tokens:
                highlighted = format_query_with_highlighted_tokens(
                    user_query or "", result.filter_tokens
                )
                st.markdown(highlighted, unsafe_allow_html=True)
                st.caption(
                    "노란색으로 표시된 단어가 스키마 매칭에 사용되었습니다: "
                    + ", ".join(result.filter_tokens)
                )
            else:
                st.info(
                    "질의에서 스키마 매칭용 키워드를 추출하지 못했습니다. "
                    "(불용어·조사만 포함된 경우)"
                )
        st.divider()
        st.markdown("#### 필터링된 스키마")
        with st.container(border=True):
            st.info("질의와 일치하는 테이블이 없어 스키마를 추출하지 못했습니다.")
    elif result.error and not result.sql:
        st.error("SQL 생성에 실패했습니다")
        st.markdown(result.error)
    else:
        render_result_panels(result)

elif not user_query:
    st.markdown("### 예시 질의")
    examples = [
        "부서별 사원 수와 평균 월급여를 보여줘",
        "2024년에 입사한 사원 목록을 입사일자 순으로",
        "급여월별 성과급 합계를 급여월 내림차순으로",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state["example"] = ex
    if "example" in st.session_state:
        st.text_area(
            "선택된 예시 질의",
            value=st.session_state["example"],
            disabled=True,
            label_visibility="collapsed",
        )
