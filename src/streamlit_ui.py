"""Streamlit 기본 UI 커스터마이징 (버튼 숨김, 메뉴 정리)."""

from __future__ import annotations

import streamlit.components.v1 as components

HIDE_CHROME_CSS = """
<style>
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stStatusWidget"] { display: none !important; }
.stAppDeployButton { display: none !important; }
.stElementContainer:has(iframe[height="0"]) {
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
div[data-testid="stHtml"] iframe {
    border: none !important;
}
div[data-testid="stHtml"] {
    margin-top: 0.75rem;
    margin-bottom: 0.25rem;
}
</style>
"""

MENU_CUSTOMIZE_SCRIPT = """
<script>
(function () {
  const doc = window.parent.document;

  const THEME_LABELS = new Set(["Theme"]);

  function hideNonSettingsItems(root) {
    if (!root) return;

    root.querySelectorAll('[role="menuitem"]').forEach((el) => {
      el.style.display = "none";
    });

    root.querySelectorAll('[role="menuitemcheckbox"]').forEach((el) => {
      el.style.display = "none";
    });

    root.querySelectorAll('[role="group"]').forEach((el) => {
      const label = el.getAttribute("aria-label") || "";
      if (!THEME_LABELS.has(label)) {
        el.style.display = "none";
      }
    });

    root.querySelectorAll('[data-testid="stMainMenuPopover"], [data-testid="stPopover"]').forEach((popover) => {
      popover.querySelectorAll("button, a, [role='button']").forEach((el) => {
        const text = (el.textContent || "").trim();
        if (/copy|version|streamlit/i.test(text) || el.getAttribute("aria-label") === "Copy") {
          el.closest("div")?.style && (el.closest("div").style.display = "none");
          el.style.display = "none";
        }
      });
      const footer = popover.querySelector("footer");
      if (footer) footer.style.display = "none";
    });
  }

  function apply() {
    const header = doc.querySelector('[data-testid="stHeader"]');
    const popovers = doc.querySelectorAll('[data-testid="stMainMenuPopover"], [data-testid="stPopover"]');
    hideNonSettingsItems(header);
    popovers.forEach((p) => hideNonSettingsItems(p));
  }

  apply();
  new MutationObserver(apply).observe(doc.body, { childList: true, subtree: true });
})();
</script>
"""


def apply_ui_customization() -> None:
    """헤더 버튼 숨김 및 메인 메뉴에서 설정(테마)만 표시합니다."""
    import streamlit as st

    st.markdown(HIDE_CHROME_CSS, unsafe_allow_html=True)
    components.html(
        MENU_CUSTOMIZE_SCRIPT,
        height=0,
        width=0,
        scrolling=False,
    )
