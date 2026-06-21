"""Text2SQL 파이프라인 진행 표시 UI."""

from __future__ import annotations

import streamlit.components.v1 as components

PIPELINE_STEPS = [
    "스키마 로드",
    "키워드 필터링",
    "프롬프트 생성",
    "SQL 생성",
    "파서 검증",
]

PROGRESS_BAR_HEIGHT = 138


def _step_state(index: int, completed_count: int, total: int) -> str:
    if index < completed_count:
        return "completed"
    if index == completed_count and completed_count < total:
        return "active"
    return "pending"


def _fill_percent(completed_count: int, total: int) -> float:
    """
    트랙(첫 원 중심~마지막 원 중심) 기준 채움 비율.
    completed_count번 단계가 진행 중일 때 해당 원 중심까지 채웁니다.
    """
    if total <= 1:
        return 100.0 if completed_count >= total else 0.0
    if completed_count >= total:
        return 100.0
    return (completed_count / (total - 1)) * 100


def _build_progress_html(completed_count: int) -> str:
    total = len(PIPELINE_STEPS)
    completed_count = max(0, min(completed_count, total))
    fill_pct = _fill_percent(completed_count, total)

    steps_html = []
    for i, label in enumerate(PIPELINE_STEPS):
        state = _step_state(i, completed_count, total)
        if state == "completed":
            node_inner = '<span class="check">✓</span>'
        elif state == "active":
            node_inner = '<span class="dots"><i></i><i></i><i></i></span>'
        else:
            node_inner = ""

        steps_html.append(
            f"""
            <div class="step step-{state}">
                <div class="node">{node_inner}</div>
                <div class="label">{label}</div>
            </div>
            """
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
    background: transparent;
    overflow: hidden;
}}
.progress {{
    position: relative;
    padding: 32px 0 10px;
}}
.track {{
    position: absolute;
    top: 44px;
    left: 10%;
    width: 80%;
    height: 12px;
    background: #e4e7eb;
    border-radius: 999px;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.12);
    z-index: 0;
}}
.track-fill {{
    position: absolute;
    top: 44px;
    left: 10%;
    width: 80%;
    height: 12px;
    border-radius: 999px;
    z-index: 0;
    pointer-events: none;
}}
.track-fill::after {{
    content: "";
    display: block;
    height: 100%;
    width: {fill_pct}%;
    background: linear-gradient(180deg, #72d572 0%, #4caf50 100%);
    border-radius: 999px;
    transition: width 0.3s ease;
}}
.steps {{
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}}
.step {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 0;
}}
.node {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fff;
}}
.step-completed .node {{
    background: linear-gradient(180deg, #72d572 0%, #4caf50 100%);
    box-shadow: 0 2px 5px rgba(76, 175, 80, 0.35);
}}
.step-completed .check {{
    color: #fff;
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
}}
.step-active .node {{
    width: 40px;
    height: 40px;
    background: linear-gradient(180deg, #72d572 0%, #43a047 100%);
    box-shadow: 0 3px 10px rgba(76, 175, 80, 0.45);
}}
.step-active .dots {{
    display: flex;
    gap: 3px;
    align-items: center;
}}
.step-active .dots i {{
    display: block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: #fff;
}}
.step-pending .node {{
    background: #eceff1;
    border: 2px solid #dde1e6;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
}}
.label {{
    margin-top: 10px;
    font-size: 12px;
    line-height: 1.25;
    text-align: center;
    color: #9e9e9e;
    padding: 0 2px;
    word-break: keep-all;
}}
.step-active .label {{
    color: #43a047;
    font-weight: 600;
}}
.step-completed .label {{
    color: #757575;
}}
</style>
</head>
<body>
<div class="progress">
    <div class="track"></div>
    <div class="track-fill"></div>
    <div class="steps">
        {''.join(steps_html)}
    </div>
</div>
</body>
</html>"""


def display_pipeline_progress(completed_count: int) -> None:
    """이미지 스타일의 stepper progress bar를 iframe으로 렌더링합니다."""
    components.html(
        _build_progress_html(completed_count),
        height=PROGRESS_BAR_HEIGHT,
        scrolling=False,
    )


def render_pipeline_progress(completed_count: int) -> str:
    """하위 호환용 — display_pipeline_progress() 사용을 권장합니다."""
    return _build_progress_html(completed_count)
