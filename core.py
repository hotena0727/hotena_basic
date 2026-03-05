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
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components
from cryptography.fernet import Fernet

try:
    # Streamlit Cookies Manager
    from streamlit_cookies_manager import EncryptedCookieManager
except Exception:  # pragma: no cover
    EncryptedCookieManager = None  # type: ignore

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None  # type: ignore


# ----------------------------
# Config (env -> secrets)
# ----------------------------
# ============================================================
# ✅ Global UI CSS (applied once per Streamlit run)
# - Fix oversized top padding on mobile/PWA across Streamlit versions
# - Keep small breathing room for our custom top nav
# ============================================================
def apply_global_ui_css(*, top_padding_rem: float = 0.5) -> None:
    """Apply global layout CSS once per run.

    Fix oversized top padding on mobile/PWA across Streamlit versions.
    Targets both legacy (.block-container) and newer [data-testid="block-container"].
    """
    if st.session_state.get("_core_global_ui_css_applied"):
        return
    st.session_state["_core_global_ui_css_applied"] = True

    pad = f"{max(0.0, float(top_padding_rem))}rem"

    css = textwrap.dedent(f"""
    <style>
    /* --- TOP SPACING FIX (mobile/PWA) --- */
    [data-testid="stAppViewContainer"]{{ padding-top: 0 !important; }}
    div[data-testid="stAppViewContainer"] > .main{{ padding-top: 0 !important; }}

    /* Newer Streamlit */
    [data-testid="block-container"]{{ padding-top: {pad} !important; }}
    /* Older Streamlit */
    .block-container{{ padding-top: {pad} !important; }}

    /* In some layouts, the first vertical block adds extra margin */
    [data-testid="stVerticalBlock"] > div:first-child{{ margin-top: 0 !important; }}

    /* ✅ Kill Streamlit default header COMPLETELY (no reserved space) */
    header, header[data-testid="stHeader"]{{
      display: none !important;
      height: 0 !important;
      min-height: 0 !important;
    }}

    /* Safe-area: avoid extra blank gap on some Android devices */
    html, body{{ padding-top: 0 !important; }}

    /* --- FORCE HIDE STREAMLIT COMPONENT IFRAMES (prevents refresh top gap) --- */
    div[data-testid="stIFrame"]{{
      display: none !important;
      height: 0 !important;
      min-height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
    }}
    div[data-testid="stIFrame"] iframe{{
      display: none !important;
      height: 0 !important;
      min-height: 0 !important;
    }}
    </style>
    """)

    st.markdown(css, unsafe_allow_html=True)


def get_cfg(key: str) -> str:
    """Read from env first, then st.secrets safely. Returns '' if missing.

    Cloud Run does not provide Streamlit secrets.toml by default, so any direct
    st.secrets[...] access can crash. This helper prefers env vars (recommended),
    then falls back to st.session_state cfg, then to st.secrets if available.
    """
    # 1) Env (Cloud Run recommended)
    v = os.getenv(key, "")
    if isinstance(v, str) and v.strip():
        return v.strip()

    # 2) Session cfg (optional)
    try:
        cfg = st.session_state.get("cfg") or {}
        v2 = cfg.get(key, "")
        if isinstance(v2, str) and v2.strip():
            return v2.strip()
    except Exception:
        pass

    # 3) Streamlit secrets (only if present; must be inside try)
    try:
        s = st.secrets  # access may raise if secrets.toml missing
        if hasattr(s, "get"):
            v3 = s.get(key, "")
            return (v3 or "") if isinstance(v3, str) else str(v3)
        return s[key] if key in s else ""
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
/* Hide Streamlit custom component placeholders (gray blocks) */
div[data-testid="stIFrame"]:has(iframe[title^="streamlit.components.v1."]){
  display:none !important;
  height:0 !important;
  min-height:0 !important;
  margin:0 !important;
  padding:0 !important;
}
div[data-testid="stIFrame"]:has(iframe[title^="streamlit.components.v1."]) iframe{
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
      var frames = doc.querySelectorAll('iframe[title^="streamlit.components.v1."]');
      frames.forEach(function(fr){
        try{
          fr.style.display='none';
          fr.style.height='0px';
          fr.style.minHeight='0px';
          var wrap = fr.closest('[data-testid="stIFrame"]') || fr.parentElement;
          if(wrap){
            wrap.style.display='none';
            wrap.style.height='0px';
            wrap.style.minHeight='0px';
            wrap.style.margin='0';
            wrap.style.padding='0';
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
        )
    except Exception:
        pass



# ============================================================
# ✅ PWA / A2HS (Android/iOS 홈화면 추가) - ROOT assets version
# - Expects these URLs to be served at ROOT:
#   /app/static/pwa-manifest.json, /app/static/sw.js, /app/static/apple-touch-icon.png, /app/static/icon-192.png, /app/static/icon-512.png, /favicon.ico (optional)
# - Safe to call multiple times; injects only once per session.
# ============================================================
def inject_pwa_once(
    app_name: str = "Hotena",
    theme_color: str = "#0F6B3F",
    manifest_path: str = "/app/static/pwa-manifest.json",
    sw_path: str = "/app/static/sw.js",
    apple_touch_icon: str = "/app/static/apple-touch-icon.png",
    icon_192: str = "/app/static/icon-192.png",
    icon_512: str = "/app/static/icon-512.png",
) -> None:
    try:
        if st.session_state.get("_pwa_injected", False):
            return
        st.session_state["_pwa_injected"] = True

        js = f"""
<script>
(function() {{
  try {{
    const doc = (window.parent && window.parent.document) ? window.parent.document : document;
    const nav = (window.parent && window.parent.navigator) ? window.parent.navigator : navigator;

    // manifest
    let m = doc.querySelector("link[rel='manifest']");
    if (!m) {{ m = doc.createElement("link"); m.rel = "manifest"; doc.head.appendChild(m); }}
    m.href = {json.dumps(manifest_path)};

    // theme + iOS meta
    const meta = (name, content) => {{
      let el = doc.querySelector(`meta[name='${{name}}']`);
      if (!el) {{ el = doc.createElement("meta"); el.name = name; doc.head.appendChild(el); }}
      el.content = content;
    }};
    meta("theme-color", {json.dumps(theme_color)});
    meta("apple-mobile-web-app-capable", "yes");
    meta("apple-mobile-web-app-status-bar-style", "black-translucent");
    meta("apple-mobile-web-app-title", {json.dumps(app_name)});

    // iOS touch icon
    let a = doc.querySelector("link[rel='apple-touch-icon']");
    if (!a) {{ a = doc.createElement("link"); a.rel = "apple-touch-icon"; doc.head.appendChild(a); }}
    a.setAttribute("sizes", "180x180");
    a.href = {json.dumps(apple_touch_icon)};

    // icons (harmless; helps some browsers)
    function upsertIcon(href, sizes) {{
      let i = doc.querySelector(`link[rel='icon'][sizes='${{sizes}}']`);
      if (!i) {{
        i = doc.createElement("link");
        i.rel = "icon";
        i.type = "image/png";
        i.setAttribute("sizes", sizes);
        doc.head.appendChild(i);
      }}
      i.href = href;
    }}
    upsertIcon({json.dumps(icon_192)}, "192x192");
    upsertIcon({json.dumps(icon_512)}, "512x512");

    // service worker (Android A2HS 핵심)
    if ("serviceWorker" in nav) {{
      window.addEventListener("load", function() {{
        nav.serviceWorker.register({json.dumps(sw_path)}).catch(function(){{}});
      }});
    }}
  }} catch (e) {{}}
}})();
</script>
"""
        components.html(js, height=0)
    except Exception:
        # Do not break the app for PWA injection failures
        return

def ensure_core(
    *,
    cookie_prefix: str = "hotena_beginner_",
    localstorage_keys: Tuple[str, str] = ("hotena_rt", "hotena_at"),
) -> dict[str, str]:
    """
    Ensure CFG/cookies/supabase anon client exist in st.session_state.
    Safe to call multiple times in the same run.
    """
    apply_global_ui_css()

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
        if EncryptedCookieManager is None:
            st.error("streamlit-cookies-manager가 설치되지 않았습니다.")
            st.stop()

        cookies = EncryptedCookieManager(prefix=cookie_prefix, password=str(cfg["COOKIE_PASSWORD"]))
        if not cookies.ready():
            st.info("잠깐만요! 곧 시작할게요🙂")
            st.stop()
        st.session_state["cookies"] = cookies

    # 3) Save lock (avoid DuplicateElementKey in same run)
    if "_cookie_save_lock" not in st.session_state:
        st.session_state["_cookie_save_lock"] = False

    # 4) Supabase anon client
    if "sb" not in st.session_state:
        if create_client is None:
            st.error("supabase-py가 설치되지 않았습니다.")
            st.stop()
        st.session_state["sb"] = create_client(cfg["SUPABASE_URL"], cfg["SUPABASE_ANON_KEY"])

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
def _fernet() -> Fernet:
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

def _core_once_key(prefix: str, key: str) -> bool:
    k = f"_core_once__{prefix}__{key}"
    if st.session_state.get(k):
        return False
    st.session_state[k] = True
    return True

def _js_bridge_localstorage_to_queryparam(ls_key: str, qp_key: str) -> None:
    """If localStorage has a value and query param doesn't, set it once."""
    if not _core_once_key('ls2qp', f"{ls_key}->{qp_key}"):
        return
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
    if not _core_once_key('ls_set', ls_key):
        return
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
    if not _core_once_key('ls_rm', ls_key):
        return
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

    sb2 = create_client(st.session_state["cfg"]["SUPABASE_URL"], st.session_state["cfg"]["SUPABASE_ANON_KEY"])
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
          setTimeout(go, 200);
          
        }})();
        </script>
        <!-- nonce:{nonce} -->
        """,
        height=0,
    )


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
        height=1,
    )


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

# ============================================================
# ✅ Top Navigation (single source of truth)
# - Render ONCE from home.py (hub)
# - Sticky top, minimal gray tone
# - Preserves current query params (rt/at etc.) and sets p=
# - Hides Streamlit default menu/sidebar
# ============================================================
def render_top_nav(active: str = "home") -> None:
    import streamlit as st
    import textwrap
    from urllib.parse import urlencode

    # preserve all existing query params; only set p
    try:
        qp = dict(st.query_params)
    except Exception:
        qp = {}

    def _href(p: str) -> str:
        q = {k: v for k, v in qp.items() if k != "p"}
        q["p"] = p
        return "?" + urlencode(q, doseq=True)

    css = textwrap.dedent("""        <style>
      /* Hide Streamlit default UI */
      #MainMenu { visibility: hidden; }
      header, header[data-testid="stHeader"]{
        display:none !important;
        height:0 !important;
        min-height:0 !important;
      }
      footer{
        display:none !important;
        height:0 !important;
        min-height:0 !important;
      }
      [data-testid="stSidebar"] { display: none !important; }
      [data-testid="stSidebarNav"] { display: none !important; }

      .hn-topnav-wrap{
        position: sticky; left: 0; right: 0;
        top: 0;
        z-index: 2147483000;
        background: rgba(255,255,255,0.94);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(0,0,0,0.06);
      }
      .hn-topnav{
        max-width: 1100px;
        margin: 0 auto;
        padding: 10px 12px;
      }
      .hn-nav{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap: 6px;
      }
      .hn-nav a{
        flex: 1 1 0;
        text-align:center;
        text-decoration:none !important;
        color: rgba(0,0,0,0.55);
        font-size: 14px;
        font-weight: 650;
        letter-spacing: -0.2px;
        padding: 10px 0;
        border-radius: 10px;
        position: relative;
      }
      .hn-nav a:hover{
        color: rgba(0,0,0,0.82);
        background: rgba(0,0,0,0.03);
      }
      .hn-nav a.active{
        color: rgba(0,0,0,0.90);
      }
      .hn-nav a.active::after{
        content:"";
        position:absolute;
        left: 32%;
        bottom: 6px;
        width: 36%;
        height: 2px;
        background: #2f80ed;
        border-radius: 2px;
      }

      @media (max-width: 820px){
        .hn-topnav{ padding: 10px 10px; }
        .hn-nav{ gap: 4px; }
        .hn-nav a{ font-size: 13.5px; padding: 10px 0; }
        .hn-nav a.active::after{ left: 30%; width: 40%; }
      }
</style>
    """)

    html = f"""        <div class="hn-topnav-wrap">
      <div class="hn-topnav">
        <div class="hn-nav" role="navigation" aria-label="Primary">
          <a href="{_href('home')}" target="_self" class="{'active' if active=='home' else ''}">홈</a>
          <a href="{_href('word')}" target="_self" class="{'active' if active=='word' else ''}">단어</a>
          <a href="{_href('kanji')}" target="_self" class="{'active' if active=='kanji' else ''}">한자</a>
          <a href="{_href('talk')}" target="_self" class="{'active' if active=='talk' else ''}">회화</a>
          <a href="{_href('my')}" target="_self" class="{'active' if active=='my' else ''}">MY</a>
        </div>
      </div>
    </div>
    """

    st.markdown(css, unsafe_allow_html=True)
    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# ✅ SFX (Sound Effects) — shared tiny UX feedback sounds
# - session-level ON/OFF (default ON)
# - Use: play_sfx("correct"|"wrong"|"reward"|"click")
# ============================================================

def is_sfx_enabled(default: bool = True) -> bool:
    """Return whether SFX is enabled (session-level)."""
    return bool(st.session_state.get("sfx_enabled", default))

def set_sfx_enabled(enabled: bool) -> None:
    """Enable/disable SFX (session-level)."""
    st.session_state["sfx_enabled"] = bool(enabled)

# Tiny embedded WAVs (base64). No external assets needed.
# ============================================================
# ✅ SFX (tiny WAVs generated at runtime to avoid huge base64 blobs)
# - 16-bit PCM mono, 22050Hz
# ============================================================
import base64
import io
import math
import struct
import wave

def _sfx__wav_bytes_from_tones(tones, framerate: int = 22050) -> bytes:
    """Generate a small WAV (PCM16 mono) from tone segments.
    tones: list of (freq_hz, seconds, volume_0_1). freq_hz==0 => silence
    """
    frames = bytearray()
    for freq, secs, vol in tones:
        n = max(0, int(secs * framerate))
        if n <= 0:
            continue
        if freq <= 0:
            # silence
            frames.extend(b"\x00\x00" * n)
            continue
        amp = int(32767 * max(0.0, min(1.0, float(vol))))
        w = 2.0 * math.pi * float(freq) / float(framerate)
        for i in range(n):
            v = int(amp * math.sin(w * i))
            frames.extend(struct.pack("<h", v))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(bytes(frames))
    return buf.getvalue()

def _sfx__wav_b64(tones) -> str:
    return base64.b64encode(_sfx__wav_bytes_from_tones(tones)).decode("ascii")

# Pre-generate once (module import time)
_SFX_WAV_B64 = {
    # quick UI click
    "click": _sfx__wav_b64([(1200, 0.020, 0.35), (0, 0.010, 0.0)]),
    # correct: two bright beeps
    "correct": _sfx__wav_b64([(880, 0.050, 0.45), (0, 0.015, 0.0), (1320, 0.060, 0.45)]),
    # wrong: one low dull beep
    "wrong": _sfx__wav_b64([(220, 0.120, 0.45)]),
    # reward: simple 3-note arpeggio
    "reward": _sfx__wav_b64([(660, 0.050, 0.45), (0, 0.010, 0.0), (880, 0.050, 0.45), (0, 0.010, 0.0), (1320, 0.070, 0.45)]),
}

def _sfx_base_url() -> str:
    """Base URL for external SFX files (mp3).

    Priority: env/secrets SFX_BASE_URL -> default Hotena CDN path.
    """
    base = (get_cfg("SFX_BASE_URL") or "").strip()
    if not base:
        base = "https://hotena.com/hotena/app/mp3/sfx/"
    if not base.endswith("/"):
        base += "/"
    return base

def _sfx_url(name: str) -> str:
    nm = str(name).strip().lower()
    # Allow custom filenames via env/secrets if needed later; for now, use {name}.mp3
    return _sfx_base_url() + f"{nm}.mp3"

def play_sfx(name: str) -> None:
    """Play a short SFX (best effort).

    1) Try external mp3 at SFX_BASE_URL (default: https://hotena.com/hotena/app/mp3/sfx/)
    2) Fallback to built-in base64 wav (always available).
    """
    if not is_sfx_enabled(True):
        return

    nm = str(name).strip().lower()
    b64 = _SFX_WAV_B64.get(nm)
    # We still try remote even if b64 is missing; but keep a hard fallback only if we have b64.
    url = _sfx_url(nm)

    try:
        src1 = json.dumps(url)
        src2 = json.dumps(f"data:audio/wav;base64,{b64}") if b64 else "null"

        # Use JS so we can fallback if the mp3 fails to load/play.
        components.html(
            f"""
<script>
(function() {{
  try {{
    var a = new Audio();
    a.preload = 'auto';
    var src1 = {src1};
    var src2 = {src2};

    var triedFallback = false;
    function playFallback() {{
      if (triedFallback) return;
      triedFallback = true;
      if (!src2 || src2 === null) return;
      try {{
        a.src = src2;
        a.currentTime = 0;
        var p2 = a.play();
        if (p2 && p2.catch) p2.catch(function(){{}});
      }} catch(e) {{}}
    }}

    a.addEventListener('error', function(){{ playFallback(); }}, {{ once: true }});

    // Try remote first
    a.src = src1;
    a.currentTime = 0;
    var p = a.play();
    if (p && p.catch) {{
      p.catch(function(){{ playFallback(); }});
    }}
  }} catch(e) {{}}
}})();
</script>
""",
            height=0,
        )
    except Exception:
        # absolute fallback (no JS): base64 wav
        if not b64:
            return



def play_sfx_once(key: str, name: str) -> None:
    """Play SFX only once per given key (guards Streamlit reruns).

    Example:
        play_sfx_once(f"submit__{quiz_version}", "correct")
    """
    k = f"_sfx_once__{str(key)}__{str(name).strip().lower()}"
    if st.session_state.get(k):
        return
    st.session_state[k] = True
    play_sfx(name)
