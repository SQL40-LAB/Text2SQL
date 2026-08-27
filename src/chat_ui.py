"""Gemini 스타일 채팅 UI 스타일 및 헬퍼."""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional

import streamlit as st

# 아바타 — assets/ Twemoji (없으면 이모지 폴백)
_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_USER_IMG = _ASSETS_DIR / "avatar_user.png"
_ASSISTANT_IMG = _ASSETS_DIR / "avatar_assistant.png"
_USER_SVG = _ASSETS_DIR / "avatar_user.svg"
_ASSISTANT_SVG = _ASSETS_DIR / "avatar_assistant.svg"
USER_AVATAR = (
    str(_USER_IMG)
    if _USER_IMG.is_file()
    else (str(_USER_SVG) if _USER_SVG.is_file() else "👤")
)
ASSISTANT_AVATAR = (
    str(_ASSISTANT_IMG)
    if _ASSISTANT_IMG.is_file()
    else (str(_ASSISTANT_SVG) if _ASSISTANT_SVG.is_file() else "🤖")
)
PROJECT_NAME = "Text2SQL"
PROJECT_ICON = "🗃️"

GEMINI_CHAT_CSS = """
<style>
/* ===== 메인 배경 흰색 통일 ===== */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
section.main,
section[data-testid="stMain"],
.main,
header[data-testid="stHeader"],
[data-testid="stHeader"],
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
.stChatFloatingInputContainer,
[data-testid="stDecoration"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
}

[data-testid="stStatusWidget"] { display: none !important; }
.stAppDeployButton { display: none !important; }
#MainMenu { visibility: hidden !important; display: none !important; }
[data-testid="stMainMenu"] { display: none !important; visibility: hidden !important; }
/* 툴바 전체는 숨기지 않음 — 사이드바 펼치기 버튼이 여기 있을 수 있음 */
div[data-testid="stToolbarActions"] [data-testid="stMainMenu"],
header [data-testid="stMainMenu"] {
    display: none !important;
}

/* ----- Sidebar (Gemini left rail) ----- */
[data-testid="stSidebar"] {
    background: #f0f4f9 !important;
    border-right: 1px solid #e1e5ea !important;
    position: relative !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
    background: #f0f4f9 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    margin-bottom: 0.25rem;
}
section[data-testid="stSidebar"] .block-container,
[data-testid="stSidebarUserContent"] {
    padding-top: 0.15rem !important;
    padding-left: 0.55rem !important;
    padding-right: 0.7rem !important;
}

/* 사이드바 헤더: 접기 버튼을 우측 상단에 정렬 */
[data-testid="stSidebarHeader"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    height: 3rem !important;
    min-height: 3rem !important;
    max-height: 3rem !important;
    padding: 0.45rem 0.15rem 0.25rem 0.55rem !important;
    margin: 0 !important;
    background: transparent !important;
    position: relative !important;
    z-index: 40 !important;
}
[data-testid="stLogoSpacer"] {
    flex: 1 1 auto !important;
    height: 1px !important;
    min-width: 0 !important;
    visibility: hidden !important;
}

/* 접기(◀) 버튼 — 사이드바 우측 끝으로 */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] button,
[data-testid="stSidebarHeader"] [data-testid="baseButton-header"],
[data-testid="stSidebarHeader"] [data-testid="baseButton-headerNoPadding"] {
    position: relative !important;
    top: 0 !important;
    right: 0 !important;
    margin: 0 0 0 auto !important;
    margin-right: -0.15rem !important;
    padding: 0.35rem !important;
    z-index: 50 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transform: translateX(0.35rem) !important;
}

/* 펼치기 화살표 — Streamlit 기본 컨트롤 사용 */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    align-items: center !important;
    top: 0.55rem !important;
    left: 0.55rem !important;
    z-index: 999999 !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}
[data-testid="stHeader"] [data-testid="collapsedControl"],
[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],
[data-testid="stToolbar"] [data-testid="collapsedControl"],
[data-testid="stToolbar"] [data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

/* 브랜드: 헤더와 같은 줄(좌측), 접기 버튼과 겹치지 않게 */
.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.15rem 2.75rem 0.55rem 0.05rem;
    margin: 0;
    position: relative;
    top: -2.65rem;
    z-index: 30;
    width: fit-content;
    max-width: calc(100% - 2.75rem);
    pointer-events: none;
}
.sidebar-brand .brand-icon,
.sidebar-brand .brand-text {
    pointer-events: auto;
}
.sidebar-brand .brand-icon {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: linear-gradient(135deg, #4285f4 0%, #9b72cb 45%, #d96570 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
    color: #fff;
    flex-shrink: 0;
}
.sidebar-brand .brand-text {
    font-size: 1.15rem;
    font-weight: 650;
    letter-spacing: -0.02em;
    color: #1f1f1f;
    line-height: 1.2;
}
.sidebar-section-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #5f6368;
    text-transform: none;
    margin: 0.85rem 0 0.4rem 0.1rem;
}

/* 최근 채팅: 한 줄 + 말줄임 */
section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start !important;
    text-align: left !important;
}
section[data-testid="stSidebar"] .stButton > button p {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: block !important;
    max-width: 100% !important;
    margin: 0 !important;
}

/* ----- Main chat column ----- */
section.main > div {
    padding-left: 0 !important;
    padding-right: 0 !important;
}
.block-container {
    max-width: 860px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 1.25rem !important;
    padding-bottom: 7.5rem !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    background: #ffffff !important;
}

[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
.stChatFloatingInputContainer {
    background: #ffffff !important;
}
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
.stChatFloatingInputContainer {
    max-width: 860px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 1.25rem !important;
    padding-right: 1.25rem !important;
    left: 0 !important;
    right: 0 !important;
    background: #ffffff !important;
}
section[data-testid="stMain"] .block-container,
section.main .block-container {
    max-width: 860px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    background: #ffffff !important;
}
[data-testid="stChatInput"] {
    max-width: 860px !important;
    width: 100% !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-bottom: 0.85rem !important;
    background: #ffffff !important;
}
/* pill 입력창 */
[data-testid="stChatInput"] > div {
    border: 1px solid #dadce0 !important;
    border-radius: 28px !important;
    box-shadow: 0 2px 12px rgba(60, 64, 67, 0.12) !important;
    background: #f0f4f9 !important;
    overflow: hidden !important;
    padding: 0 !important;
    margin: 0 !important;
}
[data-testid="stChatInput"] > div > div {
    background: #f0f4f9 !important;
    border-radius: 28px !important;
    margin: 0 !important;
    padding-left: 1.15rem !important;
    padding-right: 0.5rem !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    border: none !important;
    border-radius: 28px !important;
    box-shadow: none !important;
    caret-color: #1f1f1f;
    padding-left: 0.35rem !important;
    padding-right: 0.75rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
}
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding-left: 0.5rem !important;
}

/* 히어로 */
.gemini-hero {
    text-align: center;
    padding: 3.5rem 0 1.5rem 0;
}
.gemini-hero h1 {
    font-size: 2.15rem;
    font-weight: 650;
    letter-spacing: -0.02em;
    color: #1f1f1f;
    margin-bottom: 0.4rem;
}
.gemini-hero p {
    color: #5f6368;
    font-size: 1rem;
    margin: 0;
}

/* 채팅 아바타 — 모서리만 살짝 둥근 사각 */
[data-testid="stChatMessage"] img,
[data-testid="stChatMessage"] [data-testid="stImage"] img,
[data-testid="stChatAvatar"] img,
[data-testid="stChatMessageAvatarUser"] img,
[data-testid="stChatMessageAvatarAssistant"] img {
    border-radius: 10px !important;
    object-fit: cover !important;
    overflow: hidden !important;
}
[data-testid="stChatMessage"] [data-testid="stChatAvatar"],
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* 채팅 말풍선 */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.45rem 0 0.7rem 0 !important;
    gap: 0.75rem !important;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0.15rem 0.1rem !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
  [data-testid="stChatMessageContent"],
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
  [data-testid="stChatMessageContent"] {
    background: #f0f4f9 !important;
    border-radius: 22px !important;
    padding: 0.85rem 1.1rem !important;
    overflow: hidden !important;
    border: none !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
  [data-testid="stChatMessageContent"] > *,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"])
  [data-testid="stChatMessageContent"] > * {
    background: transparent !important;
}

.gemini-section-title {
    font-size: 0.92rem;
    font-weight: 600;
    color: #3c4043;
    margin: 0.55rem 0 0.5rem 0;
}

div[data-testid="stHtml"] iframe { border: none !important; }
.stElementContainer:has(iframe[height="0"]) {
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
</style>
"""

# 커스텀 펼치기 버튼/플래그 정리 후 Streamlit 기본 동작으로 복귀
SIDEBAR_EXPAND_CLEANUP_SCRIPT = """
<script>
(function () {
  var win = window.parent;
  var doc = win.document;
  var btn = doc.getElementById("gemini-sidebar-expand-btn");
  if (btn && btn.parentNode) btn.parentNode.removeChild(btn);
  win.__geminiSidebarExpandV2 = false;
  win.__geminiSidebarExpandV3 = false;
  win.__geminiSidebarExpandV4 = false;
})();
</script>
"""


def apply_gemini_chat_styles() -> None:
    """Gemini 스타일 CSS를 주입하고, 커스텀 사이드바 펼치기 버튼을 제거합니다."""
    import streamlit.components.v1 as components

    st.markdown(GEMINI_CHAT_CSS, unsafe_allow_html=True)
    components.html(SIDEBAR_EXPAND_CLEANUP_SCRIPT, height=0, width=0, scrolling=False)


SCROLL_TO_BOTTOM_SCRIPT = """
<script>
(function () {
  const doc = window.parent.document;
  const nonce = "__NONCE__";

  function scrollBottom() {
    try {
      // 1) 마지막 채팅 메시지 / 입력창 / 앵커로 이동
      const msgs = doc.querySelectorAll('[data-testid="stChatMessage"]');
      if (msgs.length) {
        msgs[msgs.length - 1].scrollIntoView({ behavior: "auto", block: "end" });
      }
      const input = doc.querySelector('[data-testid="stChatInput"]');
      if (input) {
        input.scrollIntoView({ behavior: "auto", block: "nearest" });
      }
      const anchors = doc.querySelectorAll('[id^="gemini-scroll-anchor-"]');
      const anchor = anchors.length ? anchors[anchors.length - 1] : null;
      if (anchor) {
        anchor.scrollIntoView({ behavior: "auto", block: "end" });
      }

      // 2) overflow 스크롤 컨테이너를 찾아 맨 아래로
      const seeds = [];
      if (msgs.length) seeds.push(msgs[msgs.length - 1]);
      if (input) seeds.push(input);
      if (anchor) seeds.push(anchor);
      seeds.push(doc.body);

      seeds.forEach((seed) => {
        let el = seed;
        while (el && el !== doc.documentElement) {
          try {
            const style = window.parent.getComputedStyle(el);
            const oy = style.overflowY;
            if (
              (oy === "auto" || oy === "scroll" || oy === "overlay") &&
              el.scrollHeight > el.clientHeight + 8
            ) {
              el.scrollTop = el.scrollHeight;
            }
          } catch (e) {}
          el = el.parentElement;
        }
      });

      // 3) 주요 후보 강제 스크롤
      [
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.querySelector('section.main'),
        doc.querySelector('[data-testid="stMain"]'),
        doc.querySelector(".main"),
        doc.scrollingElement,
        doc.documentElement,
        doc.body,
      ].forEach((el) => {
        if (!el) return;
        try {
          el.scrollTop = el.scrollHeight;
        } catch (e) {}
      });

      try {
        window.parent.scrollTo(0, Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight));
      } catch (e) {}
    } catch (e) {}
  }

  // 레이아웃이 잡히기 직전·직후만 1~2회 (생성 중 지속 스크롤 방지)
  scrollBottom();
  setTimeout(scrollBottom, 80);
})();
</script>
"""


def scroll_chat_to_bottom() -> None:
    """채팅 영역을 맨 아래로 한 번 스크롤합니다 (응답 시작 시 전용)."""
    import time

    import streamlit.components.v1 as components

    nonce = str(time.time_ns())
    # 메인 문서에 앵커를 두고, iframe 스크립트가 parent에서 scrollIntoView
    st.markdown(
        f'<div id="gemini-scroll-anchor-{nonce}" style="height:1px;width:1px;"></div>',
        unsafe_allow_html=True,
    )
    components.html(
        SCROLL_TO_BOTTOM_SCRIPT.replace("__NONCE__", nonce),
        height=0,
        width=0,
        scrolling=False,
    )


def request_scroll_to_bottom() -> None:
    """렌더 완료 후 하단 스크롤을 요청합니다."""
    st.session_state.scroll_to_bottom = True


def init_chat_state() -> None:
    """대화 세션 상태를 초기화합니다."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_sessions" not in st.session_state:
        # [{id, title, messages}] — 브라우저 세션에만 임시 보관
        st.session_state.chat_sessions = []
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None
    if "scroll_to_bottom" not in st.session_state:
        st.session_state.scroll_to_bottom = False


def truncate_one_line(text: str, max_chars: int = 24) -> str:
    """한 줄 표시용으로 잘라 ...을 붙입니다."""
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def _first_user_title(messages: list) -> str:
    for m in messages:
        if m.get("role") == "user" and str(m.get("content", "")).strip():
            return str(m.get("content", "")).strip()
    return "새 채팅"


def persist_active_chat() -> None:
    """
    [기능: 세션 임시 저장]
    현재 messages를 chat_sessions에 저장/갱신합니다.
    """
    import uuid

    messages = list(st.session_state.get("messages") or [])
    if not messages:
        return

    title = _first_user_title(messages)
    chat_id = st.session_state.get("active_chat_id")
    sessions: list = st.session_state.chat_sessions

    if chat_id:
        for i, session in enumerate(sessions):
            if session.get("id") == chat_id:
                session["title"] = title
                session["messages"] = messages
                # 최근 사용 순으로 맨 앞
                sessions.insert(0, sessions.pop(i))
                return

    new_id = str(uuid.uuid4())
    st.session_state.active_chat_id = new_id
    sessions.insert(
        0,
        {"id": new_id, "title": title, "messages": messages},
    )


def clear_chat() -> None:
    """[기능: 새 채팅] 현재 대화를 세션에 남기고 새 빈 대화를 엽니다."""
    persist_active_chat()
    st.session_state.messages = []
    st.session_state.active_chat_id = None
    for key in list(st.session_state.keys()):
        if str(key).startswith("query_result_page_"):
            del st.session_state[key]


def load_chat_session(chat_id: str) -> bool:
    """사이드바 '최근'에서 선택한 채팅·결과를 복원합니다."""
    persist_active_chat()
    for session in st.session_state.get("chat_sessions", []):
        if session.get("id") == chat_id:
            st.session_state.messages = list(session.get("messages") or [])
            st.session_state.active_chat_id = chat_id
            request_scroll_to_bottom()
            return True
    return False


def get_user_query_history() -> list[str]:
    """저장된 사용자 질의문 목록만 반환합니다 (테이블 필터링용)."""
    return [
        str(m.get("content", "")).strip()
        for m in st.session_state.get("messages", [])
        if m.get("role") == "user" and str(m.get("content", "")).strip()
    ]


def build_filter_query(latest_query: str) -> str:
    """
    누적 사용자 질의 + 최신 질의를 합쳐 키워드 필터링용 문자열을 만듭니다.
    SQL 생성 요청문 자체는 latest_query를 그대로 씁니다.
    """
    history = get_user_query_history()
    parts = [q for q in history if q]
    if latest_query.strip() and (
        not parts or parts[-1] != latest_query.strip()
    ):
        parts.append(latest_query.strip())
    return " ".join(parts)


def stream_text(text: str, chunk_size: int = 24) -> Generator[str, None, None]:
    """AI 답변 스트리밍용 간단한 텍스트 generator."""
    if not text:
        yield ""
        return
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]


def render_sidebar_brand() -> None:
    """사이드바 상단 프로젝트 로고/이름."""
    st.markdown(
        f"""
        <div class="sidebar-brand">
          <div class="brand-icon">{PROJECT_ICON}</div>
          <div class="brand-text">{PROJECT_NAME}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_db_credentials_sidebar() -> tuple[str, str]:
    """[기능: DB 로그인] 사이드바에 MariaDB ID/PW 입력."""
    st.markdown(
        '<div class="sidebar-section-label">DB 로그인</div>',
        unsafe_allow_html=True,
    )
    db_user = st.text_input(
        "사용자 ID",
        placeholder="예: root",
        key="db_user_input",
    )
    db_password = st.text_input(
        "비밀번호",
        type="password",
        placeholder="비밀번호 입력",
        key="db_password_input",
    )
    return db_user, db_password


def render_sidebar_chat_history() -> None:
    """사이드바에 세션에 저장된 최근 채팅 목록(클릭 시 복원)."""
    st.markdown(
        '<div class="sidebar-section-label">최근</div>',
        unsafe_allow_html=True,
    )
    sessions = st.session_state.get("chat_sessions") or []
    if not sessions:
        st.caption("아직 대화가 없습니다.")
        return

    active_id = st.session_state.get("active_chat_id")
    for session in sessions[:12]:
        chat_id = session.get("id")
        label = truncate_one_line(session.get("title") or "새 채팅", max_chars=24)
        is_active = chat_id == active_id
        if st.button(
            label,
            key=f"recent_chat_{chat_id}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            if load_chat_session(chat_id):
                st.rerun()


def render_empty_hero() -> None:
    """대화가 비어 있을 때 Gemini 스타일 히어로를 표시합니다."""
    st.markdown(
        f"""
        <div class="gemini-hero">
          <h1>{PROJECT_NAME}</h1>
          <p>자연어로 물어보면 스키마를 골라 SQL을 만들고, DB 결과까지 보여 드립니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
