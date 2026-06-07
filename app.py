"""
Text2SQL Streamlit UI

사용자가 자연어로 쿼리 요청을 입력하면 스키마 필터링 → 프롬프트 생성 →
ChatGPT API 호출 → SQL 검증 후 결과를 표시합니다.
"""

import streamlit as st

from src.pipeline import run_text2sql

st.set_page_config(
    page_title="Text2SQL",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
generate = st.button("SQL 생성", type="primary", use_container_width=False)

if generate:
    with st.spinner("스키마 필터링 및 SQL 생성 중..."):
        result = run_text2sql(user_query)

    if result.no_matching_tables:
        st.warning(result.error)
        st.divider()
        st.markdown("#### 필터링된 스키마")
        with st.container(border=True):
            st.info("질의와 일치하는 테이블이 없어 스키마를 추출하지 못했습니다.")
    elif result.error and not result.sql:
        st.error("SQL 생성에 실패했습니다")
        st.markdown(result.error)
    else:
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
        st.text_area("", value=st.session_state["example"], disabled=True)
