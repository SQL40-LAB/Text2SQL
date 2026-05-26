"""
Text2SQL Streamlit UI

사용자가 자연어로 쿼리 요청을 입력하면 스키마 필터링 → 프롬프트 생성 →
ChatGPT API 호출 → SQL 검증 후 결과를 표시합니다.
"""

import streamlit as st

from src.pipeline import run_text2sql
from src.schema_loader import load_all_schemas, schema_to_text

st.set_page_config(
    page_title="Text2SQL",
    page_icon="🗃️",
    layout="wide",
)

st.title("Text2SQL")
st.caption(
    "자연어 질의를 입력하면 스키마를 필터링해 ChatGPT로 SQL을 생성하고, "
    "파서로 검증한 뒤 결과를 반환합니다."
)

with st.sidebar:
    st.header("설정")
    use_mock = st.checkbox(
        "모의 모드 (API 미호출)",
        value=False,
        help="API 키·결제 한도 없이 스키마 필터링·SQL 검증 흐름만 테스트합니다.",
    )
    st.caption(
        "429 / insufficient_quota 오류는 OpenAI 결제·한도 문제입니다. "
        "당장 테스트할 때는 모의 모드를 켜세요."
    )
    st.divider()
    st.subheader("등록된 스키마 (임시 YAML 3종)")
    try:
        for schema in load_all_schemas():
            with st.expander(schema.get("database", "unknown")):
                st.text(schema_to_text(schema))
    except FileNotFoundError as e:
        st.error(str(e))

col_input, col_info = st.columns([2, 1])

with col_input:
    user_query = st.text_area(
        "만들고 싶은 쿼리를 설명해 주세요",
        height=140,
        placeholder=(
            "예: 2024년에 가입한 고객별 주문 총액을 내림차순으로 10명만 조회해줘"
        ),
    )
    generate = st.button("SQL 생성", type="primary", use_container_width=True)

with col_info:
    st.info(
        "**처리 흐름**\n\n"
        "1. 질의 입력\n"
        "2. 로컬 YAML 스키마 로드\n"
        "3. 키워드 기반 스키마 필터링\n"
        "4. 프롬프트 생성\n"
        "5. ChatGPT API 호출\n"
        "6. SQL 파서 검증\n"
        "7. 결과 표시"
    )

if generate:
    with st.spinner("스키마 필터링 및 SQL 생성 중..."):
        result = run_text2sql(user_query, use_mock=use_mock)

    if result.error and not result.sql:
        st.error("SQL 생성에 실패했습니다")
        st.markdown(result.error)
        if "quota" in result.error.lower() or "한도" in result.error:
            st.info("사이드바에서 **모의 모드**를 켠 뒤 다시 **SQL 생성**을 눌러 보세요.")
    else:
        tab_sql, tab_schema, tab_prompt = st.tabs(
            ["생성된 SQL", "필터링된 스키마", "프롬프트 미리보기"]
        )

        with tab_sql:
            if result.success:
                st.success(result.validation_message)
                st.code(result.sql, language="sql")
            else:
                st.warning(result.validation_message or "검증 실패")
                if result.sql:
                    st.code(result.sql, language="sql")
                if result.error:
                    st.error(result.error)

        with tab_schema:
            st.text(result.filtered_schema_text or "(필터링된 스키마 없음)")

        with tab_prompt:
            st.text(result.prompt_preview or "(프롬프트 없음)")

elif not user_query:
    st.markdown("### 예시 질의")
    examples = [
        "부서별 직원 수와 평균 연봉을 보여줘",
        "지난달 주문 상태가 DELIVERED인 주문 건수와 총 매출",
        "캠페인별 전환 수와 매출 합계를 매출 높은 순으로",
    ]
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state["example"] = ex
    if "example" in st.session_state:
        st.text_area("", value=st.session_state["example"], disabled=True)
