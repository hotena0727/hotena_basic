# core.py
# ============================================================
# ✅ Hotena shared core utilities (Auth/Cookies/Supabase/UI)
# - Keeps UI/feature logic inside each page file
# - Centralizes session restore + authed supabase client creation
# - Prevents duplicate cookie component render in same Streamlit run
# ============================================================

from __future__ import annotations

import os
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# (lazy imports) heavy deps are imported inside functions to reduce F5 skeleton time




# ----------------------------
# Config (env -> secrets)
# ----------------------------
def get_cfg(key: str) -> str:
    """Read from env first, then st.secrets. Returns '' if missing."""
    v = os.getenv(key)
    if v:
        return v
    try:
        return st.secrets[key]
    except Exception:
        return ""



def _hide_streamlit_component_iframes() -> None:
    """Hide Streamlit custom-component iframes that are used only for JS/cookies and show as gray blocks on F5.

    Uses CSS :has() (supported by modern Chromium/Safari) + JS fallback.
    """
    if st.session_state.get("_hide_streamlit_component_iframes_done"):
        return
    st.session_state["_hide_streamlit_component_iframes_done"] = True

    # 1) CSS (preferred): hide any stIFrame wrapper that contains a streamlit.components iframe
   st.markdown(
        """<style>
    /* ✅ 더 넓게 잡는다: title에 streamlit/components 포함 OR src에 component 포함 */
    div[data-testid="stIFrame"]:has(iframe[title*="streamlit"]),
    div[data-testid="stIFrame"]:has(iframe[title*="components"]),
    div[data-testid="stIFrame"]:has(iframe[src*="component"]),
    div[data-testid="stIFrame"]:has(iframe[srcdoc]){
      display:none !important;
      height:0 !important;
      min-height:0 !important;
      margin:0 !important;
      padding:0 !important;
    }

    div[data-testid="stIFrame"] iframe[title*="streamlit"],
    div[data-testid="stIFrame"] iframe[title*="components"],
    div[data-testid="stIFrame"] iframe[src*="component"],
    div[data-testid="stIFrame"] iframe[srcdoc]{
      display:none !important;
      height:0 !important;
      min-height:0 !important;
    }
    </style>""",
        unsafe_allow_html=True,
    )

    # 2) JS fallback: repeatedly collapse matching wrappers (in case :has isn't applied early enough)
    try:
        components.html(
"""
<script>
(function(){
  function kill(){
    try{
      var doc = (window.parent && window.parent.document) ? window.parent.document : document;
      var wrappers = doc.querySelectorAll('[data-testid="stIFrame"]');
      wrappers.forEach(function(w){
        try{
          var fr = w.querySelector('iframe');
          if(!fr) return;

          var t = (fr.getAttribute('title') || '').toLowerCase();
          var s = (fr.getAttribute('src') || '').toLowerCase();
          var isStreamlitComp = t.includes('streamlit') || t.includes('components') || s.includes('component') || fr.hasAttribute('srcdoc');

          // ✅ "큰 회색 블록"만 접는다 (실제 표시용 컴포넌트까지 죽이지 않게)
          var h = w.getBoundingClientRect().height || 0;
          if(isStreamlitComp && h >= 80){
            w.style.display='none';
            w.style.height='0px';
            w.style.minHeight='0px';
            w.style.margin='0';
            w.style.padding='0';
            fr.style.display='none';
            fr.style.height='0px';
            fr.style.minHeight='0px';
          }
        }catch(e){}
      });
    }catch(e){}
  }
  kill();
  setTimeout(kill, 60);
  setTimeout(kill, 220);
  setTimeout(kill, 650);
  var n=0, iv=setInterval(function(){ kill(); if(++n>=40) clearInterval(iv); }, 300);
})();
</script>
""",
height=0,
scrolling=False,
)
    except Exception:
        pass



def ensure_core(
    *,
    cookie_prefix: str = "hotena_beginner_",
    localstorage_keys: Tuple[str, str] = ("hotena_rt", "hotena_at"),
) -> dict[str, str]:
    """
    Ensure CFG/cookies/supabase anon client exist in st.session_state.
    Safe to call multiple times in the same run.
    """
    # 1) CFG
    cfg = st.session_state.get("cfg")
    if not isinstance(cfg, dict) or not cfg:
        cfg = {
            "COOKIE_PASSWORD": get_cfg("COOKIE_PASSWORD"),
            "SUPABASE_URL": get_cfg("SUPABASE_URL"),
            "SUPABASE_ANON_KEY": get_cfg("SUPABASE_ANON_KEY"),
        }

        # Stable fallback for cookie password (prevents "logout on refresh")
        fallback = hashlib.sha256((cfg.get("SUPABASE_ANON_KEY") or "").encode("utf-8")).hexdigest()
        if not cfg.get("COOKIE_PASSWORD"):
            cfg["COOKIE_PASSWORD"] = fallback

        st.session_state["cfg"] = cfg

    missing = [k for k, v in cfg.items() if not v]
    if missing:
        st.error(f"설정값이 없습니다: {', '.join(missing)} (Cloud Run env 또는 Streamlit secrets 확인)")
        st.stop()

    # 2) Cookie manager (render only once)
    if "cookies" not in st.session_state:
        try:
            from streamlit_cookies_manager import EncryptedCookieManager as _ECM
        except Exception:
            _ECM = None
        if _ECM is None:
            st.error("streamlit-cookies-manager가 설치되지 않았습니다.")
            st.stop()

        cookies = _ECM(prefix=cookie_prefix, password=str(cfg["COOKIE_PASSWORD"]))
        if not cookies.ready():
            st.info("잠깐만요! 곧 시작할게요🙂")
            st.stop()
        st.session_state["cookies"] = cookies

    # 3) Save lock (avoid DuplicateElementKey in same run)
    if "_cookie_save_lock" not in st.session_state:
        st.session_state["_cookie_save_lock"] = False

    # 4) Supabase anon client
    if "sb" not in st.session_state:
        try:
            from supabase import create_client as _cc
        except Exception:
            _cc = None
        if _cc is None:
            st.error("supabase-py가 설치되지 않았습니다.")
            st.stop()
        st.session_state["sb"] = _cc(cfg["SUPABASE_URL"], cfg["SUPABASE_ANON_KEY"])

    # store localstorage keys for auth bridge
    st.session_state["_core_ls_rt"] = localstorage_keys[0]
    st.session_state["_core_ls_at"] = localstorage_keys[1]

    return cfg


def _cookies_save_once_per_run() -> None:
    if st.session_state.get("_cookie_save_lock"):
        return
    st.session_state["_cookie_save_lock"] = True
    try:
        st.session_state["cookies"].save()
    except Exception:
        pass


# ----------------------------
# Encrypt / Decrypt
# ----------------------------
def _fernet():
    from cryptography.fernet import Fernet
    cfg = ensure_core()
    pw = str(cfg.get("COOKIE_PASSWORD", ""))
    key = base64.urlsafe_b64encode(hashlib.sha256(pw.encode("utf-8")).digest())
    return Fernet(key)


def enc(s: str) -> str:
    return _fernet().encrypt(s.encode("utf-8")).decode("utf-8")


def dec(token: str) -> Optional[str]:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


# ----------------------------
# JS helpers (query params <-> localStorage)
# ----------------------------
def _js_bridge_localstorage_to_queryparam(ls_key: str, qp_key: str) -> None:
    """If localStorage has a value and query param doesn't, set it once."""
    components.html(
        f"""
<script>
(function () {{
  try {{
    const v = window.localStorage.getItem({ls_key!r}) || "";
    const url = new URL(window.location.href);
    if (v && !url.searchParams.get({qp_key!r})) {{
      url.searchParams.set({qp_key!r}, v);
      window.history.replaceState(null, "", url.toString());
    }}
  }} catch(e) {{}}
}})();
</script>
        """,
        height=0,
    )


def _js_set_localstorage(ls_key: str, value: str) -> None:
    components.html(
        f"""
<script>
(function () {{
  try {{
    window.localStorage.setItem({ls_key!r}, {value!r});
  }} catch(e) {{}}
}})();
</script>
        """,
        height=0,
    )


def _js_clear_localstorage(ls_key: str) -> None:
    components.html(
        f"""
<script>
(function () {{
  try {{
    window.localStorage.removeItem({ls_key!r});
  }} catch(e) {{}}
}})();
</script>
        """,
        height=0,
    )


# ----------------------------
# Auth restore + authed client
# ----------------------------
def refresh_session_from_cookie_if_needed(*, force: bool = False) -> bool:
    """
    Restore session using:
    1) (one-time) localStorage -> query params bridge
    2) query params (encrypted)
    3) cookies
    4) validate access token as fallback
    """
    ensure_core()
    if not force and st.session_state.get("user") and st.session_state.get("access_token"):
        return True

    sb = st.session_state["sb"]
    cookies = st.session_state["cookies"]
    ls_rt = st.session_state.get("_core_ls_rt", "hotena_rt")
    ls_at = st.session_state.get("_core_ls_at", "hotena_at")

    # Bridge localStorage -> query params once
    _js_bridge_localstorage_to_queryparam(ls_rt, "rt")
    _js_bridge_localstorage_to_queryparam(ls_at, "at")

    rt = None
    at = None
    try:
        rt_enc = st.query_params.get("rt")
        at_enc = st.query_params.get("at")
        rt = dec(rt_enc) if isinstance(rt_enc, str) and rt_enc else None
        at = dec(at_enc) if isinstance(at_enc, str) and at_enc else None
    except Exception:
        rt = None
        at = None

    if not rt:
        try:
            rt = cookies.get("refresh_token")
        except Exception:
            rt = None
    if not at:
        try:
            at = cookies.get("access_token")
        except Exception:
            at = None

    if rt:
        refreshed = None
        try:
            refreshed = sb.auth.refresh_session(rt)
        except Exception:
            try:
                refreshed = sb.auth.refresh_session({"refresh_token": rt})
            except Exception:
                refreshed = None

        if refreshed and getattr(refreshed, "session", None) and getattr(refreshed.session, "access_token", None):
            st.session_state["user"] = refreshed.user
            st.session_state["access_token"] = refreshed.session.access_token
            st.session_state["refresh_token"] = refreshed.session.refresh_token

            try:
                cookies["access_token"] = refreshed.session.access_token
                cookies["refresh_token"] = refreshed.session.refresh_token
                _cookies_save_once_per_run()
            except Exception:
                pass

            try:
                st.query_params["rt"] = enc(refreshed.session.refresh_token)
                st.query_params["at"] = enc(refreshed.session.access_token)
                _js_set_localstorage(ls_rt, st.query_params.get("rt", ""))
                _js_set_localstorage(ls_at, st.query_params.get("at", ""))
            except Exception:
                pass

            return True

    if at:
        try:
            u = sb.auth.get_user(at)
            user_obj = getattr(u, "user", None) or getattr(u, "data", None)
            if user_obj:
                st.session_state["user"] = user_obj
                st.session_state["access_token"] = at
                if rt:
                    st.session_state["refresh_token"] = rt
                return True
        except Exception:
            pass

    return False


def get_authed_sb(*, force_refresh: bool = True):
    """
    Return a Supabase client authenticated with current access token.
    Caches by token to avoid rebuilding.
    """
    ensure_core()
    if force_refresh:
        refresh_session_from_cookie_if_needed(force=True)
    token = st.session_state.get("access_token")
    if not token:
        return None

    cached = st.session_state.get("sb_authed")
    cached_token = st.session_state.get("sb_authed_token")
    if cached is not None and cached_token == token:
        return cached

    try:
        from supabase import create_client as _cc
    except Exception:
        _cc = None
    if _cc is None:
        st.error('supabase-py가 설치되지 않았습니다.')
        st.stop()
    sb2 = _cc(st.session_state["cfg"]["SUPABASE_URL"], st.session_state["cfg"]["SUPABASE_ANON_KEY"])
    sb2.postgrest.auth(token)
    st.session_state["sb_authed"] = sb2
    st.session_state["sb_authed_token"] = token
    return sb2


def clear_auth_everywhere() -> None:
    """Clear session + cookies + query params + localStorage (best effort)."""
    ensure_core()
    cookies = st.session_state["cookies"]
    ls_rt = st.session_state.get("_core_ls_rt", "hotena_rt")
    ls_at = st.session_state.get("_core_ls_at", "hotena_at")

    for k in ["user", "access_token", "refresh_token", "sb_authed", "sb_authed_token", "user_plan", "is_admin", "user_id"]:
        st.session_state.pop(k, None)

    # clear cookies
    try:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        _cookies_save_once_per_run()
    except Exception:
        pass

    # clear query params
    try:
        if "rt" in st.query_params:
            del st.query_params["rt"]
        if "at" in st.query_params:
            del st.query_params["at"]
    except Exception:
        pass

    # clear localStorage
    try:
        _js_clear_localstorage(ls_rt)
        _js_clear_localstorage(ls_at)
    except Exception:
        pass


def run_db(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """Call DB function with authed client. Returns None if not authed."""
    sb_authed = get_authed_sb()
    if sb_authed is None:
        return None
    return fn(sb_authed, *args, **kwargs)


# ----------------------------
# Scroll helpers (FAB)
# ----------------------------
def inject_top_anchor() -> None:
    """Inject a top anchor once per run."""
    if st.session_state.get("_core_top_anchor"):
        return
    st.session_state["_core_top_anchor"] = True
    st.markdown('<div id="__TOP__"></div>', unsafe_allow_html=True)


def scroll_to_top(nonce: int = 0) -> None:
    inject_top_anchor()
    components.html(
        f"""
        <script>
        (function () {{
          const doc = window.parent.document;
          const targets = [
            doc.querySelector('[data-testid="stAppViewContainer"]'),
            doc.querySelector('[data-testid="stMain"]'),
            doc.querySelector('section.main'),
            doc.documentElement,
            doc.body
          ].filter(Boolean);

          const go = () => {{
            try {{
              const top = doc.getElementById("__TOP__");
              if (top) top.scrollIntoView({{behavior: "auto", block: "start"}});
              targets.forEach(t => {{
                if (t && typeof t.scrollTo === "function") t.scrollTo({{top: 0, left: 0, behavior: "auto"}});
                if (t) t.scrollTop = 0;
              }});
              window.parent.scrollTo(0, 0);
              window.scrollTo(0, 0);
            }} catch(e) {{}}
          }};

          go();
          requestAnimationFrame(go);
          setTimeout(go, 50);
          setTimeout(go, 150);
          setTimeout(go, 350);
          setTimeout(go, 800);
        }})();
        </script>
        <!-- nonce:{nonce} -->
        """,
        height=0, 
        scrolling=False)


def render_floating_scroll_top() -> None:
    inject_top_anchor()
    components.html(
        """
<script>
(function(){
  const doc = window.parent.document;
  if (doc.getElementById("__FAB_TOP__")) return;

  const btn = doc.createElement("button");
  btn.id = "__FAB_TOP__";
  btn.textContent = "↑";

  btn.style.position = "fixed";
  btn.style.right = "14px";
  btn.style.zIndex = "2147483647";
  btn.style.width = "46px";
  btn.style.height = "46px";
  btn.style.borderRadius = "999px";
  btn.style.border = "1px solid rgba(120,120,120,0.25)";
  btn.style.background = "rgba(0,0,0,0.55)";
  btn.style.color = "#fff";
  btn.style.fontSize = "18px";
  btn.style.fontWeight = "900";
  btn.style.boxShadow = "0 10px 22px rgba(0,0,0,0.25)";
  btn.style.cursor = "pointer";
  btn.style.userSelect = "none";
  btn.style.display = "flex";
  btn.style.alignItems = "center";
  btn.style.justifyContent = "center";
  btn.style.opacity = "0";

  const applyDeviceVisibility = () => {
    try {
      const w = window.parent.innerWidth || window.innerWidth;
      if (w >= 801) btn.style.display = "none";
      else btn.style.display = "flex";
    } catch(e) {}
  };

  const goTop = () => {
    try {
      const top = doc.getElementById("__TOP__");
      if (top) top.scrollIntoView({behavior:"smooth", block:"start"});

      const targets = [
        doc.querySelector('[data-testid="stAppViewContainer"]'),
        doc.querySelector('[data-testid="stMain"]'),
        doc.querySelector('section.main'),
        doc.documentElement,
        doc.body
      ].filter(Boolean);

      targets.forEach(t => {
        if (t && typeof t.scrollTo === "function") t.scrollTo({top:0, left:0, behavior:"smooth"});
        if (t) t.scrollTop = 0;
      });

      window.parent.scrollTo(0,0);
      window.scrollTo(0,0);
    } catch(e) {}
  };

  btn.addEventListener("click", goTop);

  const mount = () => doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;

  const BASE = 18;
  const EXTRA = 34;

  const reposition = () => {
    try {
      const vv = window.parent.visualViewport || window.visualViewport;
      const innerH = window.parent.innerHeight || window.innerHeight;
      const hiddenBottom = vv ? Math.max(0, innerH - vv.height - (vv.offsetTop || 0)) : 0;
      btn.style.bottom = (BASE + EXTRA + hiddenBottom) + "px";
      btn.style.opacity = "1";
    } catch(e) {
      btn.style.bottom = "220px";
      btn.style.opacity = "1";
    }
    applyDeviceVisibility();
  };

  const tryAttach = (n=0) => {
    const root = mount();
    if (!root) {
      if (n < 30) return setTimeout(() => tryAttach(n+1), 50);
      return;
    }
    root.appendChild(btn);
    reposition();
    setTimeout(reposition, 50);
    setTimeout(reposition, 200);
    setTimeout(reposition, 600);
  };

  tryAttach();
  window.parent.addEventListener("resize", reposition, {passive:true});

  const vv = window.parent.visualViewport || window.visualViewport;
  if (vv) {
    vv.addEventListener("resize", reposition, {passive:true});
    vv.addEventListener("scroll", reposition, {passive:true});
  }
})();
</script>
        """,
        height=0, scrolling=False)

# ----------------------------
# DB helpers (profiles / attempts)
# ----------------------------
def ensure_profile(sb_authed: Any, user: Any) -> None:
    """Upsert minimal profile row (id/email). Safe to call repeatedly."""
    try:
        sb_authed.table("profiles").upsert(
            {"id": getattr(user, "id", None), "email": getattr(user, "email", None)},
            on_conflict="id",
        ).execute()
    except Exception:
        pass


def load_profile(sb_authed: Any, user_id: str) -> dict[str, Any]:
    """Load profile row (id,email,is_admin,plan,full_name,progress). Returns {{}} on failure."""
    try:
        res = (
            sb_authed.table("profiles")
            .select("id,email,is_admin,plan,full_name,progress")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if res and getattr(res, "data", None):
            return res.data or {}
    except Exception:
        pass
    return {}


def clear_progress_in_db(sb_authed: Any, user_id: str) -> None:
    try:
        sb_authed.table("profiles").upsert(
            {"id": user_id, "progress": None},
            on_conflict="id",
        ).execute()
    except Exception:
        pass


def delete_all_learning_records(sb_authed: Any, user_id: str) -> None:
    """Delete attempts + clear progress."""
    try:
        sb_authed.table("quiz_attempts").delete().eq("user_id", user_id).execute()
    except Exception:
        pass
    clear_progress_in_db(sb_authed, user_id)


def mark_attendance_once(sb_authed: Any) -> Optional[dict[str, Any]]:
    """Call mark_attendance_kst RPC at most once per session."""
    if st.session_state.get("attendance_checked"):
        return None
    try:
        res = sb_authed.rpc("mark_attendance_kst", {}).execute()
        st.session_state.attendance_checked = True
        return res.data[0] if getattr(res, "data", None) else None
    except Exception:
        st.session_state.attendance_checked = True
        return None


def fetch_recent_attempts(sb_authed: Any, user_id: str, limit: int = 10):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, level, pos_mode, quiz_len, score, wrong_count, wrong_list")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )


def fetch_all_attempts_admin(sb_authed: Any, limit: int = 500):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, user_email, level, pos_mode, quiz_len, score, wrong_count")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
