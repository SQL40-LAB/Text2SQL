"""
Text2SQL Streamlit UI (Gemini-style chat)

자연어 질의 → 스키마 필터링 → 프롬프트/SQL 생성 → 검증 → MariaDB 조회를
채팅 메시지 레이아웃으로 표시합니다.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from src.chat_ui import (
    ASSISTANT_AVATAR,
    USER_AVATAR,
    apply_gemini_chat_styles,
    build_filter_query,
    clear_chat,
    init_chat_state,
    persist_active_chat,
    render_db_credentials_sidebar,
    render_empty_hero,
    render_sidebar_brand,
    render_sidebar_chat_history,
    scroll_chat_to_bottom,
    stream_text,
)
from src.config import QUERY_PAGE_SIZE, SQL_DIALECT
from src.keyword_filter import format_query_with_highlighted_tokens
from src.pipeline import Text2SQLResult, run_text2sql
from src.progress_bar import display_pipeline_progress
from src.streamlit_ui import apply_ui_customization
from src.sql_runner import (
    dataframe_to_excel_bytes,
    is_select_query,
    paginate_dataframe,
    run_query_from_generated_sql,
)

st.set_page_config(
    page_title="Text2SQL",
    page_icon="🗃️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# [기능: UI 커스터마이징] 메뉴 정리 + Gemini 스타일 CSS
apply_ui_customization()
apply_gemini_chat_styles()
init_chat_state()


def render_sidebar() -> tuple[str, str]:
    """
    [기능: Gemini 사이드바]
    프로젝트 브랜드 · 새 채팅 · DB 로그인 · 최근 질의 미리보기
    (열고 닫기는 Streamlit 기본 사이드바 토글 사용)
    """
    with st.sidebar:
        render_sidebar_brand()

        if st.button("✦  새 채팅", use_container_width=True, key="btn_new_chat"):
            clear_chat()
            st.rerun()

        st.markdown("---")
        db_user, db_password = render_db_credentials_sidebar()
        st.markdown("---")
        render_sidebar_chat_history()

    return db_user, db_password


def render_query_result_block(
    *,
    df: Optional[pd.DataFrame],
    error: Optional[str],
    executed_sql: str,
    message_index: int,
    execution_skipped: bool = False,
) -> None:
    """[기능: DB 조회 결과] 그리드 · 페이징 · Excel 추출."""
    st.markdown('<p class="gemini-section-title">DB 조회 결과</p>', unsafe_allow_html=True)

    if execution_skipped:
        st.info(
            error
            or "SELECT(또는 WITH)가 아닌 문은 실행하지 않습니다. 생성된 SQL만 표시합니다."
        )
        return

    header_left, header_right = st.columns([4, 1])
    with header_right:
        if df is not None and not df.empty:
            excel_bytes = dataframe_to_excel_bytes(df)
            st.download_button(
                label="Excel 추출",
                data=excel_bytes,
                file_name=f"query_result_{message_index}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"excel_{message_index}",
            )

    if error:
        st.error(error)
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

    page_key = f"query_result_page_{message_index}"
    total_rows = len(df)
    total_pages = max(1, (total_rows + QUERY_PAGE_SIZE - 1) // QUERY_PAGE_SIZE)
    page = max(1, min(int(st.session_state.get(page_key, 1)), total_pages))
    page_df, total_pages, total_rows = paginate_dataframe(df, page, QUERY_PAGE_SIZE)

    st.caption(
        f"총 {total_rows}건 · {page}/{total_pages} 페이지 "
        f"(페이지당 최대 {QUERY_PAGE_SIZE}건)"
    )
    st.dataframe(page_df, use_container_width=True, hide_index=True)

    nav_prev, nav_info, nav_next = st.columns([1, 2, 1])
    with nav_prev:
        if st.button("이전", disabled=page <= 1, use_container_width=True, key=f"prev_{message_index}"):
            st.session_state[page_key] = page - 1
            st.rerun()
    with nav_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.4rem;'>{page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with nav_next:
        if st.button(
            "다음",
            disabled=page >= total_pages,
            use_container_width=True,
            key=f"next_{message_index}",
        ):
            st.session_state[page_key] = page + 1
            st.rerun()

    if executed_sql:
        with st.expander("실행된 SQL (MariaDB)"):
            st.code(executed_sql, language="sql")


def render_assistant_payload(
    payload: Dict[str, Any],
    message_index: int,
    *,
    db_user: str = "",
    db_password: str = "",
) -> None:
    """assistant 메시지의 구조화 결과(SQL/조회/스키마)를 렌더링합니다."""
    kind = payload.get("kind")

    if kind == "no_match":
        st.warning(payload.get("error", "관련 테이블을 찾을 수 없습니다."))
        tokens = payload.get("filter_tokens") or []
        user_query = payload.get("user_query", "")
        st.markdown("**추출된 매칭 키워드**")
        if tokens:
            highlighted = format_query_with_highlighted_tokens(user_query, tokens)
            st.markdown(highlighted, unsafe_allow_html=True)
            st.caption("노란색 단어가 스키마 매칭에 사용됨: " + ", ".join(tokens))
        else:
            st.info("스키마 매칭용 키워드를 추출하지 못했습니다.")
        return

    if kind == "error":
        st.error(payload.get("error", "오류가 발생했습니다."))
        return

    if kind == "result":
        result_data = payload.get("result") or {}
        sql = result_data.get("sql", "")
        success = result_data.get("success", False)
        validation_message = result_data.get("validation_message", "")
        error = result_data.get("error")

        edit_flag_key = f"sql_editing_{message_index}"
        edit_text_key = f"sql_edit_text_{message_index}"
        editing = bool(st.session_state.get(edit_flag_key, False))

        title_col, action_col = st.columns([4, 1])
        with title_col:
            st.markdown(
                '<p class="gemini-section-title">생성된 SQL</p>',
                unsafe_allow_html=True,
            )
        with action_col:
            if sql:
                if not editing:
                    if st.button(
                        "수정",
                        key=f"sql_edit_btn_{message_index}",
                        use_container_width=True,
                    ):
                        st.session_state[edit_flag_key] = True
                        st.session_state[edit_text_key] = sql
                        st.rerun()
                else:
                    if st.button(
                        "완료",
                        key=f"sql_done_btn_{message_index}",
                        type="primary",
                        use_container_width=True,
                    ):
                        _apply_edited_sql_and_rerun(
                            message_index=message_index,
                            edited_sql=str(
                                st.session_state.get(edit_text_key, sql) or ""
                            ).strip(),
                            db_user=db_user,
                            db_password=db_password,
                        )

        if success:
            st.success(validation_message)
        else:
            st.warning(validation_message or "검증 실패")
            if error:
                st.error(error)

        if sql:
            if editing:
                if edit_text_key not in st.session_state:
                    st.session_state[edit_text_key] = sql
                st.text_area(
                    "SQL 수정",
                    key=edit_text_key,
                    height=220,
                    label_visibility="collapsed",
                )
            else:
                st.code(sql, language="sql")

        render_query_result_block(
            df=payload.get("query_df"),
            error=payload.get("query_error"),
            executed_sql=payload.get("executed_sql", ""),
            message_index=message_index,
            execution_skipped=bool(payload.get("execution_skipped")),
        )

        st.markdown("**필터링된 스키마**")
        st.code(
            result_data.get("filtered_schema_text") or "(없음)",
            language="text",
            line_numbers=True,
        )


def _apply_edited_sql_and_rerun(
    *,
    message_index: int,
    edited_sql: str,
    db_user: str,
    db_password: str,
) -> None:
    """수정된 SQL을 저장하고, SELECT인 경우만 재조회합니다."""
    messages = st.session_state.messages
    if message_index < 0 or message_index >= len(messages):
        return

    message = messages[message_index]
    payload = message.get("payload") or {}
    if payload.get("kind") != "result":
        return

    result_data = payload.get("result") or {}
    result_data["sql"] = edited_sql
    payload["result"] = result_data

    if not edited_sql:
        payload["execution_skipped"] = True
        payload["query_error"] = "실행할 SQL이 비어 있습니다."
        payload["query_df"] = None
        payload["executed_sql"] = ""
    elif not is_select_query(edited_sql):
        payload["execution_skipped"] = True
        payload["query_error"] = (
            "SELECT(또는 WITH)가 아닌 문은 실행하지 않습니다. "
            "생성된 SQL만 표시합니다."
        )
        payload["query_df"] = None
        payload["executed_sql"] = ""
    elif not (db_user or "").strip():
        payload["execution_skipped"] = False
        payload["query_error"] = (
            "DB 조회를 위해 사이드바에서 사용자 ID를 입력해 주세요."
        )
        payload["query_df"] = None
        payload["executed_sql"] = ""
    else:
        query_result = run_query_from_generated_sql(
            edited_sql,
            db_user=db_user,
            db_password=db_password,
            source_dialect=SQL_DIALECT,
        )
        payload["execution_skipped"] = False
        payload["query_error"] = query_result.error
        payload["executed_sql"] = query_result.executed_sql
        payload["query_df"] = (
            None if query_result.error else query_result.dataframe
        )

    message["payload"] = payload
    messages[message_index] = message

    st.session_state[f"sql_editing_{message_index}"] = False
    st.session_state[f"query_result_page_{message_index}"] = 1
    persist_active_chat()
    st.rerun()


def render_messages(*, db_user: str = "", db_password: str = "") -> None:
    """[기능: 대화 렌더링] session_state.messages를 말풍선으로 출력합니다."""
    for idx, message in enumerate(st.session_state.messages):
        role = message.get("role", "assistant")
        avatar = USER_AVATAR if role == "user" else ASSISTANT_AVATAR
        with st.chat_message(role, avatar=avatar):
            content = message.get("content", "")
            if content:
                st.markdown(content)
            payload = message.get("payload")
            if role == "assistant" and payload:
                render_assistant_payload(
                    payload,
                    message_index=idx,
                    db_user=db_user,
                    db_password=db_password,
                )


def serialize_result(result: Text2SQLResult) -> Dict[str, Any]:
    """Text2SQLResult를 session_state에 넣을 수 있는 dict로 변환합니다."""
    return {
        "sql": result.sql,
        "success": result.success,
        "validation_message": result.validation_message,
        "filtered_schema_text": result.filtered_schema_text,
        "prompt_preview": result.prompt_preview,
        "error": result.error,
        "no_matching_tables": result.no_matching_tables,
        "filter_tokens": list(result.filter_tokens or []),
    }


def handle_user_query(user_query: str, db_user: str, db_password: str) -> None:
    """
    [기능: 질의 처리 루프]
    1) 사용자 메시지를 messages에 저장
    2) 누적 질의로 테이블 필터링 + 최신 질의로 SQL 생성
    3) (가능 시) MariaDB 조회
    4) assistant 메시지를 스트리밍 후 payload와 함께 저장
    """
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        # 응답이 처음 시작될 때만 하단으로 스크롤 (생성 중에는 추가 스크롤 없음)
        scroll_chat_to_bottom()
        progress_placeholder = st.empty()

        def _update_progress(completed_count: int) -> None:
            with progress_placeholder.container():
                display_pipeline_progress(completed_count)

        filter_query = build_filter_query(user_query)
        result = run_text2sql(
            user_query,
            on_progress=_update_progress,
            filter_query=filter_query,
        )
        progress_placeholder.empty()

        if result.no_matching_tables:
            summary = (
                "요청하신 내용과 일치하는 테이블을 찾지 못했습니다. "
                "부서, 사원, 급여처럼 스키마에 있는 키워드를 포함해 다시 물어봐 주세요."
            )
            st.write_stream(stream_text(summary))
            time.sleep(0.05)
            payload = {
                "kind": "no_match",
                "error": result.error,
                "filter_tokens": list(result.filter_tokens or []),
                "user_query": user_query,
            }
            render_assistant_payload(
                payload,
                message_index=len(st.session_state.messages),
                db_user=db_user,
                db_password=db_password,
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": summary, "payload": payload}
            )
            persist_active_chat()
            return

        if result.error and not result.sql:
            summary = "SQL 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
            st.write_stream(stream_text(summary))
            payload = {"kind": "error", "error": result.error}
            render_assistant_payload(
                payload,
                message_index=len(st.session_state.messages),
                db_user=db_user,
                db_password=db_password,
            )
            st.session_state.messages.append(
                {"role": "assistant", "content": summary, "payload": payload}
            )
            persist_active_chat()
            return

        summary = (
            "요청하신 내용으로 SQL을 생성했습니다. "
            "아래에서 생성된 SQL, DB 조회 결과, 필터링된 스키마를 확인해 주세요."
        )
        st.write_stream(stream_text(summary))

        query_df = None
        query_error = None
        executed_sql = ""
        execution_skipped = False
        if result.sql:
            if not is_select_query(result.sql):
                execution_skipped = True
                query_error = (
                    "SELECT(또는 WITH)가 아닌 문은 실행하지 않습니다. "
                    "생성된 SQL만 표시합니다."
                )
            elif not db_user.strip():
                query_error = "DB 조회를 위해 사이드바에서 사용자 ID를 입력해 주세요."
            else:
                query_result = run_query_from_generated_sql(
                    result.sql,
                    db_user=db_user,
                    db_password=db_password,
                    source_dialect=SQL_DIALECT,
                )
                query_df = (
                    None if query_result.error else query_result.dataframe
                )
                query_error = query_result.error
                executed_sql = query_result.executed_sql

        payload = {
            "kind": "result",
            "result": serialize_result(result),
            "query_df": query_df,
            "query_error": query_error,
            "executed_sql": executed_sql,
            "execution_skipped": execution_skipped,
        }
        msg_index = len(st.session_state.messages)
        render_assistant_payload(
            payload,
            message_index=msg_index,
            db_user=db_user,
            db_password=db_password,
        )
        st.session_state.messages.append(
            {"role": "assistant", "content": summary, "payload": payload}
        )
        persist_active_chat()


# ---------- 화면 구성 ----------
db_user, db_password = render_sidebar()

if not st.session_state.messages:
    render_empty_hero()
else:
    render_messages(db_user=db_user, db_password=db_password)

prompt = st.chat_input("만들고 싶은 쿼리를 설명해 주세요")
if prompt:
    handle_user_query(prompt.strip(), db_user, db_password)
    st.rerun()

# 최근 채팅 복원 등, 명시적으로 요청된 경우에만 하단 스크롤
if st.session_state.get("scroll_to_bottom"):
    st.session_state.scroll_to_bottom = False
    scroll_chat_to_bottom()
