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
        # Prefer session_state, fallback to internal dict
        if key in st.session_state:
            return st.session_state.get(key) or default
        return super().get(key, default)
    def __getitem__(self, key):
        v = self.get(key, None)
        if v is None:
            raise KeyError(key)
        return v
    def __setitem__(self, key, value):
        # Mirror into session_state so child apps can read it
        st.session_state[key] = value
        return super().__setitem__(key, value)
    def save(self):
        return None

def _patch_cookie_manager():
    # Patch "streamlit_cookies_manager.EncryptedCookieManager" to return HubCookies
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
    # Child apps may call set_page_config; make it no-op
    st.set_page_config = lambda *a, **k: None

def _force_entry(entry: str):
    # Best-effort: many apps use st.session_state["page"]
    if entry:
        st.session_state["page"] = entry
        st.session_state["entry_target"] = entry
        st.session_state["quiz_entry"] = True

def _ensure_tokens():
    # Mirror to the keys that child apps most commonly expect
    at = st.session_state.get("access_token")
    rt = st.session_state.get("refresh_token")
    if at:
        st.session_state["access_token"] = at
    if rt:
        st.session_state["refresh_token"] = rt

def run(entry: str = "quiz"):
    _patch_cookie_manager()
    _patch_set_page_config()
    _force_entry(entry)
    _ensure_tokens()
    # Execute original word app script in isolated globals
    runpy.run_path("word_src.py", run_name="__main__")
