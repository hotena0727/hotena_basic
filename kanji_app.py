from __future__ import annotations

import sys
import types
import runpy
import streamlit as st

# ------------------------------------------------------------
# ✅ Hub cookie shim: NEVER creates components (no duplicate key)
# ------------------------------------------------------------
class HubCookies(dict):
    def ready(self) -> bool:
        return True
    def get(self, key, default=None):
        # Prefer session_state
        if key in st.session_state:
            return st.session_state.get(key) or default
        return super().get(key, default)
    def __setitem__(self, key, value):
        st.session_state[key] = value
        return super().__setitem__(key, value)
    def save(self):
        return None

def _patch_cookie_manager():
    mod_name = "streamlit_cookies_manager"
    if mod_name in sys.modules:
        mod = sys.modules[mod_name]
    else:
        mod = types.ModuleType(mod_name)
        sys.modules[mod_name] = mod

    def EncryptedCookieManager(*args, **kwargs):
        return HubCookies()

    setattr(mod, "EncryptedCookieManager", EncryptedCookieManager)

def _patch_set_page_config():
    st.set_page_config = lambda *a, **k: None

def _force_entry(entry: str):
    if entry:
        st.session_state["page"] = entry
        st.session_state["entry_target"] = entry
        st.session_state["quiz_entry"] = True

def _ensure_tokens():
    at = st.session_state.get("access_token")
    rt = st.session_state.get("refresh_token")
    if at:
        st.session_state["access_token"] = at
    if rt:
        st.session_state["refresh_token"] = rt

def _hide_child_buttons():
    # Hide duplicate buttons inside child apps (they should use hub menu now)
    orig_button = st.button

    HIDE_LABELS = {
        "마이페이지", "로그아웃", "로그아웃하기", "My Page", "Logout", "ログアウト", "マイページ",
        "홈", "Home"
    }

    def wrapped_button(label, *args, **kwargs):
        try:
            if isinstance(label, str) and label.strip() in HIDE_LABELS:
                # Do not render
                return False
        except Exception:
            pass
        return orig_button(label, *args, **kwargs)

    st.button = wrapped_button

def run(entry: str = "quiz"):
    _patch_cookie_manager()
    _patch_set_page_config()
    _hide_child_buttons()
    _force_entry(entry)
    _ensure_tokens()
    runpy.run_path("kanji_src.py", run_name="__main__")
