# ============================================================
# ✅ 왕초보 탈출 하테나일본어 (단어 앱) - 전체 복붙용 단일 파일
# - 품사 선택 + 유형 선택(발음/뜻/한→일)
# - 로그인/회원가입(Supabase Auth) + 쿠키 세션 복원
# - 홈/퀴즈/마이페이지/관리자 라우팅
# - 오답노트 + 오답만 다시풀기
# - 맞힌 단어 제외(정복) + 초기화
# - 사운드 토글 + 테스트 재생 + 제출 후 1회 SFX
#
# ✅ CSV (data/.csv) 필수 컬럼(최종):
#   level, pos, jp_word, reading, meaning, example_jp, example_kr
#   - 문제는 jp_word(한자 포함 단어)에서 뽑음
#
# ✅ 이번 수정 반영:
#   1) 발음(読み) 문제에서 "보기 모양"으로 찍기 방지:
#      - verb: 가능한 한 '끝 2글자(히라가나 기준)' 동일 → 부족하면 '끝 1글자' 동일
#      - verb: する 동사는 보기 4개 모두 '～する'로 통일
#      - adj_i: 보기 전부 끝이 'い'로 통일(동일 pos 풀에서)
#      - adj_na: pos가 동일하므로 기본적으로 모양 찍기 난이도 상승(동사처럼 suffix 적용은 X)
#   2) 제출 후 SFX: perfect / (0.7 이상) correct / (그 외) wrong
#   3) ✅ B안 반영:
#      - 상단 품사 버튼: noun/verb/adj_i/adj_na/other(기타)
#      - 기타 선택 시: 부사/조사/접속사/감탄사 체크박스(expander) + "적용(새 문제)" 버튼
#      - 기타에서는 유형을 "뜻, 한→일" 2개만 노출 (발음 숨김)
#   4) ✅ 필수패턴: "퀴즈"가 아니라 "카드"로(품사 그룹별) expander 제공
# ============================================================

from __future__ import annotations

from pathlib import Path
import random
import pandas as pd
import streamlit as st
import unicodedata
from supabase import create_client
from streamlit_cookies_manager import EncryptedCookieManager
import streamlit.components.v1 as components
from collections import Counter
import time
import traceback
import base64
import textwrap 
import json
import html
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None


# ============================================================
# ✅ Page Config + Paths
# ============================================================
st.set_page_config(
    page_title="왕초보탈출 하테나일본어",
    page_icon="static/icon-192.png",   # 또는 "🟦"
    layout="centered",
)


# ============================================================
# ✅ Time helpers (KST)
# ============================================================
def _kst_now():
    if ZoneInfo:
        return datetime.now(ZoneInfo("Asia/Seoul"))
    return datetime.now(timezone(timedelta(hours=9)))

def _kst_today_str() -> str:
    return _kst_now().date().isoformat()

def _reset_daily_session_state():
    """Reset 'daily' state when KST date changes (combo, 'today only' excludes, etc.)."""
    today = _kst_today_str()

    # ✅ 콤보(일일 기준)
    if st.session_state.get("combo_date") != today:
        st.session_state["combo_date"] = today
        st.session_state["combo_best_today"] = 0
        st.session_state["combo_last_notice"] = 0

    # ✅ '오늘만 제외' 류 상태(일일 기준)
    if st.session_state.get("exclude_date") != today:
        st.session_state["exclude_date"] = today
        st.session_state["excluded_wrong_words"] = {}

# ============================================================
# ✅ PWA/아이콘 - set_page_config 바로 아래
# ============================================================

components.html("""
<script>
window.addEventListener("load", async () => {
  // ✅ 부모 문서(=진짜 페이지)로 주입
  const doc = (window.parent && window.parent.document) ? window.parent.document : document;

  // ✅ 작은 로그 박스(디버그용) - 가능하면 부모 body에
  const pre = doc.createElement("pre");
  pre.id = "pwa_debug";
  pre.style.cssText = "white-space:pre-wrap;font-size:12px;opacity:0.75;margin:6px 0 0;";
  pre.textContent = "";
  (doc.body || doc.documentElement).prepend(pre);

  const log = (msg) => { pre.textContent += msg + "\\n"; };

  // ✅ manifest
  let m = doc.querySelector("link[rel='manifest']");
  if (!m) { m = doc.createElement("link"); m.rel = "manifest"; doc.head.appendChild(m); }
  m.href = "/manifest.json";
  log("manifest: /manifest.json");

  // ✅ icons
  let a = doc.querySelector("link[rel='apple-touch-icon']");
  if (!a) { a = doc.createElement("link"); a.rel = "apple-touch-icon"; doc.head.appendChild(a); }
  a.setAttribute("sizes", "180x180");
  a.href = "/apple-touch-icon.png";
  log("apple-touch-icon: /apple-touch-icon.png");

  // ✅ Android/Chrome icon
  let i = doc.querySelector("link[rel='icon']");
  if (!i) { i = doc.createElement("link"); i.rel = "icon"; doc.head.appendChild(i); }
  i.setAttribute("type", "image/png");
  i.setAttribute("sizes", "192x192");
  i.href = "/icon-192.png";
  log("icon: /icon-192.png");

  // ✅ meta (iOS + theme)
  const meta = (name, content) => {
    let el = doc.querySelector(`meta[name='${name}']`);
    if (!el) { el = doc.createElement("meta"); el.name = name; doc.head.appendChild(el); }
    el.content = content;
  };
  meta("theme-color", "#0B2A6F");
  meta("apple-mobile-web-app-capable", "yes");
  meta("apple-mobile-web-app-status-bar-style", "black-translucent");

  // ✅ SW 등록은 “부모 navigator”로 시도(환경에 따라 더 안정적)
  const nav = (window.parent && window.parent.navigator) ? window.parent.navigator : navigator;

  // ✅ 먼저 sw.js가 실제로 200으로 오는지 확인
  try {
    const r = await fetch("/sw.js", { cache: "no-store" });
    log("fetch /sw.js status: " + r.status);
  } catch (e) {
    log("fetch /sw.js FAILED: " + e);
  }

  if ("serviceWorker" in nav) {
    try {
      const reg = await nav.serviceWorker.register("/sw.js");
      log("SW registered scope: " + reg.scope);
    } catch (e) {
      log("SW register FAILED: " + e);
    }
  } else {
    log("serviceWorker not supported");
  }

  log("UA: " + nav.userAgent);
});
</script>
""", height=140)




BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "beginner.csv"   # ✅ 왕초보 단어 CSV
PATTERN_CSV_PATH = BASE_DIR / "data" / "patterns_beginner.csv"
APP_URL = "https://hotena-basic-925102605904.asia-northeast3.run.app/"      # ✅ 이메일 인증 redirect용 (스트림릿 앱 주소로 교체)

# ============================================================
# ✅ App Settings
# ============================================================
SHOW_POST_SUBMIT_UI = "N"  # 제출 후 '내 최근 기록' 등을 퀴즈 페이지에 바로 보여줄지
SHOW_NAVER_TALK = "Y"
NAVER_TALK_URL = "https://talk.naver.com/W45141"

KST_TZ = "Asia/Seoul"
N = 10  # 한 번에 10문항

# ============================================================
# ✅ POS / QUIZ TYPES  (✅ B안: pos_group + other 세부 선택)
# ============================================================
POS_GROUP_OPTIONS = ["noun", "adj_i", "adj_na", "verb", "other"]
POS_LABEL_MAP = {
    "noun": "명사",
    "verb": "동사",
    "adj_i": "い형용사",
    "adj_na": "な형용사",
    "other": "기타",
}

OTHER_POS_OPTIONS = ["adv", "particle", "conj", "interj"]
OTHER_POS_LABEL_MAP = {
    "adv": "부사",
    "particle": "조사",
    "conj": "접속사",
    "interj": "감탄사",
}

quiz_label_map = {
    "reading": "발음",
    "meaning": "뜻",
    "kr2jp": "한→일",
}
QUIZ_TYPES_USER = ["reading", "meaning", "kr2jp"]
QUIZ_TYPES_ADMIN = ["reading", "meaning", "kr2jp"]  # 필요시 관리자 전용 유형 추가 가능

# ✅ 요청 반영: 기타(adv/particle/conj/interj)에서는 발음(reading) 숨김 → 그룹 단위로 other만 제한
POS_ONLY_2TYPES = {"other"}

# ============================================================
# ✅ 필수패턴(카드) - 최소 샘플(원하면 나중에 확장)
# ============================================================
PATTERNS = {
    "noun": [
        {"title": "～です", "jp": "これはXです。", "kr": "이것은 X입니다.",
         "ex": [("これは本です。", "이것은 책입니다."), ("これは私のかばんです。", "이것은 제 가방입니다.")]}
    ],
    "verb": [
        {"title": "～ます", "jp": "毎日Xます。", "kr": "매일 ~합니다.",
         "ex": [("毎日勉強します。", "매일 공부합니다."), ("駅まで歩きます。", "역까지 걷습니다.")]}
    ],
    "adj_i": [
        {"title": "い形容詞 + です", "jp": "今日はXいです。", "kr": "오늘은 ~해요.",
         "ex": [("今日は寒いです。", "오늘은 추워요."), ("この店は安いです。", "이 가게는 싸요.")]}
    ],
    "adj_na": [
        {"title": "な形容詞 + です", "jp": "この町はXです。", "kr": "이 동네는 ~해요.",
         "ex": [("この町は静かです。", "이 동네는 조용해요."), ("彼は親切です。", "그는 친절해요.")]}
    ],
    "other": [
        {"title": "だから / でも", "jp": "だから、X。 / でも、X。", "kr": "그래서 / 하지만",
         "ex": [("だから、行きません。", "그래서 안 가요."), ("でも、行きたいです。", "하지만 가고 싶어요.")]}
    ],
}

def render_pattern_cards():
    ensure_patterns_ready()

    g = str(st.session_state.get("pos_group", "noun")).lower().strip()
    pats = st.session_state.get("_patterns", {}) or {}
    items = pats.get(g, [])
    if not items:
        st.caption("이 품사에는 아직 필수패턴이 준비되지 않았어요 🙂")
        return

    st.markdown("""
<style>
.pat-card{
  border:1px solid rgba(120,120,120,0.22);
  border-radius:16px;
  padding:14px 14px;
  margin:10px 0;
  background: rgba(255,255,255,0.02);
}
.pat-title{ font-weight:900; font-size:16px; margin-bottom:6px; }
.pat-main{ font-size:14px; line-height:1.5; }
.pat-sub{ opacity:.75; font-size:13px; margin-top:6px; }
.pat-ex{ margin-top:10px; font-size:13px; line-height:1.55; }
.pat-ex b{ font-weight:900; }
</style>
""", unsafe_allow_html=True)

    for it in items[:1]:
        ex_html = ""
        for jp, kr in it.get("ex", [])[:2]:
            ex_html += f"<div class='pat-ex'><b>{jp}</b><br/>{kr}</div>"

        st.markdown(f"""
<div class="jp">
  <div class="pat-card">
    <div class="pat-title">📌 {it.get("title","")}</div>
    <div class="pat-main"><b>{it.get("jp","")}</b></div>
    <div class="pat-sub">{it.get("kr","")}</div>
    {ex_html}
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# ✅ Session Defaults  (✅ pos → pos_group / 기타 체크 세트)
# ============================================================
if "quiz_type" not in st.session_state:
    st.session_state.quiz_type = "meaning"  # 왕초보는 뜻부터 추천
if "pos_group" not in st.session_state:
    st.session_state.pos_group = "noun"

if "other_pos_selected" not in st.session_state:
    # ✅ 처음엔 기타 전체 체크
    st.session_state.other_pos_selected = set(["adv", "particle", "conj", "interj"])

if st.session_state.quiz_type not in QUIZ_TYPES_USER:
    st.session_state.quiz_type = "meaning"
if st.session_state.pos_group not in POS_GROUP_OPTIONS:
    st.session_state.pos_group = "noun"

# ✅ (안전) 제한 그룹인데 reading이 잡혀 있으면 meaning으로 강제
if str(st.session_state.get("pos_group", "noun")).lower().strip() in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
    st.session_state.quiz_type = "meaning"

# ============================================================
# ✅ CSS (폰트/버튼/카드/간격)
# ============================================================
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kosugi+Maru&family=Noto+Sans+JP:wght@400;500;700;800&display=swap" rel="stylesheet">

<style>
:root{
  --jp-rounded: "Noto Sans JP","Kosugi Maru","Hiragino Sans","Yu Gothic","Meiryo",sans-serif;
}
.jp, .jp *{
  font-family: var(--jp-rounded) !important;
  line-height:1.7;
  letter-spacing:.2px;
}

/* 메인 컨테이너 위쪽 여백 줄이기 */
div[data-testid="stAppViewContainer"] .block-container{
  padding-top: 1.0rem !important;   /* 0.5~1.5rem 사이로 취향 조절 */
}

/* Streamlit 상단 헤더(투명 영역 포함) 자체를 더 얇게 */
header[data-testid="stHeader"]{
  height: 0rem !important;
}

/* (선택) 우측 상단 Streamlit 기본 툴바 영역 숨김 */
div[data-testid="stToolbar"]{
  visibility: hidden !important;
  height: 0 !important;
}


/* 헤더 여백 */
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4{
  margin-top: 10px !important;
  margin-bottom: 8px !important;
}

/* 버튼 기본 */
div.stButton > button{
  padding: 6px 10px !important;
  font-size: 13px !important;
  line-height: 1.1 !important;
  white-space: nowrap !important;
}

/* 상단 환영바 */
.headbar{
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:12px;
  margin: 0px 0 12px 0;
}
.headtitle{
  font-size:32px;
  font-weight:900;
  line-height:1.15;
  white-space: nowrap;
}
.headhello{
  font-size: 13px;
  font-weight:700;
  opacity:.88;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 52%;
}
.headhello .mail{
  font-weight:600;
  opacity:.75;
  margin-left:8px;
}

@media (max-width: 480px){
  div[data-baseweb="button-group"] button{
    padding: 9px 12px !important;
    font-size: 14px !important;
  }
  .headhello .mail{ display:none !important; }
  .headhello{ font-size:11px; }
  .headtitle{ font-size:22px; }
}

/* ====== 상단 선택 버튼 카드 스타일 ====== */
.qtypewrap div.stButton > button{
  height: 46px !important;
  border-radius: 14px !important;
  font-weight: 900 !important;
  font-size: 14px !important;
  border: 1px solid rgba(120,120,120,0.22) !important;
  background: rgba(255,255,255,0.04) !important;
  box-shadow: none !important;
  transition: transform .08s ease, box-shadow .08s ease, filter .08s ease;
}
.qtypewrap div.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(0,0,0,0.12) !important;
  filter: brightness(1.02);
}

/* 캡션 */
.qtype_hint{
  font-size: 15px;
  opacity: .70;
  margin-top: 2px;
  margin-bottom: 10px;
  line-height: 1.2;
}

/* divider 간격(래퍼로만) */
.tight-divider hr{
  margin: 6px 0 10px 0 !important;
}

/* Q번호 아래 간격 축소 */
div[data-testid="stMarkdownContainer"] h3{
  margin-bottom: 4px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# ✅ Scroll Top Anchor + Helpers
# ============================================================
st.markdown('<div id="__TOP__"></div>', unsafe_allow_html=True)

def scroll_to_top(nonce: int = 0):
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
        height=1,
    )

def render_floating_scroll_top():
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

render_floating_scroll_top()

if st.session_state.get("_scroll_top_once"):
    st.session_state["_scroll_top_once"] = False
    st.session_state["_scroll_top_nonce"] = st.session_state.get("_scroll_top_nonce", 0) + 1
    scroll_to_top(nonce=st.session_state["_scroll_top_nonce"])

# ============================================================
# ✅ Cookies + Supabase (Cloud Run env + Streamlit secrets 겸용)
# ============================================================
import os
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from supabase import create_client

def get_cfg(key: str) -> str:
    # 1) Cloud Run: 환경변수 우선
    v = os.getenv(key)
    if v:
        return v
    # 2) Streamlit Cloud: secrets
    try:
        return st.secrets[key]
    except Exception:
        return ""

COOKIE_PASSWORD = get_cfg("COOKIE_PASSWORD")
SUPABASE_URL = get_cfg("SUPABASE_URL")
SUPABASE_ANON_KEY = get_cfg("SUPABASE_ANON_KEY")

# ✅ 필수값 체크
missing = [k for k, v in {
    "COOKIE_PASSWORD": COOKIE_PASSWORD,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
}.items() if not v]

if missing:
    st.error(f"설정값이 없습니다: {', '.join(missing)} (Cloud Run env 또는 Streamlit secrets 확인)")
    st.stop()

cookies = EncryptedCookieManager(
    prefix="hotena_beginner_",   # ✅ hotena로 통일 권장
    password=COOKIE_PASSWORD,
)
if not cookies.ready():
    st.info("잠깐만요! 곧 시작할게요🙂")
    st.stop()

sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ============================================================
# ✅ Utils: 위젯 잔상(q_...) 제거
# ============================================================
def clear_question_widget_keys():
    keys_to_del = [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith("q_")]
    for k in keys_to_del:
        st.session_state.pop(k, None)

        
# ============================================================
# ✅ FREE 관련 공통 유틸 (현재 제한 OFF 모드)
# ============================================================

def add_free_used(n: int) -> None:
    """FREE 사용량 기록. 현재 제한 OFF라 no-op."""
    return

def free_limit_reached() -> bool:
    """FREE 제한 체크. 현재 제한 OFF라 항상 False."""
    return False

def should_lock_quiz() -> bool:
    """버튼 disabled 등에 쓰는 잠금 플래그."""
    return free_limit_reached()

# ============================================================
# ✅ COMBO 시스템 (연속 정답)
# - 제출 시 10문항 기준으로 "최대 연속 정답" 계산
# - 5 콤보: 🔥 / 10 콤보: 🎉 Perfect Streak
# ============================================================

def ensure_combo_state():
    _reset_daily_session_state()
    if "combo_best_today" not in st.session_state:
        st.session_state.combo_best_today = 0
    if "combo_last_notice" not in st.session_state:
        st.session_state.combo_last_notice = 0  # 마지막으로 띄운 콤보 단계(5/10 등)

def compute_max_combo(correct_flags: list[bool]) -> int:
    mx = 0
    cur = 0
    for ok in correct_flags:
        if ok:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return int(mx)

def render_combo_celebration(max_combo: int):
    """
    max_combo 기준으로 축하 메시지/효과를 1회만 띄움
    """
    ensure_combo_state()

    # 오늘 최고 기록 갱신
    if max_combo > int(st.session_state.combo_best_today or 0):
        st.session_state.combo_best_today = int(max_combo)

    # 단계별 트리거 (중복 방지)
    # 10은 최상위이므로 먼저 체크
    if max_combo >= 10 and st.session_state.combo_last_notice < 10:
        st.session_state.combo_last_notice = 10
        st.balloons()
        st.success("🎉 Perfect Streak! 10연속 정답!")
        return

    if max_combo >= 5 and st.session_state.combo_last_notice < 5:
        st.session_state.combo_last_notice = 5
        st.success("🔥 콤보! 5연속 정답!")
        return

def render_combo_small_badge():
    """
    (선택) 상단/결과 근처에 조용히 보여주는 배지
    """
    ensure_combo_state()
    best = int(st.session_state.combo_best_today or 0)
    if best <= 0:
        return
    st.caption(f"🧠 오늘 최고 콤보: {best}연속")


# ============================================================
# ✅ POS filters (✅ B안 핵심)
# ============================================================
def get_pos_filters() -> list[str]:
    g = str(st.session_state.get("pos_group", "noun")).strip().lower()
    if g == "other":
        sel = st.session_state.get("other_pos_selected", set())
        sel = [x for x in OTHER_POS_OPTIONS if x in sel]
        return sel if sel else list(OTHER_POS_OPTIONS)
    return [g]

# ============================================================
# ✅ Key helpers (정복/제외/배너)
# ============================================================
def mastery_key(qtype: str | None = None, pos: str | None = None) -> str:
    qt = qtype or st.session_state.get("quiz_type", "meaning")
    ps = (pos or st.session_state.get("pos_group", "noun")).lower().strip()
    return f"{ps}__{qt}"

def fetch_is_admin_from_db(sb_authed, user_id: str) -> bool:
    try:
        res = (
            sb_authed.table("profiles")
            .select("is_admin")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if res and res.data is not None:
            return bool(res.data.get("is_admin", False))
    except Exception:
        return False
    return False

def is_admin() -> bool:
    cached = st.session_state.get("is_admin_cached")
    if cached is not None:
        return bool(cached)

    u = st.session_state.get("user")
    if u is None:
        st.session_state["is_admin_cached"] = False
        return False

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        st.session_state["is_admin_cached"] = False
        return False

    # ✅ 여기: fetch 함수가 없으면 False로
    if "fetch_is_admin_from_db" not in globals():
        st.session_state["is_admin_cached"] = False
        return False

    val = fetch_is_admin_from_db(sb_authed_local, u.id)
    st.session_state["is_admin_cached"] = val
    return bool(val)

def ensure_mastered_words_shape():
    if "mastered_words" not in st.session_state or not isinstance(st.session_state.mastered_words, dict):
        st.session_state.mastered_words = {}
    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        st.session_state.mastered_words.setdefault(mastery_key(qt), set())

def ensure_excluded_wrong_words_shape():
    if "excluded_wrong_words" not in st.session_state or not isinstance(st.session_state.excluded_wrong_words, dict):
        st.session_state.excluded_wrong_words = {}
    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        st.session_state.excluded_wrong_words.setdefault(mastery_key(qt), set())

def ensure_seen_words_shape():
    if "seen_words" not in st.session_state or not isinstance(st.session_state.seen_words, dict):
        st.session_state.seen_words = {}
    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        st.session_state.seen_words.setdefault(mastery_key(qt), set())     

def ensure_mastery_banner_shape():
    if "mastery_banner_shown" not in st.session_state or not isinstance(st.session_state.mastery_banner_shown, dict):
        st.session_state.mastery_banner_shown = {}
    if "mastery_done" not in st.session_state or not isinstance(st.session_state.mastery_done, dict):
        st.session_state.mastery_done = {}

    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER
    for qt in types:
        k = mastery_key(qt)
        st.session_state.mastery_banner_shown.setdefault(k, False)
        st.session_state.mastery_done.setdefault(k, False)

# ============================================================
# ✅ Answers 동기화 + Progress save helper
# ============================================================
def sync_answers_from_widgets():
    qv = st.session_state.get("quiz_version", 0)
    quiz = st.session_state.get("quiz", [])
    if not isinstance(quiz, list):
        return

    answers = st.session_state.get("answers")
    if not isinstance(answers, list) or len(answers) != len(quiz):
        st.session_state.answers = [None] * len(quiz)

    for idx in range(len(quiz)):
        widget_key = f"q_{qv}_{idx}"
        if widget_key in st.session_state:
            st.session_state.answers[idx] = st.session_state[widget_key]

def start_quiz_state(quiz_list: list, qtype: str, clear_wrongs: bool = True):
    st.session_state.quiz_version = int(st.session_state.get("quiz_version", 0)) + 1
    st.session_state.quiz_type = qtype

    if not isinstance(quiz_list, list):
        quiz_list = []

    st.session_state.quiz = quiz_list
    st.session_state.answers = [None] * len(quiz_list)

    st.session_state.submitted = False
    st.session_state.saved_this_attempt = False
    st.session_state.stats_saved_this_attempt = False
    st.session_state.session_stats_applied_this_attempt = False
    
    # ✅ 추가: 새 회차 시작 시 콤보 알림 단계 초기화
    st.session_state["combo_last_notice"] = 0

    # (선택) 디버그/추적용
    # st.session_state.free_limit_applied_ts = None

    if clear_wrongs:
        st.session_state.wrong_list = []

def mark_progress_dirty():
    st.session_state.progress_dirty = True

    sb_authed_local = get_authed_sb()
    u = st.session_state.get("user")
    if (sb_authed_local is None) or (u is None):
        return

    now = time.time()
    last = st.session_state.get("_last_progress_save_ts", 0.0)
    if now - last < 60.0:
        return

    try:
        save_progress_to_db(sb_authed_local, u.id)
        st.session_state._last_progress_save_ts = now
        st.session_state.progress_dirty = False
    except Exception:
        pass

def mark_quiz_as_seen(quiz_list: list[dict], qtype: str, pos_group: str):
    ensure_seen_words_shape()
    k = mastery_key(qtype=qtype, pos=pos_group)
    s = st.session_state.seen_words.setdefault(k, set())
    for q in (quiz_list or []):
        w = str(q.get("jp_word", "")).strip()
        if w:
            s.add(w)
            
# ============================================================
# ✅ Auth helpers (JWT refresh, sb authed)
# ============================================================
def is_jwt_expired_error(e: Exception) -> bool:
    msg = str(e).lower()
    return ("jwt expired" in msg) or ("pgrst303" in msg)

def clear_auth_everywhere():
    try:
        cookies["access_token"] = ""
        cookies["refresh_token"] = ""
        cookies.save()
    except Exception:
        pass

    for k in [
        "user", "access_token", "refresh_token",
        "login_email", "email_link_notice_shown",
        "auth_mode", "signup_done", "last_signup_ts",
        "page",
        "quiz", "answers", "submitted", "wrong_list",
        "quiz_version", "quiz_type",
        "saved_this_attempt", "stats_saved_this_attempt",
        "history", "wrong_counter", "total_counter",
        "attendance_checked", "streak_count", "did_attend_today",
        "is_admin_cached",
        "session_stats_applied_this_attempt",
        "mastered_words",
        "progress_restored", "pool_ready",
        "_sb_authed", "_sb_authed_token",
        "excluded_wrong_words",
        "mastery_banner_shown", "mastery_done",
        "pos_group",
        "other_pos_selected",
        "plan_cached",
    ]:
        st.session_state.pop(k, None)

def run_db(callable_fn):
    try:
        return callable_fn()
    except Exception as e:
        if is_jwt_expired_error(e):
            ok = refresh_session_from_cookie_if_needed(force=True)
            if ok:
                st.rerun()
            clear_auth_everywhere()
            st.warning("세션이 만료되었습니다. 다시 로그인해 주세요.")
            st.rerun()
        raise
def refresh_session_from_cookie_if_needed(force: bool = False) -> bool:
    # 이미 세션이 있으면 OK
    if not force and st.session_state.get("user") and st.session_state.get("access_token"):
        return True

    rt = cookies.get("refresh_token")
    at = cookies.get("access_token")

    # 1) refresh_token 우선
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
            st.session_state.user = refreshed.user
            st.session_state.access_token = refreshed.session.access_token
            st.session_state.refresh_token = refreshed.session.refresh_token

            u_email = getattr(refreshed.user, "email", None)
            if u_email:
                st.session_state["login_email"] = u_email.strip()

            cookies["access_token"] = refreshed.session.access_token
            cookies["refresh_token"] = refreshed.session.refresh_token
            cookies.save()
            return True

    # 2) access_token으로 유저 조회 시도
    if at:
        try:
            u = sb.auth.get_user(at)
            user_obj = getattr(u, "user", None) or getattr(u, "data", None)
            if user_obj:
                st.session_state.user = user_obj
                st.session_state.access_token = at
                if rt:
                    st.session_state.refresh_token = rt

                u_email = getattr(user_obj, "email", None)
                if u_email:
                    st.session_state["login_email"] = u_email.strip()
                return True
        except Exception:
            pass

    return False

def get_authed_sb():
    if not st.session_state.get("access_token"):
        refresh_session_from_cookie_if_needed(force=True)

    token = st.session_state.get("access_token")
    if not token:
        return None

    cached = st.session_state.get("_sb_authed")
    cached_token = st.session_state.get("_sb_authed_token")

    if cached is not None and cached_token == token:
        return cached

    sb2 = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    sb2.postgrest.auth(token)

    st.session_state["_sb_authed"] = sb2
    st.session_state["_sb_authed_token"] = token
    return sb2

def to_kst_naive(x):
    ts = pd.to_datetime(x, utc=True, errors="coerce")
    if isinstance(ts, pd.Series):
        return ts.dt.tz_convert(KST_TZ).dt.tz_localize(None)
    if pd.isna(ts):
        return ts
    return ts.tz_convert(KST_TZ).tz_localize(None)

# ============================================================
# ✅ DB functions (기존 테이블 구조 그대로 활용)
# ============================================================
def delete_all_learning_records(sb_authed, user_id):
    sb_authed.table("quiz_attempts").delete().eq("user_id", user_id).execute()
    clear_progress_in_db(sb_authed, user_id)

def ensure_profile(sb_authed, user):
    try:
        sb_authed.table("profiles").upsert(
            {"id": user.id, "email": getattr(user, "email", None)},
            on_conflict="id",
        ).execute()
    except Exception:
        pass

def mark_attendance_once(sb_authed):
    if st.session_state.get("attendance_checked"):
        return None
    try:
        res = sb_authed.rpc("mark_attendance_kst", {}).execute()
        st.session_state.attendance_checked = True
        return res.data[0] if res.data else None
    except Exception:
        st.session_state.attendance_checked = True
        return None

def save_attempt_to_db(sb_authed, user_id, user_email, pos, quiz_type, quiz_len, score, wrong_list):
    payload = {
        "user_id": user_id,
        "user_email": user_email,
        "level": str(pos),          # ✅ level 컬럼에 pos_group 저장
        "pos_mode": str(quiz_type), # ✅ pos_mode 컬럼에 유형 저장
        "quiz_len": int(quiz_len),
        "score": int(score),
        "wrong_count": int(len(wrong_list)),
        "wrong_list": wrong_list,
    }
    sb_authed.table("quiz_attempts").insert(payload).execute()

def fetch_recent_attempts(sb_authed, user_id, limit=10):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, level, pos_mode, quiz_len, score, wrong_count, wrong_list")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

def fetch_all_attempts_admin(sb_authed, limit=500):
    return (
        sb_authed.table("quiz_attempts")
        .select("created_at, user_email, level, pos_mode, quiz_len, score, wrong_count")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

def fetch_plan_from_db(sb_authed, user_id) -> str:
    try:
        res = sb_authed.table("profiles").select("plan").eq("id", user_id).single().execute()
        if res and res.data and "plan" in res.data:
            v = str(res.data["plan"] or "free").strip().lower()
            return v if v in ("free", "pro") else "free"
    except Exception:
        pass
    return "free"

def get_user_plan() -> str:
    cached = st.session_state.get("plan_cached")
    if cached in ("free", "pro"):
        return cached

    u = st.session_state.get("user")
    if u is None:
        st.session_state["plan_cached"] = "free"
        return "free"

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        st.session_state["plan_cached"] = "free"
        return "free"

    plan = fetch_plan_from_db(sb_authed_local, u.id)
    st.session_state["plan_cached"] = plan
    return plan

def is_pro() -> bool:
    # ✅ 단일 기준: profiles.plan == "pro"
    try:
        return (get_user_plan() == "pro")
    except Exception:
        return False
    
def build_word_results_bulk_payload(quiz: list[dict], answers: list, quiz_type: str, pos: str) -> list[dict]:
    items = []
    for idx, q in enumerate(quiz):
        word_key = (str(q.get("jp_word", "")).strip() or str(q.get("reading", "")).strip())
        if not word_key:
            continue
        picked = answers[idx] if idx < len(answers) else None
        is_correct = (picked == q.get("correct_text"))

        items.append(
            {
                "word_key": word_key,
                "level": "BEGINNER",
                "pos": str(pos),            # ✅ pos_group 저장(통계에서는 그룹 기준)
                "quiz_type": str(quiz_type),
                "is_correct": bool(is_correct),
            }
        )
    return items

# ============================================================
# ✅ Progress (DB 저장/복원)  (✅ pos_group + 기타 체크 저장)
# ============================================================
def save_progress_to_db(sb_authed, user_id: str):
    if "quiz" not in st.session_state or "answers" not in st.session_state:
        return

    payload = {
        "pos_group": st.session_state.get("pos_group"),
        "other_pos_selected": list(st.session_state.get("other_pos_selected", set())),
        "quiz_type": st.session_state.get("quiz_type"),
        "quiz_version": int(st.session_state.get("quiz_version", 0) or 0),
        "quiz": st.session_state.get("quiz"),
        "answers": st.session_state.get("answers"),
        "submitted": bool(st.session_state.get("submitted", False)),
    }

    sb_authed.table("profiles").upsert(
        {"id": user_id, "progress": payload},
        on_conflict="id",
    ).execute()

def clear_progress_in_db(sb_authed, user_id: str):
    sb_authed.table("profiles").upsert(
        {"id": user_id, "progress": None},
        on_conflict="id",
    ).execute()

def restore_progress_from_db(sb_authed, user_id: str):
    try:
        res = (
            sb_authed.table("profiles")
            .select("progress")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception:
        return

    if not res or not res.data:
        return

    progress = res.data.get("progress")
    if not progress:
        return

    # ✅ 구버전(progress에 pos가 있던 경우)도 최대한 흡수
    restored_group = progress.get("pos_group") or progress.get("pos") or st.session_state.get("pos_group", "noun")
    st.session_state.pos_group = restored_group

    other_sel = progress.get("other_pos_selected", None)
    if isinstance(other_sel, list):
        st.session_state.other_pos_selected = set([x for x in other_sel if x in OTHER_POS_OPTIONS])

    st.session_state.quiz_type = progress.get("quiz_type", st.session_state.get("quiz_type", "meaning"))
    st.session_state.quiz_version = int(progress.get("quiz_version", st.session_state.get("quiz_version", 0) or 0))
    st.session_state.quiz = progress.get("quiz", st.session_state.get("quiz"))
    st.session_state.answers = progress.get("answers", st.session_state.get("answers"))
    st.session_state.submitted = bool(progress.get("submitted", st.session_state.get("submitted", False)))

    if st.session_state.pos_group not in POS_GROUP_OPTIONS:
        st.session_state.pos_group = "noun"
    if st.session_state.quiz_type not in QUIZ_TYPES_USER:
        st.session_state.quiz_type = "meaning"

    # ✅ 제한 그룹이면 reading 복원되더라도 meaning으로 강제
    if str(st.session_state.get("pos_group", "noun")).lower().strip() in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
        st.session_state.quiz_type = "meaning"

    if isinstance(st.session_state.quiz, list):
        qlen = len(st.session_state.quiz)
        if not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != qlen:
            st.session_state.answers = [None] * qlen

# ============================================================
# ✅ Admin
# ============================================================
def get_available_quiz_types() -> list[str]:
    return QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER

# ✅ (신규) pos_group에 따라 가능한 유형 필터
def get_available_quiz_types_for_pos(pos_group: str) -> list[str]:
    pos_group = str(pos_group).strip().lower()
    base = get_available_quiz_types()
    if pos_group in POS_ONLY_2TYPES:
        return [t for t in base if t in ("meaning", "kr2jp")]
    return base

# ============================================================
# ✅ SOUND
# ============================================================
def _audio_autoplay_data_uri(mime: str, b: bytes):
    b64 = base64.b64encode(b).decode("utf-8")
    st.markdown(
        f"""
        <audio autoplay>
          <source src="data:{mime};base64,{b64}">
        </audio>
        """,
        unsafe_allow_html=True
    )

def play_sound_file(path: str):
    try:
        p = (BASE_DIR / path).resolve() if not str(path).startswith("/") else Path(path)
        if not p.exists():
            if is_admin():
                st.warning(f"[SOUND] 파일 없음: {p}")
            return
        data = p.read_bytes()
        mime = "audio/mpeg" if str(p).lower().endswith(".mp3") else "audio/wav"
        _audio_autoplay_data_uri(mime, data)
    except Exception as e:
        if is_admin():
            st.error("[SOUND] 재생 실패")
            st.exception(e)

def render_sound_toggle():
    if "sound_enabled" not in st.session_state:
        st.session_state.sound_enabled = False

    c1, c2, c3 = st.columns([1.4, 4.6, 4.0], vertical_alignment="center")
    with c1:
        st.session_state.sound_enabled = st.toggle("🔊", value=st.session_state.sound_enabled, label_visibility="collapsed")
    with c2:
        st.caption("소리 " + ("ON ✅" if st.session_state.sound_enabled else "OFF"))
    with c3:
        if st.session_state.sound_enabled:
            if st.button("🔈 테스트", use_container_width=True, key="btn_sound_test"):
                play_sound_file("assets/correct.mp3")

def sfx(event: str):
    if not st.session_state.get("sound_enabled", False):
        return
    mp = {
        "correct": "assets/correct.mp3",
        "wrong":   "assets/wrong.mp3",
        "perfect": "assets/perfect.mp3",
    }
    path = mp.get(event)
    if path:
        play_sound_file(path)

# ============================================================
# ✅ TTS (브라우저 Web Speech API) - 일본어 발음 버튼용
# ============================================================
def render_pronounce_button(text: str, uid: str, label: str = "🔊 발음"):
    t = (text or "").strip()
    if not t:
        return

    js_text = json.dumps(t)

    components.html(
        f"""
<div style="display:inline-block; margin-left:8px;">
  <button
    id="btn_{uid}"
    type="button"
    style="
      border:1px solid rgba(120,120,120,0.25);
      background: rgba(255,255,255,0.04);
      border-radius: 10px;
      padding: 6px 10px;
      font-weight: 900;
      cursor: pointer;
    "
  >{label}</button>
</div>

<script>
(function(){{
  const text = {js_text};
  const btn = document.getElementById("btn_{uid}");
  if(!btn) return;

  let speakingNow = false;

  function pickFemaleJaVoice(vs){{
    if (!vs || !vs.length) return null;

    // ✅ 일본어 보이스만 추림
    const ja = vs.filter(v => String(v.lang || "").toLowerCase().startsWith("ja"));
    if (!ja.length) return null;

    // ✅ "여성"로 추정되는 이름/키워드 우선 (환경별로 다름)
    const prefer = /(kyoko|haruka|ayumi|nanami|hina|sakura|female|woman|girl)/i;
    const avoid  = /(otoya|takumi|male|man|boy)/i;

    // 1) prefer 강하게 매칭
    let cand = ja.find(v => prefer.test(String(v.name || "")));
    if (cand) return cand;

    // 2) avoid는 피하고 남은 것 중 첫번째
    cand = ja.find(v => !avoid.test(String(v.name || "")));
    if (cand) return cand;

    // 3) 그냥 첫번째 일본어 보이스
    return ja[0];
  }}

  function speakJA(){{
    try {{
      const w = window;
      if (!w.speechSynthesis) {{
        alert("이 기기/브라우저는 음성 재생을 지원하지 않습니다.");
        return;
      }}

      if (speakingNow) return;
      speakingNow = true;

      w.speechSynthesis.cancel();

      const u = new SpeechSynthesisUtterance(String(text));
      u.lang = "ja-JP";

      // ✅ “여성 느낌” 쪽으로 살짝 보정 (너무 올리면 부자연스러울 수 있어요)
      u.rate  = 1.0;
      u.pitch = 1.15;

      u.onend   = () => {{ speakingNow = false; }};
      u.onerror = () => {{ speakingNow = false; }};

      let spoken = false;

      const pickAndSpeak = () => {{
        if (spoken) return;
        spoken = true;

        try {{ w.speechSynthesis.onvoiceschanged = null; }} catch(e) {{}}

        const vs = w.speechSynthesis.getVoices() || [];
        const v = pickFemaleJaVoice(vs);
        if (v) u.voice = v;

        w.speechSynthesis.speak(u);
      }};

      const vsNow = w.speechSynthesis.getVoices();
      if (vsNow && vsNow.length) {{
        pickAndSpeak();
      }} else {{
        w.speechSynthesis.onvoiceschanged = () => pickAndSpeak();
        setTimeout(() => pickAndSpeak(), 250);
      }}
    }} catch(e) {{
      speakingNow = false;
      console.log(e);
    }}
  }}

  btn.addEventListener("click", speakJA, {{ once:false }});
}})();
</script>
        """,
        height=43,
    )
# ============================================================
# ✅ Onboarding (첫 방문 이용안내)
# ============================================================

ONBOARDING_COOKIE_KEY = "onboarding_seen_v1"

def has_seen_onboarding() -> bool:
    try:
        v = cookies.get(ONBOARDING_COOKIE_KEY)
        if str(v).strip() == "1":
            return True
    except Exception:
        pass
    return False

def mark_seen_onboarding():
    try:
        cookies[ONBOARDING_COOKIE_KEY] = "1"
        cookies.save()
    except Exception:
        pass

def render_onboarding_card(expanded=True):
    with st.expander("📘 처음 오셨나요? 60초 이용안내", expanded=expanded):
        st.markdown("""
**이 앱은 하루 10문항 루틴 퀴즈입니다.**

1️⃣ 홈 → ▶ 오늘의 퀴즈 시작  
2️⃣ 퀴즈 → 품사 선택 → 유형 선택  
3️⃣ 제출 → 오답은 다시 풀기  
4️⃣ 🔊 소리 ON 후 테스트 버튼 확인

막히면 네이버톡 상담으로 문의하세요 🙂
""")

        if st.button("✅ 확인했어요 (다음부터 안 보기)", use_container_width=True):
            mark_seen_onboarding()
            st.rerun()

# ============================================================
# ✅ Login UI
# ============================================================
def auth_box():
    st.markdown("<div style='max-width:520px; margin:0 auto;'>", unsafe_allow_html=True)

    st.markdown(
        '<div class="jp" style="font-weight:900; font-size:16px; margin:6px 0 6px 0;">로그인</div>',
        unsafe_allow_html=True
    )

    qp = st.query_params
    came_from_email_link = any(k in qp for k in ["code", "token", "type", "access_token", "refresh_token"])
    if came_from_email_link and not st.session_state.get("email_link_notice_shown"):
        st.session_state.email_link_notice_shown = True
        st.session_state.auth_mode = "login"
        st.success("이메일 인증(또는 링크 확인)이 완료되었습니다. 이제 로그인해 주세요.")

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    mode = st.radio(
        label="",
        options=["login", "signup"],
        format_func=lambda x: "로그인" if x == "login" else "회원가입",
        horizontal=True,
        key="auth_mode_radio",
        index=0 if st.session_state.auth_mode == "login" else 1,
    )
    st.session_state.auth_mode = mode

    if st.session_state.get("signup_done"):
        st.success("회원가입 요청 완료! 이메일 인증이 필요할 수 있어요. 메일함을 확인한 뒤 로그인해 주세요.")
        st.session_state.signup_done = False

    if mode == "login":
        email = st.text_input("이메일", key="login_email_input")
        pw = st.text_input("비밀번호", type="password", key="login_pw_input")

        st.caption("비밀번호는 **회원가입 때 8자리 이상**으로 설정했을 가능성이 큽니다.")
        if pw and len(pw) < 8:
            st.warning(f"입력하신 비밀번호가 {len(pw)}자리입니다. 회원가입 때 8자리 이상으로 설정하셨다면 더 길게 입력해 주세요.")

        if st.button("로그인", use_container_width=True, key="btn_login"):
            if not email or not pw:
                st.warning("이메일과 비밀번호를 입력해주세요.")
                st.stop()

            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pw})
                st.session_state.user = res.user
                st.session_state["login_email"] = email.strip()

                if res.session and res.session.access_token:
                    st.session_state.access_token = res.session.access_token
                    st.session_state.refresh_token = res.session.refresh_token
                    cookies["access_token"] = res.session.access_token
                    cookies["refresh_token"] = res.session.refresh_token
                    cookies.save()
                else:
                    st.warning("로그인은 되었지만 세션 토큰이 없습니다. 이메일 인증 상태를 확인해주세요.")
                    st.session_state.access_token = None
                    st.session_state.refresh_token = None

                st.session_state.pop("is_admin_cached", None)
                st.success("로그인 완료!")
                st.rerun()

            except Exception:
                st.error("로그인 실패: 이메일/비밀번호 또는 이메일 인증 상태를 확인해주세요.")
                st.stop()

    else:
        email = st.text_input("이메일", key="signup_email")
        pw = st.text_input("비밀번호", type="password", key="signup_pw")

        pw_len = len(pw) if pw else 0
        pw_ok = pw_len >= 8
        email_ok = bool(email and email.strip())

        st.caption("비밀번호는 **8자리 이상**으로 설정해 주세요.")
        if pw and not pw_ok:
            st.warning(f"비밀번호가 너무 짧습니다. (현재 {pw_len}자) 8자리 이상으로 입력해 주세요.")

        if st.button("회원가입", use_container_width=True, disabled=not (email_ok and pw_ok), key="btn_signup"):
            try:
                last = st.session_state.get("last_signup_ts", 0.0)
                now = time.time()
                if now - last < 8:
                    st.warning("요청이 너무 빠릅니다. 잠시 후 다시 시도해주세요.")
                    st.stop()
                st.session_state.last_signup_ts = now

                sb.auth.sign_up(
                    {
                        "email": email,
                        "password": pw,
                        "options": {"email_redirect_to": APP_URL},
                    }
                )

                st.session_state.signup_done = True
                st.session_state.auth_mode = "login"
                st.session_state["login_email"] = email.strip()
                st.rerun()

            except Exception as e:
                msg = str(e).lower()
                if "rate limit" in msg and "email" in msg:
                    st.session_state.auth_mode = "login"
                    st.session_state["login_email"] = email.strip()
                    st.session_state.signup_done = False
                    st.warning("이메일 발송 제한에 걸렸습니다. 잠시 후 다시 시도해주세요.")
                    st.rerun()

                st.error("회원가입 실패(에러 확인):")
                st.exception(e)
                st.stop()

    st.markdown("</div>", unsafe_allow_html=True)

def require_login():
    if st.session_state.get("user") is None:
        st.markdown(
            """
<div class="jp" style="margin: 8px 0 14px 0;">
  <div style="
    border:1px solid rgba(120,120,120,0.18);
    border-radius:18px;
    padding:16px 16px;
    background: rgba(255,255,255,0.03);
  ">
    <div style="font-weight:900; font-size:22px; line-height:1.15;">
      ✨ 왕초보 탈출 하테나일본어
    </div>
    <div style="margin-top:6px; opacity:.85; font-size:13px; line-height:1.55;">
      하루 10문항으로 가볍게 루틴을 만들어요.<br/>
      정답은 저장되고, 오답은 다시 풀 수 있어요.
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        auth_box()
        st.stop()

# ✅ 첫 방문 자동 노출
if not has_seen_onboarding():
    render_onboarding_card(expanded=True)
else:
    if st.button("📘 이용안내 다시보기", use_container_width=True):
        render_onboarding_card(expanded=True)

# ============================================================
# ✅ 네이버톡 배너 (제출 후만)
# ============================================================
def render_naver_talk():
    st.divider()
    st.markdown(
        f"""
<style>
@keyframes floaty {{
  0% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-6px); }}
  100% {{ transform: translateY(0); }}
}}
@keyframes ping {{
  0% {{ transform: scale(1); opacity: 0.9; }}
  70% {{ transform: scale(2.2); opacity: 0; }}
  100% {{ transform: scale(2.2); opacity: 0; }}
}}
.floating-naver-talk,
.floating-naver-talk:visited,
.floating-naver-talk:hover,
.floating-naver-talk:active {{
  position: fixed;
  right: 18px;
  bottom: 90px;
  z-index: 99999;
  text-decoration: none !important;
  color: inherit !important;
}}
.floating-wrap {{
  position: relative;
  animation: floaty 2.2s ease-in-out infinite;
}}
.talk-btn {{
  background: #03C75A;
  color: #fff;
  border: 0;
  border-radius: 999px;
  padding: 14px 18px;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 12px 28px rgba(0,0,0,0.22);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  line-height: 1.1;
  text-decoration: none !important;
}}
.talk-btn:hover {{ filter: brightness(0.95); }}
.talk-text small {{
  display: block;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.95;
  margin-top: 2px;
}}
.badge {{
  position: absolute;
  top: -6px;
  right: -6px;
  width: 12px;
  height: 12px;
  background: #ff3b30;
  border-radius: 999px;
  box-shadow: 0 6px 14px rgba(0,0,0,0.25);
}}
.badge::after {{
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  background: rgba(255,59,48,0.55);
  animation: ping 1.2s ease-out infinite;
}}
@media (max-width: 600px) {{
  .floating-naver-talk {{ bottom: 110px; right: 14px; }}
  .talk-btn {{ padding: 13px 16px; font-size: 14px; }}
  .talk-text small {{ font-size: 11px; }}
}}
</style>

<a class="floating-naver-talk" href="{NAVER_TALK_URL}" target="_blank" rel="noopener noreferrer">
  <div class="floating-wrap">
    <span class="badge"></span>
    <button class="talk-btn" type="button">
      <span>💬</span>
      <span class="talk-text">
        1:1 하테나쌤 상담
        <small>수강신청 문의하기</small>
      </span>
    </button>
  </div>
</a>
""",
        unsafe_allow_html=True,
    )

# ============================================================
# ✅ Top Card (마이페이지/관리자/로그아웃)
# ============================================================

def nav_to(page: str, scroll_top: bool = True):
    st.session_state.page = page
    if scroll_top:
        st.session_state["_scroll_top_once"] = True

def nav_logout():
    clear_auth_everywhere()

def render_topcard():
    u = st.session_state.get("user")
    if not u:
        return

    st.markdown('<div class="topcard">', unsafe_allow_html=True)
    left, r_admin, r_my, r_logout = st.columns([6.0, 1.2, 2.4, 2.4], vertical_alignment="center")

    with left:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    with r_admin:
        if is_admin():
            st.button("📊", use_container_width=True, help="관리자 대시보드",
                      key="topcard_btn_nav_admin", on_click=nav_to, args=("admin",))
        else:
            st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    with r_my:
        st.button("📌 마이페이지", use_container_width=True, help="내 학습 기록/오답 TOP10 보기",
                  key="topcard_btn_nav_my", on_click=nav_to, args=("my",))

    with r_logout:
        st.button("🚪 로그아웃", use_container_width=True, help="로그아웃",
                  key="topcard_btn_logout", on_click=nav_logout)

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ✅ CSV Load Pool  (✅ CSV 최종 스펙 반영)
# ============================================================
READ_KW = dict(
    dtype=str,
    keep_default_na=False,
    na_values=["nan", "NaN", "NULL", "null", "None", "none"],
)

@st.cache_data(show_spinner=False)
def load_pool(csv_path_str: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path_str, **READ_KW)

    # ✅ CSV 최종 필수 컬럼
    required_cols = {"level", "pos", "jp_word", "reading", "meaning", "example_jp", "example_kr"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV 필수 컬럼 누락: {sorted(list(missing))}")

    def _nfkc(s):
        return unicodedata.normalize("NFKC", str(s or "")).strip()

    df["level"] = df["level"].apply(_nfkc).str.upper().str.strip()
    df["pos"] = df["pos"].apply(_nfkc).str.lower().str.strip()
    df["jp_word"] = df["jp_word"].apply(_nfkc).str.strip()
    df["reading"] = df["reading"].apply(_nfkc).str.strip()
    df["meaning"] = df["meaning"].apply(_nfkc).str.strip()
    df["example_jp"] = df["example_jp"].apply(_nfkc).str.strip()
    df["example_kr"] = df["example_kr"].apply(_nfkc).str.strip()

    # 빈 줄 제거
    df = df[
        (df["pos"] != "") &
        (df["jp_word"] != "") &
        (df["reading"] != "") &
        (df["meaning"] != "")
    ].copy()

    return df.reset_index(drop=True)

def ensure_pool_ready():
    if st.session_state.get("pool_ready") and isinstance(st.session_state.get("_pool"), pd.DataFrame):
        return
    try:
        pool = load_pool(str(CSV_PATH))
    except Exception as e:
        st.error(f"단어 데이터 로드 실패: {e}")
        st.stop()

    if len(pool) < N:
        st.error(f"단어가 부족합니다: pool={len(pool)} (N={N})")
        st.stop()

    st.session_state["_pool"] = pool
    st.session_state["pool_ready"] = True

    if is_admin():
        with st.expander("🔎 디버그: 품사별 단어 수", expanded=False):
            st.write(pool["pos"].value_counts(dropna=False))
            st.write("CSV_PATH =", str(CSV_PATH))

@st.cache_data(show_spinner=False)
def load_patterns(csv_path_str: str) -> dict[str, list[dict]]:
    df = pd.read_csv(csv_path_str, **READ_KW)

    required = {
        "pos_group", "title", "jp", "kr",
        "ex1_jp", "ex1_kr", "ex2_jp", "ex2_kr"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"patterns CSV 필수 컬럼 누락: {sorted(list(missing))}")

    def _nfkc(s):
        return unicodedata.normalize("NFKC", str(s or "")).strip()

    for c in df.columns:
        df[c] = df[c].apply(_nfkc)

    df["pos_group"] = df["pos_group"].str.lower().str.strip()

    # 빈 행 제거(최소 title/jp는 있어야 카드가 의미가 있음)
    df = df[(df["pos_group"] != "") & (df["title"] != "") & (df["jp"] != "")].copy()

    out: dict[str, list[dict]] = {}
    for _, r in df.iterrows():
        g = r["pos_group"]
        item = {
            "title": r["title"],
            "jp": r["jp"],
            "kr": r["kr"],
            "ex": [
                (r.get("ex1_jp", ""), r.get("ex1_kr", "")),
                (r.get("ex2_jp", ""), r.get("ex2_kr", "")),
            ],
        }
        # 예문이 비어있으면 제거
        item["ex"] = [(a, b) for (a, b) in item["ex"] if a and b]

        out.setdefault(g, []).append(item)

    return out

def ensure_patterns_ready():
    if st.session_state.get("_patterns_ready") and isinstance(st.session_state.get("_patterns"), dict):
        return
    try:
        pats = load_patterns(str(PATTERN_CSV_PATH))
    except Exception as e:
        st.error(f"필수패턴 CSV 로드 실패: {e}")
        st.stop()

    st.session_state["_patterns"] = pats
    st.session_state["_patterns_ready"] = True

# ============================================================
# ✅ Quiz Logic
# ============================================================
def _nfkc_str(x) -> str:
    return unicodedata.normalize("NFKC", str(x or "")).strip()

def _has_kanji(s: str) -> bool:
    """
    jp_word에 '한자'가 1글자라도 포함되어 있으면 True.
    (발음 문제에서 '히라가나만 있는 단어'를 제외하기 위한 용도)
    """
    s = _nfkc_str(s)
    for ch in s:
        code = ord(ch)
        # CJK Unified Ideographs (일반 한자 범위)
        if 0x4E00 <= code <= 0x9FFF:
            return True
        # CJK Extension A (일부 한자)
        if 0x3400 <= code <= 0x4DBF:
            return True
    return False

def _to_hira(s: str) -> str:
    s = _nfkc_str(s)
    out = []
    for ch in s:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)

def _uniq(xs):
    out, seen = [], set()
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def _suffix_kana(x: str, n: int) -> str:
    s = _to_hira(_nfkc_str(x))
    return s[-n:] if len(s) >= n else s

def _is_suru_verb(reading: str) -> bool:
    r = _to_hira(_nfkc_str(reading))
    return r.endswith("する")

def _jp_okurigana_suffix(jp_word: str) -> str:
    """
    jp_word 끝에서 '오쿠리가나(히라/가타카나 연속 꼬리)'를 뽑아 히라가나로 반환.
    """
    s = _nfkc_str(jp_word)
    if not s:
        return ""
    i = len(s)
    while i > 0:
        ch = s[i-1]
        code = ord(ch)
        is_hira = (0x3040 <= code <= 0x309F)
        is_kata = (0x30A0 <= code <= 0x30FF)
        if is_hira or is_kata:
            i -= 1
        else:
            break
    tail = s[i:]
    tail = _to_hira(tail)
    return tail

def _safe_suffix_hira(x: str, n: int) -> str:
    xh = _to_hira(_nfkc_str(x))
    return xh[-n:] if len(xh) >= n else xh

def _pick_reading_wrongs(candidates: list[str], correct: str, pos: str, jp_word: str = "", k: int = 3) -> list[str]:
    correct_nf = _nfkc_str(correct)
    cands = _uniq([_nfkc_str(c) for c in candidates if _nfkc_str(c) and _nfkc_str(c) != correct_nf])
    if len(cands) < k:
        return []

    correct_h = _to_hira(correct_nf)

    okuri = _jp_okurigana_suffix(jp_word)
    okuri = _to_hira(okuri)

    ok2 = okuri[-2:] if len(okuri) >= 2 else ""
    ok1 = okuri[-1:] if len(okuri) >= 1 else ""

    cor2 = _safe_suffix_hira(correct_h, 2)
    cor1 = _safe_suffix_hira(correct_h, 1)

    target2 = ok2 if ok2 else cor2
    target1 = ok1 if ok1 else cor1

    want_suru = (target2 == "する") or correct_h.endswith("する")

    def score(c: str) -> int:
        ch = _to_hira(c)
        sc = 0
        if want_suru:
            if ch.endswith("する"):
                sc += 100
            else:
                sc -= 50
        if target2 and _safe_suffix_hira(ch, 2) == target2:
            sc += 60
        if target1 and _safe_suffix_hira(ch, 1) == target1:
            sc += 25
        if ch == correct_h:
            sc -= 999
        return sc

    ranked = sorted(cands, key=lambda x: score(x), reverse=True)

    same2 = [c for c in ranked if target2 and _safe_suffix_hira(c, 2) == target2]
    same1 = [c for c in ranked if target1 and _safe_suffix_hira(c, 1) == target1]

    out = []
    for c in same2:
        if c not in out:
            out.append(c)
        if len(out) == k:
            return out
    for c in same1:
        if c not in out:
            out.append(c)
        if len(out) == k:
            return out
    for c in ranked:
        if c not in out:
            out.append(c)
        if len(out) == k:
            return out

    return out[:k]

def make_question(row: pd.Series, qtype: str, pool: pd.DataFrame) -> dict:
    jp = str(row.get("jp_word", "")).strip()
    rd = str(row.get("reading", "")).strip()
    mn = str(row.get("meaning", "")).strip()
    pos = str(row.get("pos", "")).strip().lower()
    ex_jp = str(row.get("example_jp", "")).strip()
    ex_kr = str(row.get("example_kr", "")).strip()

    # ✅ 같은 실제 pos 풀
    pool_pos = pool[pool["pos"].astype(str).str.strip().str.lower() == pos].copy()

    if qtype == "reading":
        prompt = f"{jp}의 발음은?"
        correct = rd
        candidates = (
            pool_pos.loc[pool_pos["reading"] != correct, "reading"]
            .dropna().drop_duplicates().tolist()
        )
        wrongs = _pick_reading_wrongs(candidates, correct, pos=pos, jp_word=jp, k=3)
        if len(wrongs) < 3:
            c2 = _uniq([str(x).strip() for x in candidates if str(x).strip()])
            if len(c2) < 3:
                st.error(f"오답 후보 부족(발음): pos={pos}, 후보={len(c2)}개")
                st.stop()
            wrongs = random.sample(c2, 3)

    elif qtype == "meaning":
        prompt = f"{jp}의 뜻은?"
        correct = mn
        candidates = (
            pool_pos.loc[pool_pos["meaning"] != correct, "meaning"]
            .dropna().drop_duplicates().tolist()
        )
        if len(candidates) < 3:
            st.error(f"오답 후보 부족(뜻): pos={pos}, 후보={len(candidates)}개")
            st.stop()
        wrongs = random.sample(candidates, 3)

    elif qtype == "kr2jp":
        prompt = f"'{mn}'의 일본어는?"
        correct = jp
        candidates = (
            pool_pos.loc[pool_pos["jp_word"] != correct, "jp_word"]
            .dropna().astype(str).str.strip().tolist()
        )
        candidates = [x for x in dict.fromkeys(candidates) if x]
        if len(candidates) < 3:
            st.error(f"오답 후보 부족(한→일): pos={pos}, 후보={len(candidates)}개")
            st.stop()
        wrongs = random.sample(candidates, 3)

    else:
        raise ValueError(f"Unknown qtype: {qtype}")

    choices = wrongs + [correct]
    random.shuffle(choices)

    return {
        "prompt": prompt,
        "choices": choices,
        "correct_text": correct,
        "jp_word": jp,
        "reading": rd,
        "meaning": mn,
        "pos": pos,
        "qtype": qtype,
        "example_jp": ex_jp,
        "example_kr": ex_kr,
    }

def build_quiz(qtype: str, pos_group: str) -> list[dict]:
    # ✅ 안전장치: 제한 그룹에서는 reading 강제 금지
    pos_group = str(pos_group).strip().lower()
    qtype = str(qtype).strip()
    if pos_group in POS_ONLY_2TYPES and qtype == "reading":
        qtype = "meaning"

    ensure_pool_ready()
    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()
    ensure_seen_words_shape()

    pool = st.session_state["_pool"]

    pos_filters = get_pos_filters()
    base_pos = pool[pool["pos"].astype(str).str.strip().str.lower().isin(pos_filters)].copy()

    # ✅ 발음(reading) 문제: jp_word에 한자가 없는(히라가나만 등) 단어는 제외
    if qtype == "reading":
        base_pos = base_pos[base_pos["jp_word"].apply(_has_kanji)].copy()

    if len(base_pos) < N:
        st.warning(f"{POS_LABEL_MAP.get(pos_group,pos_group)} 단어가 부족합니다. (현재 {len(base_pos)}개 / 필요 {N}개)")
        return []

    k = mastery_key(qtype=qtype, pos=pos_group)

    seen = st.session_state.get("seen_words", {}).get(k, set())
    mastered = st.session_state.get("mastered_words", {}).get(k, set())
    excluded = st.session_state.get("excluded_wrong_words", {}).get(k, set())

    blocked = set()
    if seen:
        blocked |= set(seen)          # ✅ 한 번이라도 출제된 건 전부 제외
    if mastered:
        blocked |= set(mastered)      # (겹쳐도 무관)
    if excluded:
        blocked |= set(excluded)    

    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:
        if not blocked:
            return df
        keys = df["jp_word"].astype(str).str.strip()
        return df[~keys.isin(blocked)].copy()

    base = _filter_blocked(base_pos)

    if len(base) < N:
        st.session_state.setdefault("mastery_done", {})
        st.session_state.mastery_done[k] = True
        return []

    sampled = base.sample(n=N, replace=False).reset_index(drop=True)
    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]


# ============================================================
# ✅ Quiz builders for review (TOP10 / wrong retry)
# ✅ 반드시 Admin/My pages(마이페이지) 보다 위에 있어야 합니다.
# ============================================================

def build_quiz_from_word_keys(word_keys: list[str], qtype: str, pos_group: str) -> list[dict]:
    # ✅ 안전장치
    pos_group = str(pos_group).strip().lower()
    qtype = str(qtype).strip()
    if pos_group in POS_ONLY_2TYPES and qtype == "reading":
        qtype = "meaning"

    ensure_pool_ready()
    pool = st.session_state["_pool"]

    keys = [str(x).strip() for x in (word_keys or []) if str(x).strip()]
    keys = list(dict.fromkeys(keys))
    if not keys:
        st.warning("TOP10 단어가 비어 있어요.")
        return []

    pos_filters = get_pos_filters()
    df = pool[
        (pool["pos"].astype(str).str.strip().str.lower().isin(pos_filters))
        & (pool["jp_word"].astype(str).str.strip().isin(keys))
    ].copy()

    if qtype == "reading":
        df = df[df["jp_word"].apply(_has_kanji)].copy()

    if df.empty:
        st.warning("TOP10 단어를 현재 풀(품사/기타 선택)에서 찾지 못했어요. (필터 조건 확인)")
        return []

    df = df.sample(frac=1).reset_index(drop=True)
    return [make_question(df.iloc[i], qtype, pool) for i in range(len(df))]

def build_quiz_from_wrongs(wrong_list: list, qtype: str, pos_group: str) -> list[dict]:
    # ✅ 안전장치
    pos_group = str(pos_group).strip().lower()
    qtype = str(qtype).strip()
    if pos_group in POS_ONLY_2TYPES and qtype == "reading":
        qtype = "meaning"

    ensure_pool_ready()
    pool = st.session_state["_pool"]

    # ✅ wrong_list에서 jp_word 키 뽑기
    wrong_words = []
    for w in (wrong_list or []):
        key = str(w.get("단어", "")).strip()
        if key:
            wrong_words.append(key)
    wrong_words = list(dict.fromkeys(wrong_words))

    if not wrong_words:
        st.warning("현재 오답 노트가 비어 있어요. 🙂")
        return []

    # ✅ 현재 화면의 pos 필터(기타면 체크된 세부 품사들)
    pos_filters = get_pos_filters()

    # ✅ pool에서 오답 단어 + 현재 pos필터로 매칭
    retry_df = pool[
        (pool["pos"].astype(str).str.strip().str.lower().isin(pos_filters))
        & (pool["jp_word"].astype(str).str.strip().isin(wrong_words))
    ].copy()

    if retry_df.empty:
        st.error("오답 단어를 현재 풀(품사/기타 선택)에서 찾지 못했습니다. (jp_word 매칭/필터 확인)")
        return []

    # ✅ reading이면 ‘한자 포함 jp_word’만
    if qtype == "reading":
        retry_df = retry_df[retry_df["jp_word"].apply(_has_kanji)].copy()
        if retry_df.empty:
            st.warning("오답 중 ‘한자 포함 단어’가 없어 발음 문제로는 복습할 수 없어요. (뜻/한→일로 복습 추천)")
            return []

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)

    # ✅ 오답 전체를 문제로 만들되, 최대 N개까지만 (원하면 삭제 가능)
    if len(retry_df) > N:
        retry_df = retry_df.head(N).copy()

    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]

# ============================================================
# ✅ Admin/My pages
# ============================================================
def render_admin_dashboard():
    st.subheader("📊 관리자 대시보드")

    if not is_admin():
        st.error("접근 권한이 없습니다.")
        st.session_state.page = "quiz"
        st.stop()

    if st.button("← 돌아가기", use_container_width=True, key="btn_admin_back"):
        st.session_state.page = "quiz"
        st.rerun()

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        st.warning("세션 토큰이 없습니다. 다시 로그인해 주세요.")
        return

    st.caption("※ 확장 가능: 전체 기록 조회 등")
    if st.button("최근 전체 기록 100개 보기", use_container_width=True, key="btn_admin_fetch100"):
        try:
            res = run_db(lambda: fetch_all_attempts_admin(sb_authed_local, limit=100))
            if not res.data:
                st.info("기록이 없습니다.")
            else:
                df = pd.DataFrame(res.data)
                df["created_at"] = to_kst_naive(df["created_at"])
                df["품사"] = df["level"].map(lambda x: POS_LABEL_MAP.get(str(x), str(x)))
                df["유형"] = df["pos_mode"].map(lambda x: quiz_label_map.get(str(x), str(x)))
                st.dataframe(df, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("조회 실패")
            st.write(str(e))

def render_my_dashboard():
    st.subheader("📌 내 대시보드")

    if st.button("← 돌아가기", use_container_width=True, key="btn_my_back"):
        st.session_state.page = "quiz"
        st.rerun()

    u = st.session_state.get("user")
    if not u:
        st.warning("로그인 정보가 없습니다. 다시 로그인해 주세요.")
        st.session_state.page = "quiz"
        st.stop()

    user_id_local = getattr(u, "id", None)
    if not user_id_local:
        st.warning("유저 ID를 찾지 못했습니다. 다시 로그인해 주세요.")
        st.session_state.page = "quiz"
        st.stop()

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        st.warning("세션 토큰이 없습니다. 다시 로그인해 주세요.")
        return

    with st.expander("🗑️ 전체 학습 기록 완전 초기화", expanded=False):
        st.warning("이 작업은 되돌릴 수 없습니다.\n(최근 기록 / 오답 TOP10 / 진행중 복원까지 모두 초기화됩니다.)")
        agree = st.checkbox("초기화에 동의합니다.", key="chk_reset_all_agree")
        if st.button("🗑️ 지금 완전 초기화", type="primary", use_container_width=True, key="btn_reset_all_records"):
            if not agree:
                st.error("초기화에 동의해 주세요.")
                st.stop()

            try:
                run_db(lambda: delete_all_learning_records(sb_authed_local, user_id_local))

                clear_question_widget_keys()
                for k in [
                    "history", "wrong_counter", "total_counter",
                    "wrong_list", "quiz", "answers", "submitted",
                    "saved_this_attempt", "stats_saved_this_attempt",
                    "session_stats_applied_this_attempt",
                    "quiz_version",
                    "mastered_words", "mastery_banner_shown", "mastery_done",
                    "progress_restored", "pool_ready",
                    "excluded_wrong_words",
                ]:
                    st.session_state.pop(k, None)

                st.success("✅ 전체 학습 기록이 완전 초기화되었습니다.")
                st.session_state.page = "quiz"
                st.rerun()

            except Exception as e:
                st.error("초기화 실패: RLS 정책(삭제 권한) 또는 테이블/컬럼 확인이 필요합니다.")
                st.exception(e)

    try:
        res = run_db(lambda: fetch_recent_attempts(sb_authed_local, user_id_local, limit=50))
    except Exception as e:
        st.info("기록을 불러오지 못했습니다.")
        st.write(str(e))
        return

    if not res.data:
        st.info("아직 저장된 기록이 없습니다. 문제를 풀고 제출하면 기록이 쌓여요.")
        return

    hist = pd.DataFrame(res.data).copy()
    hist["created_at"] = to_kst_naive(hist["created_at"])
    hist["품사"] = hist["level"].map(lambda x: POS_LABEL_MAP.get(str(x), str(x)))
    hist["유형"] = hist["pos_mode"].map(lambda x: quiz_label_map.get(str(x), str(x)))
    hist["정답률"] = (hist["score"] / hist["quiz_len"]).fillna(0.0)

    avg_rate = float(hist["정답률"].mean() * 100)
    best = int(hist["score"].max())
    last_score = int(hist.iloc[0]["score"])
    last_total = int(hist.iloc[0]["quiz_len"])

    dashboard_html = f"""
    <style>
    .stat-grid{{
      display:grid;
      grid-template-columns: repeat(3, 1fr);
      gap:12px;
      margin: 6px 0 6px 0;
    }}
    .stat-card{{
      border:1px solid rgba(120,120,120,0.25);
      border-radius:18px;
      padding:14px 14px;
      background: rgba(255,255,255,0.02);
    }}
    .stat-label{{
      font-size:12px;
      font-weight:800;
      opacity:.72;
      line-height:1.2;
    }}
    .stat-value{{
      margin-top:6px;
      font-size:22px;
      font-weight:900;
      line-height:1.1;
    }}
    .stat-sub{{
      margin-top:6px;
      font-size:12px;
      opacity:.70;
      line-height:1.2;
    }}
    @media (max-width: 520px){{
      .stat-grid{{ grid-template-columns: 1fr; }}
      .stat-value{{ font-size:24px; }}
    }}
    </style>

    <div class="jp">
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">최근 평균(최대 50회)</div>
          <div class="stat-value">{avg_rate:.0f}%</div>
          <div class="stat-sub">정답률 기준</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">최고 점수</div>
          <div class="stat-value">{best} / {last_total}</div>
          <div class="stat-sub">최근 기록 중 최고</div>
        </div>

        <div class="stat-card">
          <div class="stat-label">최근 점수</div>
          <div class="stat-value">{last_score} / {last_total}</div>
          <div class="stat-sub">가장 최근 1회</div>
        </div>
      </div>
    </div>
    """
    components.html(dashboard_html, height=330)

    st.markdown("### ❌ 자주 틀린 단어 TOP10 (최근 50회)")

    counter = Counter()
    for row in (res.data or []):
        wl = row.get("wrong_list") or []
        if isinstance(wl, list):
            for w in wl:
                word = str(w.get("단어", "")).strip()
                if word:
                    counter[word] += 1

    if not counter:
        st.caption("아직 오답 데이터가 충분하지 않습니다. 몇 번 더 풀면 TOP10이 생겨요 🙂")
        return

    st.markdown(
        """
<style>
.wt10-card{
  border:1px solid rgba(120,120,120,0.25);
  border-radius:18px;
  padding:14px 16px;
  margin:12px 0;
  background: rgba(255,255,255,0.02);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:14px;
}
.wt10-left{
  display:flex;
  flex-direction:column;
  gap:6px;
  min-width: 0;
}
.wt10-title{
  font-size:18px;
  font-weight:900;
  line-height:1.15;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.wt10-sub{
  font-size:13px;
  opacity:.75;
}
.wt10-badge{
  border:1px solid rgba(120,120,120,0.25);
  background: rgba(255,255,255,0.03);
  border-radius:999px;
  padding:7px 12px;
  font-size:13px;
  font-weight:900;
  white-space:nowrap;
}
</style>
""",
        unsafe_allow_html=True,
    )

    def render_wrong_top10_card(rank: int, word: str, cnt: int):
        st.markdown(
            f"""
<div class="jp">
  <div class="wt10-card">
    <div class="wt10-left">
      <div class="wt10-title">#{rank} {word}</div>
      <div class="wt10-sub">최근 50회 기준</div>
    </div>
    <div class="wt10-badge">오답 {cnt}회</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    top10 = counter.most_common(10)
    for i, (w, cnt) in enumerate(top10, start=1):
        render_wrong_top10_card(i, str(w), int(cnt))

    # ✅ TOP10 시험보기 버튼
    top10_words = [str(w) for (w, _) in top10]

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("🧪 TOP10으로 시험보기", type="primary", use_container_width=True, key="btn_top10_quiz"):
        clear_question_widget_keys()

        quiz = build_quiz_from_word_keys(
            word_keys=top10_words,
            qtype=st.session_state.get("quiz_type", "meaning"),
            pos_group=st.session_state.get("pos_group", "noun"),
        )

        start_quiz_state(quiz, st.session_state.get("quiz_type", "meaning"), clear_wrongs=True)
        st.session_state.page = "quiz"
        st.session_state["_scroll_top_once"] = True
        st.rerun()

# ============================================================
# ✅ Home
# ============================================================
def reset_quiz_state_only():
    clear_question_widget_keys()
    for k in ["quiz", "answers", "submitted", "wrong_list",
              "saved_this_attempt", "stats_saved_this_attempt",
              "session_stats_applied_this_attempt"]:
        st.session_state.pop(k, None)

def go_quiz_from_home():
    reset_quiz_state_only()

    # ✅ 콤보 알림 단계 리셋(오늘 최고 기록은 유지)
    st.session_state["combo_last_notice"] = 0
    
    st.session_state.page = "quiz"
    st.session_state["_scroll_top_once"] = True

MODE_LABEL_MAP = {
    "reading": "발음",
    "meaning": "뜻",
    "kr2jp": "한→일",
    # 필요하면 더 추가
}

def mode_label(x: str) -> str:
    x = "" if x is None else str(x).strip().lower()
    return MODE_LABEL_MAP.get(x, x)  # 없는 값이면 원문 유지


# ============================================================
# ✅ [KANJI] 한자 퀴즈 (words_kanji.csv / 레벨 5단계)
# - 선우님이 주신 app.py 로직을 "통합 앱" 구조에 맞게 이식
# - 세션키 충돌 방지: kanji_* prefix 사용
# ============================================================

KANJI_APP_CODE = "# ============================================================\n# \u2705 [A] Imports + Page Config (\ud30c\uc77c \ucd5c\uc0c1\ub2e8, st.* \ud638\ucd9c\ubcf4\ub2e4 \uba3c\uc800)\n# ============================================================\nfrom pathlib import Path\nimport random\nimport pandas as pd\nimport streamlit as st\nimport unicodedata\nfrom supabase import create_client\nfrom streamlit_cookies_manager import EncryptedCookieManager\nimport streamlit.components.v1 as components\nfrom collections import Counter\nimport time\nimport traceback\nimport base64\nimport io\nimport textwrap\n\n# ============================================================\n# \u2705 [SOUND] \uc0ac\uc6b4\ub4dc \uc720\ud2f8 (\ubaa8\ubc14\uc77c \uc790\ub3d9\uc7ac\uc0dd \uc815\ucc45 \ub300\uc751)\n# ============================================================\ndef _audio_autoplay_data_uri(mime: str, b: bytes):\n    b64 = base64.b64encode(b).decode(\"utf-8\")\n    # autoplay\ub294 \ub9c9\ud790 \uc218 \uc788\uc74c. \uadf8\ub798\ub3c4 \"\uc0ac\uc6a9\uc790 \ud074\ub9ad \uc9c1\ud6c4\"\uc5d4 \uc131\uacf5\ub960\uc774 \uc62c\ub77c\uac10\n    st.markdown(\n        f\"\"\"\n        <audio autoplay>\n          <source src=\"data:{mime};base64,{b64}\">\n        </audio>\n        \"\"\",\n        unsafe_allow_html=True\n    )\n\ndef play_sound_file(path: str):\n    \"\"\"assets/*.mp3 or *.wav \ud30c\uc77c \uc7ac\uc0dd (\ub514\ubc84\uadf8 \uac00\ub2a5)\"\"\"\n    try:\n        p = (BASE_DIR / path).resolve() if not str(path).startswith(\"/\") else Path(path)\n        if not p.exists():\n            # \u2705 \uc870\uc6a9\ud788 \uc0bc\ud0a4\uc9c0 \ub9d0\uace0, \uad00\ub9ac\uc790\ub9cc \ubcf4\uc774\uac8c\ub77c\ub3c4 \ud45c\uc2dc\n            if is_admin():\n                st.warning(f\"[SOUND] \ud30c\uc77c \uc5c6\uc74c: {p}\")\n            return\n\n        data = p.read_bytes()\n        mime = \"audio/mpeg\" if str(p).lower().endswith(\".mp3\") else \"audio/wav\"\n        _audio_autoplay_data_uri(mime, data)\n\n    except Exception as e:\n        if is_admin():\n            st.error(\"[SOUND] \uc7ac\uc0dd \uc2e4\ud328\")\n            st.exception(e)\n\ndef render_sound_toggle():\n    \"\"\"\n    \u2705 \ud575\uc2ec:\n    - \ud1a0\uae00 \ud074\ub9ad\uc5d0 st.rerun()\uc744 \uac78\uba74 '\uc0ac\uc6a9\uc790 \uc81c\uc2a4\ucc98'\uac00 \ub04a\uaca8\uc11c \uc18c\ub9ac\uac00 \ub354 \uc548 \ub0a8\n    - \ub300\uc2e0 \ud1a0\uae00\uc740 \uc0c1\ud0dc\ub9cc \ubc14\uafb8\uace0,\n      \uc0ac\uc6a9\uc790\uac00 '\ud14c\uc2a4\ud2b8 \uc7ac\uc0dd' \ubc84\ud2bc\uc744 \ub20c\ub7ec \ube0c\ub77c\uc6b0\uc800\uc5d0 \uc624\ub514\uc624 \ud5c8\uc6a9\uc744 \"\ud55c \ubc88\" \ud574\uc8fc\uac8c \ud568\n    \"\"\"\n    if \"sound_enabled\" not in st.session_state:\n        st.session_state.sound_enabled = False\n\n    c1, c2, c3 = st.columns([1.4, 4.6, 4.0], vertical_alignment=\"center\")\n\n    with c1:\n        st.session_state.sound_enabled = st.toggle(\"\ud83d\udd0a\", value=st.session_state.sound_enabled, label_visibility=\"collapsed\")\n\n    with c2:\n        st.caption(\"\uc18c\ub9ac \" + (\"ON \u2705\" if st.session_state.sound_enabled else \"OFF\"))\n\n    with c3:\n        # \u2705 \uc0ac\uc6a9\uc790 \ud074\ub9ad\uc73c\ub85c \ud55c \ubc88 \uc7ac\uc0dd(\uad8c\ud55c/\ud5c8\uc6a9 \ud2b8\ub9ac\uac70)\n        if st.session_state.sound_enabled:\n            if st.button(\"\ud83d\udd08 \ud14c\uc2a4\ud2b8\", use_container_width=True, key=\"btn_sound_test\"):\n                play_sound_file(\"assets/correct.mp3\")\n\ndef sfx(event: str):\n    \"\"\"\n    event:\n      - \"correct\" : \uc815\ub2f5\n      - \"wrong\"   : \uc624\ub2f5\n      - \"perfect\" : 100\uc810\n    \"\"\"\n    if not st.session_state.get(\"sound_enabled\", False):\n        return\n\n    mp = {\n        \"correct\": \"assets/correct.mp3\",\n        \"wrong\":   \"assets/wrong.mp3\",\n        \"perfect\": \"assets/perfect.mp3\",\n    }\n    path = mp.get(event)\n    if path:\n        play_sound_file(path)\n\n# ============================================================\n# \u2705 Streamlit \uae30\ubcf8 \uc124\uc815 (\ucd5c\uc0c1\ub2e8)\n# ============================================================\nst.markdown(\"\"\"\n<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n<link href=\"https://fonts.googleapis.com/css2?family=Kosugi+Maru&family=Noto+Sans+JP:wght@400;500;700;800&display=swap\" rel=\"stylesheet\">\n\n<style>\n:root{ --jp-rounded: \"Noto Sans JP\",\"Kosugi Maru\",\"Hiragino Sans\",\"Yu Gothic\",\"Meiryo\",sans-serif; }\n.jp, .jp *{ font-family: var(--jp-rounded) !important; line-height:1.7; letter-spacing:.2px; }\n\ndiv[data-testid=\"stRadio\"] * ,\ndiv[data-baseweb=\"radio\"] * ,\nlabel[data-baseweb=\"radio\"] * {\n  font-family: var(--jp-rounded) !important;\n}\n\n/* \ud5e4\ub354 \uc5ec\ubc31 */\ndiv[data-testid=\"stMarkdownContainer\"] h3,\ndiv[data-testid=\"stMarkdownContainer\"] h2,\ndiv[data-testid=\"stMarkdownContainer\"] h3,\ndiv[data-testid=\"stMarkdownContainer\"] h4{\n  margin-top: 10px !important;\n  margin-bottom: 8px !important;\n}\n\n/* \ubc84\ud2bc \uae30\ubcf8 */\ndiv.stButton > button {\n  padding: 6px 10px !important;\n  font-size: 13px !important;\n  line-height: 1.1 !important;\n  white-space: nowrap !important;\n}\n\n/* \uc0c1\ub2e8 \ud658\uc601\ubc14 */\n.headbar{\n  display:flex;\n  align-items:flex-end;\n  justify-content:space-between;\n  gap:12px;\n  margin: 10px 0 16px 0;\n}\n.headtitle{\n  font-size:34px;\n  font-weight:900;\n  line-height:1.15;\n  white-space: nowrap;\n}\n.headhello{\n  font-size: 13px;\n  font-weight:700;\n  opacity:.88;\n  white-space: nowrap;\n  overflow: hidden;\n  text-overflow: ellipsis;\n  max-width: 52%;\n}\n.headhello .mail{\n  font-weight:600;\n  opacity:.75;\n  margin-left:8px;\n}\n\n@media (max-width: 480px){\n  div[data-baseweb=\"button-group\"] button{\n    padding: 9px 12px !important;\n    font-size: 14px !important;\n  }\n  .headhello .mail{ display:none !important; }\n  .headhello{ font-size:11px; }\n  .headtitle{ font-size:24px; }\n}\n\n/* ====== \ub808\ubca8 \ubc84\ud2bc \uce74\ub4dc \uc2a4\ud0c0\uc77c ====== */\n.qtypewrap div.stButton > button{\n  height: 46px !important;\n  border-radius: 14px !important;\n  font-weight: 900 !important;\n  font-size: 14px !important;\n  border: 1px solid rgba(120,120,120,0.22) !important;\n  background: rgba(255,255,255,0.04) !important;\n  box-shadow: none !important;\n  transition: transform .08s ease, box-shadow .08s ease, filter .08s ease;\n}\n.qtypewrap div.stButton > button:hover{\n  transform: translateY(-1px);\n  box-shadow: 0 12px 26px rgba(0,0,0,0.12) !important;\n  filter: brightness(1.02);\n}\n\n/* \ucea1\uc158(\ub808\ubca8 \uc548\ub0b4) */\n.qtype_hint{\n  font-size: 15px;\n  opacity: .70;\n  margin-top: 2px;\n  margin-bottom: 10px;\n  line-height: 1.2;\n}\n\n/* \u2705 divider \uc804\uc5ed hr \ub9c8\uc9c4\uc740 \uc704\ud5d8\ud558\ub2c8 '\ub798\ud37c'\ub85c\ub9cc \uc4f0\ub294 \uac78 \uad8c\uc7a5\n   \uc544\ub798 \uc804\uc5ed hr\uc740 \uc8fc\uc11d \ucc98\ub9ac \ucd94\ucc9c\n*/\n/*\nhr{\n  margin: 3px 0 14px 0 !important;\n}\n*/\n.tight-divider hr{\n  margin: 6px 0 10px 0 !important;\n}\n/* \u2705 Q\ubc88\ud638(subheader) \uc544\ub798 \uac04\uaca9\ub9cc \uc904\uc774\uae30 */\ndiv[data-testid=\"stMarkdownContainer\"] h3{\n  margin-bottom: 4px !important;\n}\n</style>\n\"\"\", unsafe_allow_html=True)\n\n# ============================================================\n# \u2705 [D] Scroll Top Anchor + Helpers\n# ============================================================\nst.markdown('<div id=\"__TOP__\"></div>', unsafe_allow_html=True)\n\ndef scroll_to_top(nonce: int = 0):\n    components.html(\n        f\"\"\"\n        <script>\n        (function () {{\n          const doc = window.parent.document;\n          const targets = [\n            doc.querySelector('[data-testid=\"stAppViewContainer\"]'),\n            doc.querySelector('[data-testid=\"stMain\"]'),\n            doc.querySelector('section.main'),\n            doc.documentElement,\n            doc.body\n          ].filter(Boolean);\n\n          const go = () => {{\n            try {{\n              const top = doc.getElementById(\"__TOP__\");\n              if (top) top.scrollIntoView({{behavior: \"auto\", block: \"start\"}});\n\n              targets.forEach(t => {{\n                if (t && typeof t.scrollTo === \"function\") t.scrollTo({{top: 0, left: 0, behavior: \"auto\"}});\n                if (t) t.scrollTop = 0;\n              }});\n              window.parent.scrollTo(0, 0);\n              window.scrollTo(0, 0);\n            }} catch(e) {{}}\n          }};\n\n          go();\n          requestAnimationFrame(go);\n          setTimeout(go, 50);\n          setTimeout(go, 150);\n          setTimeout(go, 350);\n          setTimeout(go, 800);\n        }})();\n        </script>\n        <!-- nonce:{nonce} -->\n        \"\"\",\n        height=1,\n    )\n\ndef render_floating_scroll_top():\n    components.html(\n        \"\"\"\n<script>\n(function(){\n  const doc = window.parent.document;\n  if (doc.getElementById(\"__FAB_TOP__\")) return;\n\n  const btn = doc.createElement(\"button\");\n  btn.id = \"__FAB_TOP__\";\n  btn.textContent = \"\u2191\";\n\n  btn.style.position = \"fixed\";\n  btn.style.right = \"14px\";\n  btn.style.zIndex = \"2147483647\";\n  btn.style.width = \"46px\";\n  btn.style.height = \"46px\";\n  btn.style.borderRadius = \"999px\";\n  btn.style.border = \"1px solid rgba(120,120,120,0.25)\";\n  btn.style.background = \"rgba(0,0,0,0.55)\";\n  btn.style.color = \"#fff\";\n  btn.style.fontSize = \"18px\";\n  btn.style.fontWeight = \"900\";\n  btn.style.boxShadow = \"0 10px 22px rgba(0,0,0,0.25)\";\n  btn.style.cursor = \"pointer\";\n  btn.style.userSelect = \"none\";\n  btn.style.display = \"flex\";\n  btn.style.alignItems = \"center\";\n  btn.style.justifyContent = \"center\";\n  btn.style.opacity = \"0\";\n\n  const applyDeviceVisibility = () => {\n    try {\n      const w = window.parent.innerWidth || window.innerWidth;\n      if (w >= 801) btn.style.display = \"none\";\n      else btn.style.display = \"flex\";\n    } catch(e) {}\n  };\n\n  const goTop = () => {\n    try {\n      const top = doc.getElementById(\"__TOP__\");\n      if (top) top.scrollIntoView({behavior:\"smooth\", block:\"start\"});\n\n      const targets = [\n        doc.querySelector('[data-testid=\"stAppViewContainer\"]'),\n        doc.querySelector('[data-testid=\"stMain\"]'),\n        doc.querySelector('section.main'),\n        doc.documentElement,\n        doc.body\n      ].filter(Boolean);\n\n      targets.forEach(t => {\n        if (t && typeof t.scrollTo === \"function\") t.scrollTo({top:0, left:0, behavior:\"smooth\"});\n        if (t) t.scrollTop = 0;\n      });\n\n      window.parent.scrollTo(0,0);\n      window.scrollTo(0,0);\n    } catch(e) {}\n  };\n\n  btn.addEventListener(\"click\", goTop);\n\n  const mount = () => doc.querySelector('[data-testid=\"stAppViewContainer\"]') || doc.body;\n\n  const BASE = 18;\n  const EXTRA = 34;\n\n  const reposition = () => {\n    try {\n      const vv = window.parent.visualViewport || window.visualViewport;\n      const innerH = window.parent.innerHeight || window.innerHeight;\n      const hiddenBottom = vv ? Math.max(0, innerH - vv.height - (vv.offsetTop || 0)) : 0;\n      btn.style.bottom = (BASE + EXTRA + hiddenBottom) + \"px\";\n      btn.style.opacity = \"1\";\n    } catch(e) {\n      btn.style.bottom = \"220px\";\n      btn.style.opacity = \"1\";\n    }\n    applyDeviceVisibility();\n  };\n\n  const tryAttach = (n=0) => {\n    const root = mount();\n    if (!root) {\n      if (n < 30) return setTimeout(() => tryAttach(n+1), 50);\n      return;\n    }\n    root.appendChild(btn);\n    reposition();\n    setTimeout(reposition, 50);\n    setTimeout(reposition, 200);\n    setTimeout(reposition, 600);\n  };\n\n  tryAttach();\n  window.parent.addEventListener(\"resize\", reposition, {passive:true});\n\n  const vv = window.parent.visualViewport || window.visualViewport;\n  if (vv) {\n    vv.addEventListener(\"resize\", reposition, {passive:true});\n    vv.addEventListener(\"scroll\", reposition, {passive:true});\n  }\n})();\n</script>\n        \"\"\",\n        height=1,\n    )\n\nrender_floating_scroll_top()\n\nif st.session_state.get(\"_scroll_top_once\"):\n    st.session_state[\"_scroll_top_once\"] = False\n    st.session_state[\"_scroll_top_nonce\"] = st.session_state.get(\"_scroll_top_nonce\", 0) + 1\n    scroll_to_top(nonce=st.session_state[\"_scroll_top_nonce\"])\n\n# ============================================================\n# \u2705 Cookies\n# ============================================================\ncookies = EncryptedCookieManager(\n    prefix=\"hatena_kanji_\",\n    password=st.secrets[\"COOKIE_PASSWORD\"],\n)\nif not cookies.ready():\n    st.info(\"\uc7a0\uae50\ub9cc\uc694! \uace7 \uc2dc\uc791\ud560\uac8c\uc694\ud83d\ude42\")\n    st.stop()\n\nif \"SUPABASE_URL\" not in st.secrets or \"SUPABASE_ANON_KEY\" not in st.secrets:\n    st.error(\"Supabase Secrets\uac00 \uc124\uc815\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4. (SUPABASE_URL / SUPABASE_ANON_KEY)\")\n    st.stop()\n\n# ============================================================\n# \u2705 Supabase \uc5f0\uacb0\n# ============================================================\nSUPABASE_URL = st.secrets[\"SUPABASE_URL\"]\nSUPABASE_ANON_KEY = st.secrets[\"SUPABASE_ANON_KEY\"]\nsb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)\n\n# ============================================================\n# \u2705 \uc0c1\uc218/\uc124\uc815\n# ============================================================\nSHOW_POST_SUBMIT_UI = \"N\"\nSHOW_NAVER_TALK = \"Y\"\nNAVER_TALK_URL = \"https://talk.naver.com/W45141\"\nAPP_URL = \"https://hotenaquiztestapp-5wiha4zfuvtnq4qgxdhq72.streamlit.app/\"\nKST_TZ = \"Asia/Seoul\"\n\nN = 10\nBASE_DIR = Path(__file__).resolve().parent\nCSV_PATH = BASE_DIR / \"data\" / \"words_kanji.csv\"\n\nquiz_label_map = {\n    \"reading\": \"\ubc1c\uc74c\",\n    \"meaning\": \"\ub73b\",\n    \"kr2jp\": \"\ud55c\u2192\uc77c\",\n}\nquiz_label_for_table = quiz_label_map.copy()\n\nQUIZ_TYPES_USER = [\"reading\", \"meaning\", \"kr2jp\"]\nQUIZ_TYPES_ADMIN = [\"reading\", \"meaning\", \"kr2jp\"]\n\nLEVEL_OPTIONS = [\"N5\", \"N4\", \"N3\", \"N2\", \"N1\"]\nLEVEL_LABEL_MAP = {lv: lv for lv in LEVEL_OPTIONS}\n\n# \u2705 \uc138\uc158 \uae30\ubcf8\uac12(\uac00\uc7a5 \uc911\uc694)\nif \"quiz_type\" not in st.session_state:\n    st.session_state.quiz_type = \"reading\"\nif \"level\" not in st.session_state:\n    st.session_state.level = \"N5\"\n\n# (\ud639\uc2dc \uc774\uc0c1\uac12\uc774 \ub4e4\uc5b4\uc62c \ub54c \uc548\uc804\uc7a5\uce58)\nif st.session_state.level not in LEVEL_OPTIONS:\n    st.session_state.level = \"N5\"\nif st.session_state.quiz_type not in QUIZ_TYPES_USER:\n    st.session_state.quiz_type = \"reading\"\n  \n# ============================================================\n# \u2705 Utils: \uc704\uc82f \uc794\uc0c1(q_...) \uc81c\uac70\n# ============================================================\ndef clear_question_widget_keys():\n    keys_to_del = [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith(\"q_\")]\n    for k in keys_to_del:\n        st.session_state.pop(k, None)\n\ndef mastery_key(qtype: str | None = None, level: str | None = None) -> str:\n    qt = qtype or st.session_state.get(\"quiz_type\", \"reading\")\n    lv = (level or st.session_state.get(\"level\", \"N5\")).upper()\n    return f\"{lv}__{qt}\"\n\ndef ensure_mastered_words_shape():\n    if \"mastered_words\" not in st.session_state or not isinstance(st.session_state.mastered_words, dict):\n        st.session_state.mastered_words = {}\n    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER\n    for qt in types:\n        st.session_state.mastered_words.setdefault(mastery_key(qt), set())\n\ndef ensure_excluded_wrong_words_shape():\n    if \"excluded_wrong_words\" not in st.session_state or not isinstance(st.session_state.excluded_wrong_words, dict):\n        st.session_state.excluded_wrong_words = {}\n    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER\n    for qt in types:\n        st.session_state.excluded_wrong_words.setdefault(mastery_key(qt), set())\n\ndef ensure_mastery_banner_shape():\n    if \"mastery_banner_shown\" not in st.session_state or not isinstance(st.session_state.mastery_banner_shown, dict):\n        st.session_state.mastery_banner_shown = {}\n    if \"mastery_done\" not in st.session_state or not isinstance(st.session_state.mastery_done, dict):\n        st.session_state.mastery_done = {}\n\n    types = QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER\n    for qt in types:\n        k = mastery_key(qt)\n        st.session_state.mastery_banner_shown.setdefault(k, False)\n        st.session_state.mastery_done.setdefault(k, False)\n\n# ============================================================\n# \u2705 [G] Answers \ub3d9\uae30\ud654 + Progress save helper\n# ============================================================\ndef sync_answers_from_widgets():\n    qv = st.session_state.get(\"quiz_version\", 0)\n    quiz = st.session_state.get(\"quiz\", [])\n    if not isinstance(quiz, list):\n        return\n\n    answers = st.session_state.get(\"answers\")\n    if not isinstance(answers, list) or len(answers) != len(quiz):\n        st.session_state.answers = [None] * len(quiz)\n\n    for idx in range(len(quiz)):\n        widget_key = f\"q_{qv}_{idx}\"\n        if widget_key in st.session_state:\n            st.session_state.answers[idx] = st.session_state[widget_key]\n\ndef mark_progress_dirty():\n    st.session_state.progress_dirty = True\n    st.session_state._progress_dirty_ts = time.time()\n\n    sb_authed_local = get_authed_sb()\n    u = st.session_state.get(\"user\")\n    if (sb_authed_local is None) or (u is None):\n        return\n\n    now = time.time()\n    last = st.session_state.get(\"_last_progress_save_ts\", 0.0)\n    if now - last < 10.0:\n        return\n\n    try:\n        save_progress_to_db(sb_authed_local, u.id)\n        st.session_state._last_progress_save_ts = now\n        st.session_state.progress_dirty = False\n    except Exception:\n        pass\n\ndef start_quiz_state(quiz_list: list, qtype: str, clear_wrongs: bool = True):\n    st.session_state.quiz_version = int(st.session_state.get(\"quiz_version\", 0)) + 1\n    st.session_state.quiz_type = qtype\n\n    if not isinstance(quiz_list, list):\n        quiz_list = []\n\n    st.session_state.quiz = quiz_list\n    st.session_state.answers = [None] * len(quiz_list)\n\n    st.session_state.submitted = False\n    st.session_state.saved_this_attempt = False\n    st.session_state.stats_saved_this_attempt = False\n    st.session_state.session_stats_applied_this_attempt = False\n\n    if clear_wrongs:\n        st.session_state.wrong_list = []\n\n# ============================================================\n# \u2705 JWT \ub9cc\ub8cc \uac10\uc9c0 + \uc138\uc158 \uac31\uc2e0 + DB \ud638\ucd9c \ub798\ud37c\n# ============================================================\n# ============================================================\n# \u2705 [H] Auth: JWT \ub9cc\ub8cc \uac10\uc9c0 + refresh + get_authed_sb\n# ============================================================\ndef is_jwt_expired_error(e: Exception) -> bool:\n    msg = str(e).lower()\n    return (\"jwt expired\" in msg) or (\"pgrst303\" in msg)\n\ndef clear_auth_everywhere():\n    try:\n        cookies[\"access_token\"] = \"\"\n        cookies[\"refresh_token\"] = \"\"\n        cookies.save()\n    except Exception:\n        pass\n\n    for k in [\n        \"user\", \"access_token\", \"refresh_token\",\n        \"login_email\", \"email_link_notice_shown\",\n        \"auth_mode\", \"signup_done\", \"last_signup_ts\",\n        \"page\",\n        \"quiz\", \"answers\", \"submitted\", \"wrong_list\",\n        \"quiz_version\", \"quiz_type\",\n        \"saved_this_attempt\", \"stats_saved_this_attempt\",\n        \"history\", \"wrong_counter\", \"total_counter\",\n        \"attendance_checked\", \"streak_count\", \"did_attend_today\",\n        \"is_admin_cached\",\n        \"session_stats_applied_this_attempt\",\n        \"mastered_words\",\n        \"progress_restored\", \"pool_ready\",\n        \"_sb_authed\", \"_sb_authed_token\",\n        \"excluded_wrong_words\",\n        \"mastery_banner_shown\", \"mastery_done\",\n    ]:\n        st.session_state.pop(k, None)\n\ndef run_db(callable_fn):\n    try:\n        return callable_fn()\n    except Exception as e:\n        if is_jwt_expired_error(e):\n            ok = refresh_session_from_cookie_if_needed(force=True)\n            if ok:\n                st.rerun()\n            clear_auth_everywhere()\n            st.warning(\"\uc138\uc158\uc774 \ub9cc\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n            st.rerun()\n        raise\n\ndef refresh_session_from_cookie_if_needed(force: bool = False) -> bool:\n    if not force and st.session_state.get(\"user\") and st.session_state.get(\"access_token\"):\n        return True\n\n    rt = cookies.get(\"refresh_token\")\n    at = cookies.get(\"access_token\")\n\n    if rt:\n        try:\n            refreshed = sb.auth.refresh_session(rt)\n            if refreshed and refreshed.session and refreshed.session.access_token:\n                st.session_state.user = refreshed.user\n                st.session_state.access_token = refreshed.session.access_token\n                st.session_state.refresh_token = refreshed.session.refresh_token\n\n                u_email = getattr(refreshed.user, \"email\", None)\n                if u_email:\n                    st.session_state[\"login_email\"] = u_email.strip()\n\n                cookies[\"access_token\"] = refreshed.session.access_token\n                cookies[\"refresh_token\"] = refreshed.session.refresh_token\n                cookies.save()\n                return True\n        except Exception:\n            pass\n\n    if at:\n        try:\n            u = sb.auth.get_user(at)\n            user_obj = getattr(u, \"user\", None) or getattr(u, \"data\", None) or None\n            if user_obj:\n                st.session_state.user = user_obj\n                st.session_state.access_token = at\n                if rt:\n                    st.session_state.refresh_token = rt\n                u_email = getattr(user_obj, \"email\", None)\n                if u_email:\n                    st.session_state[\"login_email\"] = u_email.strip()\n                return True\n        except Exception:\n            pass\n\n    return False\n\ndef get_authed_sb():\n    if not st.session_state.get(\"access_token\"):\n        refresh_session_from_cookie_if_needed(force=True)\n\n    token = st.session_state.get(\"access_token\")\n    if not token:\n        return None\n\n    cached = st.session_state.get(\"_sb_authed\")\n    cached_token = st.session_state.get(\"_sb_authed_token\")\n\n    if cached is not None and cached_token == token:\n        return cached\n\n    sb2 = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)\n    sb2.postgrest.auth(token)\n\n    st.session_state[\"_sb_authed\"] = sb2\n    st.session_state[\"_sb_authed_token\"] = token\n    return sb2\n\ndef to_kst_naive(x):\n    ts = pd.to_datetime(x, utc=True, errors=\"coerce\")\n    if isinstance(ts, pd.Series):\n        return ts.dt.tz_convert(KST_TZ).dt.tz_localize(None)\n    if pd.isna(ts):\n        return ts\n    return ts.tz_convert(KST_TZ).tz_localize(None)\n\n# ============================================================\n# \u2705 DB \ud568\uc218 (\uae30\uc874 \uadf8\ub300\ub85c \ud65c\uc6a9)\n# ============================================================\ndef delete_all_learning_records(sb_authed, user_id):\n    sb_authed.table(\"quiz_attempts\").delete().eq(\"user_id\", user_id).execute()\n    clear_progress_in_db(sb_authed, user_id)\n\ndef ensure_profile(sb_authed, user):\n    try:\n        sb_authed.table(\"profiles\").upsert(\n            {\"id\": user.id, \"email\": getattr(user, \"email\", None)},\n            on_conflict=\"id\",\n        ).execute()\n    except Exception:\n        pass\n\ndef mark_attendance_once(sb_authed):\n    if st.session_state.get(\"attendance_checked\"):\n        return None\n    try:\n        res = sb_authed.rpc(\"mark_attendance_kst\", {}).execute()\n        st.session_state.attendance_checked = True\n        return res.data[0] if res.data else None\n    except Exception:\n        st.session_state.attendance_checked = True\n        return None\n\ndef save_attempt_to_db(sb_authed, user_id, user_email, level, quiz_type, quiz_len, score, wrong_list):\n    # \u2705 pos_mode \uceec\ub7fc\uba85\uc740 \uadf8\ub300\ub85c \ub450\ub418, \uac12\uc740 quiz_type \ub123\uc5b4\uc11c \ud14c\uc774\ube14 \ubcc0\uacbd \uc5c6\uc774 \uc720\uc9c0\n    payload = {\n        \"user_id\": user_id,\n        \"user_email\": user_email,\n        \"level\": level,\n        \"pos_mode\": quiz_type,\n        \"quiz_len\": int(quiz_len),\n        \"score\": int(score),\n        \"wrong_count\": int(len(wrong_list)),\n        \"wrong_list\": wrong_list,\n    }\n    sb_authed.table(\"quiz_attempts\").insert(payload).execute()\n\ndef fetch_recent_attempts(sb_authed, user_id, limit=10):\n    return (\n        sb_authed.table(\"quiz_attempts\")\n        .select(\"created_at, level, pos_mode, quiz_len, score, wrong_count, wrong_list\")\n        .eq(\"user_id\", user_id)\n        .order(\"created_at\", desc=True)\n        .limit(limit)\n        .execute()\n    )\n\ndef fetch_all_attempts_admin(sb_authed, limit=500):\n    return (\n        sb_authed.table(\"quiz_attempts\")\n        .select(\"created_at, user_email, level, pos_mode, quiz_len, score, wrong_count\")\n        .order(\"created_at\", desc=True)\n        .limit(limit)\n        .execute()\n    )\n\ndef fetch_is_admin_from_db(sb_authed, user_id):\n    try:\n        res = sb_authed.table(\"profiles\").select(\"is_admin\").eq(\"id\", user_id).single().execute()\n        if res and res.data and \"is_admin\" in res.data:\n            return bool(res.data[\"is_admin\"])\n    except Exception:\n        pass\n    return False\n\ndef build_word_results_bulk_payload(quiz: list[dict], answers: list, quiz_type: str, level: str) -> list[dict]:\n    items = []\n    for idx, q in enumerate(quiz):\n        word_key = (str(q.get(\"jp_word\", \"\")).strip() or str(q.get(\"reading\", \"\")).strip())\n        if not word_key:\n            continue\n\n        picked = answers[idx] if idx < len(answers) else None\n        is_correct = (picked == q.get(\"correct_text\"))\n\n        items.append(\n            {\n                \"word_key\": word_key,\n                \"level\": str(level),\n                \"pos\": \"\",  # \u2705 \ud55c\uc790\ud034\uc988\ub294 \ud488\uc0ac \uc5c6\uc74c \u2192 \ube48 \uac12\n                \"quiz_type\": str(quiz_type),\n                \"is_correct\": bool(is_correct),\n            }\n        )\n    return items\n\n# ============================================================\n# \u2705 Progress (DB \uc800\uc7a5/\ubcf5\uc6d0)\n# ============================================================\ndef save_progress_to_db(sb_authed, user_id: str):\n    if \"quiz\" not in st.session_state or \"answers\" not in st.session_state:\n        return\n\n    payload = {\n        \"quiz_type\": st.session_state.get(\"quiz_type\"),\n        \"quiz_version\": int(st.session_state.get(\"quiz_version\", 0) or 0),\n        \"quiz\": st.session_state.get(\"quiz\"),\n        \"answers\": st.session_state.get(\"answers\"),\n        \"submitted\": bool(st.session_state.get(\"submitted\", False)),\n    }\n\n    sb_authed.table(\"profiles\").upsert(\n        {\"id\": user_id, \"progress\": payload},\n        on_conflict=\"id\",\n    ).execute()\n\ndef clear_progress_in_db(sb_authed, user_id: str):\n    sb_authed.table(\"profiles\").upsert(\n        {\"id\": user_id, \"progress\": None},\n        on_conflict=\"id\",\n    ).execute()\n\ndef restore_progress_from_db(sb_authed, user_id: str):\n    try:\n        res = (\n            sb_authed.table(\"profiles\")\n            .select(\"progress\")\n            .eq(\"id\", user_id)\n            .single()\n            .execute()\n        )\n    except Exception:\n        return\n\n    if not res or not res.data:\n        return\n\n    progress = res.data.get(\"progress\")\n    if not progress:\n        return\n\n    st.session_state.quiz_type = progress.get(\"quiz_type\", st.session_state.get(\"quiz_type\", \"reading\"))\n    st.session_state.quiz_version = int(progress.get(\"quiz_version\", st.session_state.get(\"quiz_version\", 0) or 0))\n    st.session_state.quiz = progress.get(\"quiz\", st.session_state.get(\"quiz\"))\n    st.session_state.answers = progress.get(\"answers\", st.session_state.get(\"answers\"))\n    st.session_state.submitted = bool(progress.get(\"submitted\", st.session_state.get(\"submitted\", False)))\n\n    if isinstance(st.session_state.quiz, list):\n        qlen = len(st.session_state.quiz)\n        if not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != qlen:\n            st.session_state.answers = [None] * qlen\n\n# ============================================================\n# \u2705 Admin \uc124\uc815 (DB ONLY)\n# ============================================================\ndef is_admin() -> bool:\n    cached = st.session_state.get(\"is_admin_cached\")\n    if cached is not None:\n        return bool(cached)\n\n    u = st.session_state.get(\"user\")\n    if u is None:\n        st.session_state[\"is_admin_cached\"] = False\n        return False\n\n    sb_authed_local = get_authed_sb()\n    if sb_authed_local is None:\n        st.session_state[\"is_admin_cached\"] = False\n        return False\n\n    val = fetch_is_admin_from_db(sb_authed_local, u.id)\n    st.session_state[\"is_admin_cached\"] = val\n    return bool(val)\n\ndef get_available_quiz_types() -> list[str]:\n    return QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER\n\n# ============================================================\n# \u2705 \ub85c\uadf8\uc778 UI (\uc6d0\ubcf8 \uc720\uc9c0)\n# ============================================================\ndef auth_box():\n    st.markdown(\"<div style='max-width:520px; margin:0 auto;'>\", unsafe_allow_html=True)\n\n    st.markdown(\n        '<div class=\"jp\" style=\"font-weight:900; font-size:16px; margin:6px 0 6px 0;\">\ub85c\uadf8\uc778</div>',\n        unsafe_allow_html=True\n    )\n\n    qp = st.query_params\n    came_from_email_link = any(k in qp for k in [\"code\", \"token\", \"type\", \"access_token\", \"refresh_token\"])\n    if came_from_email_link and not st.session_state.get(\"email_link_notice_shown\"):\n        st.session_state.email_link_notice_shown = True\n        st.session_state.auth_mode = \"login\"\n        st.success(\"\uc774\uba54\uc77c \uc778\uc99d(\ub610\ub294 \ub9c1\ud06c \ud655\uc778)\uc774 \uc644\ub8cc\ub418\uc5c8\uc2b5\ub2c8\ub2e4. \uc774\uc81c \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n\n    if \"auth_mode\" not in st.session_state:\n        st.session_state.auth_mode = \"login\"\n\n    mode = st.radio(\n        label=\"\",\n        options=[\"login\", \"signup\"],\n        format_func=lambda x: \"\ub85c\uadf8\uc778\" if x == \"login\" else \"\ud68c\uc6d0\uac00\uc785\",\n        horizontal=True,\n        key=\"auth_mode_radio\",\n        index=0 if st.session_state.auth_mode == \"login\" else 1,\n    )\n    st.session_state.auth_mode = mode\n\n    if st.session_state.get(\"signup_done\"):\n        st.success(\"\ud68c\uc6d0\uac00\uc785 \uc694\uccad \uc644\ub8cc! \uc774\uba54\uc77c \uc778\uc99d\uc774 \ud544\uc694\ud560 \uc218 \uc788\uc5b4\uc694. \uba54\uc77c\ud568\uc744 \ud655\uc778\ud55c \ub4a4 \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n        st.session_state.signup_done = False\n\n    if mode == \"login\":\n        email = st.text_input(\"\uc774\uba54\uc77c\", key=\"login_email_input\")\n        pw = st.text_input(\"\ube44\ubc00\ubc88\ud638\", type=\"password\", key=\"login_pw_input\")\n\n        st.caption(\"\ube44\ubc00\ubc88\ud638\ub294 **\ud68c\uc6d0\uac00\uc785 \ub54c 8\uc790\ub9ac \uc774\uc0c1**\uc73c\ub85c \uc124\uc815\ud588\uc744 \uac00\ub2a5\uc131\uc774 \ud07d\ub2c8\ub2e4.\")\n        if pw and len(pw) < 8:\n            st.warning(f\"\uc785\ub825\ud558\uc2e0 \ube44\ubc00\ubc88\ud638\uac00 {len(pw)}\uc790\ub9ac\uc785\ub2c8\ub2e4. \ud68c\uc6d0\uac00\uc785 \ub54c 8\uc790\ub9ac \uc774\uc0c1\uc73c\ub85c \uc124\uc815\ud558\uc168\ub2e4\uba74 \ub354 \uae38\uac8c \uc785\ub825\ud574 \uc8fc\uc138\uc694.\")\n\n        if st.button(\"\ub85c\uadf8\uc778\", use_container_width=True, key=\"btn_login\"):\n            if not email or not pw:\n                st.warning(\"\uc774\uba54\uc77c\uacfc \ube44\ubc00\ubc88\ud638\ub97c \uc785\ub825\ud574\uc8fc\uc138\uc694.\")\n                st.stop()\n\n            try:\n                res = sb.auth.sign_in_with_password({\"email\": email, \"password\": pw})\n\n                st.session_state.user = res.user\n                st.session_state[\"login_email\"] = email.strip()\n\n                if res.session and res.session.access_token:\n                    st.session_state.access_token = res.session.access_token\n                    st.session_state.refresh_token = res.session.refresh_token\n\n                    cookies[\"access_token\"] = res.session.access_token\n                    cookies[\"refresh_token\"] = res.session.refresh_token\n                    cookies.save()\n                else:\n                    st.warning(\"\ub85c\uadf8\uc778\uc740 \ub418\uc5c8\uc9c0\ub9cc \uc138\uc158 \ud1a0\ud070\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \uc774\uba54\uc77c \uc778\uc99d \uc0c1\ud0dc\ub97c \ud655\uc778\ud574\uc8fc\uc138\uc694.\")\n                    st.session_state.access_token = None\n                    st.session_state.refresh_token = None\n\n                st.session_state.pop(\"is_admin_cached\", None)\n                st.success(\"\ub85c\uadf8\uc778 \uc644\ub8cc!\")\n                st.rerun()\n\n            except Exception:\n                st.error(\"\ub85c\uadf8\uc778 \uc2e4\ud328: \uc774\uba54\uc77c/\ube44\ubc00\ubc88\ud638 \ub610\ub294 \uc774\uba54\uc77c \uc778\uc99d \uc0c1\ud0dc\ub97c \ud655\uc778\ud574\uc8fc\uc138\uc694.\")\n                st.stop()\n\n    else:\n        email = st.text_input(\"\uc774\uba54\uc77c\", key=\"signup_email\")\n        pw = st.text_input(\"\ube44\ubc00\ubc88\ud638\", type=\"password\", key=\"signup_pw\")\n\n        pw_len = len(pw) if pw else 0\n        pw_ok = pw_len >= 8\n        email_ok = bool(email and email.strip())\n\n        st.caption(\"\ube44\ubc00\ubc88\ud638\ub294 **8\uc790\ub9ac \uc774\uc0c1**\uc73c\ub85c \uc124\uc815\ud574 \uc8fc\uc138\uc694.\")\n        if pw and not pw_ok:\n            st.warning(f\"\ube44\ubc00\ubc88\ud638\uac00 \ub108\ubb34 \uc9e7\uc2b5\ub2c8\ub2e4. (\ud604\uc7ac {pw_len}\uc790) 8\uc790\ub9ac \uc774\uc0c1\uc73c\ub85c \uc785\ub825\ud574 \uc8fc\uc138\uc694.\")\n\n        if st.button(\"\ud68c\uc6d0\uac00\uc785\", use_container_width=True, disabled=not (email_ok and pw_ok), key=\"btn_signup\"):\n            try:\n                last = st.session_state.get(\"last_signup_ts\", 0.0)\n                now = time.time()\n                if now - last < 8:\n                    st.warning(\"\uc694\uccad\uc774 \ub108\ubb34 \ube60\ub985\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694.\")\n                    st.stop()\n                st.session_state.last_signup_ts = now\n\n                sb.auth.sign_up(\n                    {\n                        \"email\": email,\n                        \"password\": pw,\n                        \"options\": {\"email_redirect_to\": APP_URL},\n                    }\n                )\n\n                st.session_state.signup_done = True\n                st.session_state.auth_mode = \"login\"\n                st.session_state[\"login_email\"] = email.strip()\n                st.rerun()\n\n            except Exception as e:\n                msg = str(e).lower()\n                if \"rate limit\" in msg and \"email\" in msg:\n                    st.session_state.auth_mode = \"login\"\n                    st.session_state[\"login_email\"] = email.strip()\n                    st.session_state.signup_done = False\n                    st.warning(\"\uc774\uba54\uc77c \ubc1c\uc1a1 \uc81c\ud55c\uc5d0 \uac78\ub838\uc2b5\ub2c8\ub2e4. \uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694.\")\n                    st.rerun()\n\n                st.error(\"\ud68c\uc6d0\uac00\uc785 \uc2e4\ud328(\uc5d0\ub7ec \ud655\uc778):\")\n                st.exception(e)\n                st.stop()\n\n    st.markdown(\"</div>\", unsafe_allow_html=True)\n\ndef require_login():\n    if st.session_state.get(\"user\") is None:\n        st.markdown(\n            \"\"\"\n<div class=\"jp\" style=\"margin: 8px 0 14px 0;\">\n  <div style=\"\n    border:1px solid rgba(120,120,120,0.18);\n    border-radius:18px;\n    padding:16px 16px;\n    background: rgba(255,255,255,0.03);\n  \">\n    <div style=\"font-weight:900; font-size:22px; line-height:1.15;\">\n      \u2728 \ud55c\uc790 \ud034\uc988\n    </div>\n    <div style=\"margin-top:6px; opacity:.85; font-size:13px; line-height:1.55;\">\n      \ud558\ub8e8 10\ubb38\ud56d\uc73c\ub85c \uac00\ubccd\uac8c \ub8e8\ud2f4\uc744 \ub9cc\ub4e4\uc5b4\uc694.<br/>\n      \uc815\ub2f5\uc740 \uc800\uc7a5\ub418\uace0, \uc624\ub2f5\uc740 \ub2e4\uc2dc \ud480 \uc218 \uc788\uc5b4\uc694.\n    </div>\n  </div>\n</div>\n\"\"\",\n            unsafe_allow_html=True,\n        )\n        auth_box()\n        st.stop()\n\n# ============================================================\n# \u2705 \ub124\uc774\ubc84\ud1a1 \ubc30\ub108 (\uc81c\ucd9c \ud6c4\ub9cc)\n# ============================================================\ndef render_naver_talk():\n    st.divider()\n    st.markdown(\n        f\"\"\"\n<style>\n@keyframes floaty {{\n  0% {{ transform: translateY(0); }}\n  50% {{ transform: translateY(-6px); }}\n  100% {{ transform: translateY(0); }}\n}}\n@keyframes ping {{\n  0% {{ transform: scale(1); opacity: 0.9; }}\n  70% {{ transform: scale(2.2); opacity: 0; }}\n  100% {{ transform: scale(2.2); opacity: 0; }}\n}}\n.floating-naver-talk,\n.floating-naver-talk:visited,\n.floating-naver-talk:hover,\n.floating-naver-talk:active {{\n  position: fixed;\n  right: 18px;\n  bottom: 90px;\n  z-index: 99999;\n  text-decoration: none !important;\n  color: inherit !important;\n}}\n.floating-wrap {{\n  position: relative;\n  animation: floaty 2.2s ease-in-out infinite;\n}}\n.talk-btn {{\n  background: #03C75A;\n  color: #fff;\n  border: 0;\n  border-radius: 999px;\n  padding: 14px 18px;\n  font-size: 15px;\n  font-weight: 700;\n  box-shadow: 0 12px 28px rgba(0,0,0,0.22);\n  cursor: pointer;\n  display: flex;\n  align-items: center;\n  gap: 10px;\n  line-height: 1.1;\n  text-decoration: none !important;\n}}\n.talk-btn:hover {{ filter: brightness(0.95); }}\n.talk-text small {{\n  display: block;\n  font-size: 12px;\n  font-weight: 600;\n  opacity: 0.95;\n  margin-top: 2px;\n}}\n.badge {{\n  position: absolute;\n  top: -6px;\n  right: -6px;\n  width: 12px;\n  height: 12px;\n  background: #ff3b30;\n  border-radius: 999px;\n  box-shadow: 0 6px 14px rgba(0,0,0,0.25);\n}}\n.badge::after {{\n  content: \"\";\n  position: absolute;\n  left: 50%;\n  top: 50%;\n  width: 12px;\n  height: 12px;\n  transform: translate(-50%, -50%);\n  border-radius: 999px;\n  background: rgba(255,59,48,0.55);\n  animation: ping 1.2s ease-out infinite;\n}}\n@media (max-width: 600px) {{\n  .floating-naver-talk {{ bottom: 110px; right: 14px; }}\n  .talk-btn {{ padding: 13px 16px; font-size: 14px; }}\n  .talk-text small {{ font-size: 11px; }}\n}}\n</style>\n\n<a class=\"floating-naver-talk\" href=\"{NAVER_TALK_URL}\" target=\"_blank\" rel=\"noopener noreferrer\">\n  <div class=\"floating-wrap\">\n    <span class=\"badge\"></span>\n    <button class=\"talk-btn\" type=\"button\">\n      <span>\ud83d\udcac</span>\n      <span class=\"talk-text\">\n        1:1 \ud558\ud14c\ub098\uc324 \uc0c1\ub2f4\n        <small>\uc218\uac15\uc2e0\uccad \ubb38\uc758\ud558\uae30</small>\n      </span>\n    </button>\n  </div>\n</a>\n\"\"\",\n        unsafe_allow_html=True,\n    )\n\n# ============================================================\n# \u2705 \uc0c1\ub2e8 \uce74\ub4dc(\uad00\ub9ac\uc790/\ub9c8\uc774\ud398\uc774\uc9c0/\ub85c\uadf8\uc544\uc6c3)\n# ============================================================\ndef nav_to(page: str, scroll_top: bool = True):\n    st.session_state.page = page\n    if scroll_top:\n        st.session_state[\"_scroll_top_once\"] = True\n\ndef nav_logout():\n    clear_auth_everywhere()\n\ndef render_topcard():\n    u = st.session_state.get(\"user\")\n    if not u:\n        return\n\n    email = getattr(u, \"email\", None) or st.session_state.get(\"login_email\", \"\")\n\n    st.markdown('<div class=\"topcard\">', unsafe_allow_html=True)\n\n    left, r_admin, r_my, r_logout = st.columns([6.0, 1.2, 2.4, 2.4], vertical_alignment=\"center\")\n\n    with left:\n        # \u2705 \uc67c\ucabd '\ud658\uc601\ud569\ub2c8\ub2e4/\uc774\uba54\uc77c' \uc81c\uac70 (\uacf5\uac04\ub9cc \uc720\uc9c0)\n        st.markdown(\"<div style='height:40px;'></div>\", unsafe_allow_html=True)\n\n    with r_admin:\n        if is_admin():\n            st.button(\"\ud83d\udcca\", use_container_width=True, help=\"\uad00\ub9ac\uc790 \ub300\uc2dc\ubcf4\ub4dc\",\n                      key=\"topcard_btn_nav_admin\", on_click=nav_to, args=(\"admin\",))\n        else:\n            st.markdown(\"<div style='height:40px;'></div>\", unsafe_allow_html=True)\n\n    with r_my:\n        st.button(\"\ud83d\udccc \ub9c8\uc774\ud398\uc774\uc9c0\", use_container_width=True, help=\"\ub0b4 \ud559\uc2b5 \uae30\ub85d/\uc624\ub2f5 TOP10 \ubcf4\uae30\",\n                  key=\"topcard_btn_nav_my\", on_click=nav_to, args=(\"my\",))\n\n    with r_logout:\n        st.button(\"\ud83d\udeaa \ub85c\uadf8\uc544\uc6c3\", use_container_width=True, help=\"\ub85c\uadf8\uc544\uc6c3\",\n                  key=\"topcard_btn_logout\", on_click=nav_logout)\n\n    st.markdown(\"</div>\", unsafe_allow_html=True)\n\n# ============================================================\n# \u2705 \ub85c\ub529: CSV \ud480\n# ============================================================\nREAD_KW = dict(\n    dtype=str,\n    keep_default_na=False,\n    na_values=[\"nan\", \"NaN\", \"NULL\", \"null\", \"None\", \"none\"],\n)\n\n@st.cache_data(show_spinner=False)\ndef load_pool(csv_path_str: str) -> pd.DataFrame:\n    df = pd.read_csv(csv_path_str, **READ_KW)\n\n    # \u2705 \ud55c\uc790 \ud034\uc988 \ud544\uc218 \uceec\ub7fc\n    # \u2705 \ud55c\uc790 \ud034\uc988 \ud544\uc218 \uceec\ub7fc (+pos \ucd94\uac00)\n    required_cols = {\"level\", \"jp_word\", \"reading\", \"meaning\", \"pos\"}\n    missing = required_cols - set(df.columns)\n    if missing:\n        raise ValueError(f\"CSV \ud544\uc218 \uceec\ub7fc \ub204\ub77d: {sorted(list(missing))}\")\n\n    # \u2705 pos \uc815\uaddc\ud654 (\ud544\uc218)\n    df[\"pos\"] = df[\"pos\"].astype(str).str.strip().str.lower()\n\n\n    # \u2705 1) \uc720\ub2c8\ucf54\ub4dc \uc815\uaddc\ud654 (\uff2e\uff15 / \uff4e\uff14 / \uc804\uac01 \uc22b\uc790 \ub4f1 \u2192 N5 / N4\ub85c \ud1b5\uc77c)\n    def _nfkc(s):\n        return unicodedata.normalize(\"NFKC\", str(s or \"\"))\n\n    lv = df[\"level\"].apply(_nfkc).astype(str).str.upper().str.strip()\n    lv = lv.str.replace(\" \", \"\", regex=False)\n\n    # \u2705 2) \ub808\ubca8 \uc548\uc5d0 N1~N5\uac00 \uc788\uc73c\uba74 \ucd94\ucd9c\n    extracted = lv.str.extract(r\"(N[1-5])\", expand=False)\n\n    # \u2705 3) \uc5c6\uc73c\uba74 \uc22b\uc790\ub9cc \uc788\ub294 \ucf00\uc774\uc2a4 \ucc98\ub9ac (\"1\"~\"5\")\n    digit_map = {\"1\": \"N1\", \"2\": \"N2\", \"3\": \"N3\", \"4\": \"N4\", \"5\": \"N5\"}\n    only_digit = lv.where(extracted.isna(), \"\")  # \ucd94\ucd9c \uc131\uacf5\ud55c \ud589\uc740 \ube44\uc6c0\n    only_digit = only_digit.str.extract(r\"^([1-5])$\", expand=False)\n    digit_fixed = only_digit.map(digit_map)\n\n    # \u2705 4) \ucd5c\uc885 \ub808\ubca8: extracted \uc6b0\uc120, \uadf8 \ub2e4\uc74c digit_fixed, \uadf8\ub798\ub3c4 \uc5c6\uc73c\uba74 \uc6d0\ubcf8 lv\n    final_lv = extracted.fillna(digit_fixed).fillna(lv)\n\n    # \u2705 5) \uc548\uc804\uc7a5\uce58: N1~N5 \uc544\ub2cc \uac12\uc740 \ube48\uce78 \ucc98\ub9ac\n    final_lv = final_lv.where(final_lv.isin([\"N1\", \"N2\", \"N3\", \"N4\", \"N5\"]), \"\")\n\n    df[\"level\"] = final_lv\n\n\n    df[\"jp_word\"] = df[\"jp_word\"].astype(str).str.strip()\n    df[\"reading\"] = df[\"reading\"].astype(str).str.strip()\n    df[\"meaning\"] = df[\"meaning\"].astype(str).str.strip()\n\n    # \ube44\uc5b4\uc788\ub294 \uc904 \uc81c\uac70(\uc548\uc804)\n    df = df[(df[\"jp_word\"] != \"\") & (df[\"reading\"] != \"\") & (df[\"meaning\"] != \"\")].copy()\n    return df.reset_index(drop=True)\n\ndef ensure_pool_ready():\n    if st.session_state.get(\"pool_ready\") and isinstance(st.session_state.get(\"_pool\"), pd.DataFrame):\n        return\n\n    try:\n        pool = load_pool(str(CSV_PATH))\n    except Exception as e:\n        st.error(f\"\ub2e8\uc5b4 \ub370\uc774\ud130 \ub85c\ub4dc \uc2e4\ud328: {e}\")\n        st.stop()\n\n    if len(pool) < N:\n        st.error(f\"\ub2e8\uc5b4\uac00 \ubd80\uc871\ud569\ub2c8\ub2e4: pool={len(pool)} (N={N})\")\n        st.stop()\n\n    st.session_state[\"_pool\"] = pool\n    st.session_state[\"pool_ready\"] = True\n    \n    # \u2705 \ub514\ubc84\uadf8(\uad00\ub9ac\uc790\ub9cc)\n    if is_admin():\n        with st.expander(\"\ud83d\udd0e \ub514\ubc84\uadf8: \ub808\ubca8\ubcc4 \ub2e8\uc5b4 \uc218\", expanded=False):\n            pool = st.session_state.get(\"_pool\")\n            if isinstance(pool, pd.DataFrame):\n                st.write(pool[\"level\"].value_counts(dropna=False))\n                st.write(\"CSV_PATH =\", str(CSV_PATH))\n\n# ============================================================\n# \u2705 \ud034\uc988 \ub85c\uc9c1 (\ud55c\uc790\uc6a9) - 3\uc720\ud615 \uc9c0\uc6d0 + reading\ub9cc \ud328\ud134 \ubc29\uc9c0(\ud488\uc0ac\ubcc4 \uac15\ub3c4\uc870\uc808)\n# ============================================================\n\nimport unicodedata\nimport random\nimport pandas as pd\nimport streamlit as st\n\ndef _nfkc_str(x) -> str:\n    return unicodedata.normalize(\"NFKC\", str(x or \"\")).strip()\n\ndef _to_hira(s: str) -> str:\n    # \uce74\ud0c0\uce74\ub098 \u2192 \ud788\ub77c\uac00\ub098 (\uc77d\uae30\uac00 \uce74\ud0c0\uce74\ub098\uc77c \uac00\ub2a5\uc131 \ub300\ube44)\n    s = _nfkc_str(s)\n    out = []\n    for ch in s:\n        code = ord(ch)\n        if 0x30A1 <= code <= 0x30F6:  # \u30a1-\u30f6\n            out.append(chr(code - 0x60))\n        else:\n            out.append(ch)\n    return \"\".join(out)\n\ndef _last_char(x) -> str:\n    s = _to_hira(_nfkc_str(x))\n    return s[-1] if s else \"\"\n\ndef _vowel_group(kana_or_word: str) -> str:\n    \"\"\"\n    \ub9c8\uc9c0\ub9c9 \uae00\uc790\ub97c '\ub2e8(\ud589)'\uc73c\ub85c \ubb36\uae30: a/i/u/e/o/n/other\n    \"\"\"\n    ch = _last_char(kana_or_word)\n    if not ch:\n        return \"other\"\n\n    if ch == \"\u3093\":\n        return \"n\"\n\n    # \uc791\uc740 \uae00\uc790/\uc7a5\uc74c/\ucd09\uc74c \ub4f1\uc740 other\n    if ch in \"\u3041\u3043\u3045\u3047\u3049\u3083\u3085\u3087\u3063\u30fc\u308e\":\n        return \"other\"\n\n    A = set(\"\u3042\u304b\u3055\u305f\u306a\u306f\u307e\u3084\u3089\u308f\u304c\u3056\u3060\u3070\u3071\u3041\u3083\u308e\")\n    I = set(\"\u3044\u304d\u3057\u3061\u306b\u3072\u307f\u308a\u304e\u3058\u3062\u3073\u3074\u3043\")\n    U = set(\"\u3046\u304f\u3059\u3064\u306c\u3075\u3080\u3086\u308b\u3050\u305a\u3065\u3076\u3077\u3045\u3085\")\n    E = set(\"\u3048\u3051\u305b\u3066\u306d\u3078\u3081\u308c\u3052\u305c\u3067\u3079\u307a\u3047\")\n    O = set(\"\u304a\u3053\u305d\u3068\u306e\u307b\u3082\u3088\u308d\u3092\u3054\u305e\u3069\u307c\u307d\u3049\u3087\u3092\")\n\n    if ch in A: return \"a\"\n    if ch in I: return \"i\"\n    if ch in U: return \"u\"\n    if ch in E: return \"e\"\n    if ch in O: return \"o\"\n    return \"other\"\n\ndef _uniq(xs):\n    out = []\n    seen = set()\n    for x in xs:\n        if x not in seen:\n            seen.add(x)\n            out.append(x)\n    return out\n\ndef _pick_reading_wrongs(\n    candidates: list[str],\n    correct: str,\n    pos: str,\n    jp_word: str = \"\",\n    k: int = 3,\n    strict_pos: set[str] | None = None,\n) -> list[str]:\n    \"\"\"\n    \u2705 reading(\ubc1c\uc74c) \uc624\ub2f5 \uc120\ud0dd\n    \ubaa9\ud45c: '\ubaa8\uc591(\ub05d\uae00\uc790) + \ub05d 2\uae00\uc790(\uc608: \u308f\u308b/\u308a\u308b/\u308b\u304f/\u304d\u3044)' \ud78c\ud2b8\ub85c \uc27d\uac8c \ubabb \ub9de\ud788\uac8c \ud558\uae30\n\n    \ub3d9\uc0ac/\ud615\uc6a9\uc0ac(\ud2b9\ud788 \u3044\ud615\uc6a9\uc0ac)\ub294:\n      1) \ub05d 2\uae00\uc790 \ub3d9\uc77c \uc6b0\uc120 (\uc608: \u308f\u308b, \u308b\u304f, \u304d\u3044)\n      2) \ubd80\uc871\ud558\uba74 \ub05d 1\uae00\uc790 \ub3d9\uc77c (\uc608: \u308b, \u304f, \u3044)\n      3) \ubd80\uc871\ud558\uba74 \uac19\uc740 \ub2e8(\ud589) (u\ub2e8/e\ub2e8 \ub4f1)\n      4) \uadf8\ub798\ub3c4 \ubd80\uc871\ud558\uba74 \uc804\uccb4 \ub79c\ub364 (\uc571\uc774 \uba48\ucd94\uc9c0 \uc54a\uac8c)\n\n    \uadf8 \uc678 \ud488\uc0ac(adv/noun \ub4f1)\ub294:\n      - \uc704\ucc98\ub7fc '\ub05d \ud1b5\uc77c'\uc744 \uac15\uc81c\ud558\uba74 \uc624\ud788\ub824 \uc774\uc0c1\ud574\uc9c8 \uc218 \uc788\uc73c\ub2c8,\n        \ub9c8\uc9c0\ub9c9 \uae00\uc790 \ubd84\uc0b0\uc744 \uc6b0\uc120\ud558\uace0, \ud544\uc694\uc2dc \ub79c\ub364\uc73c\ub85c \ucc44\uc6c0.\n    \"\"\"\n\n    def _suffix(x: str, n: int) -> str:\n        s = _to_hira(_nfkc_str(x))\n        return s[-n:] if len(s) >= n else s\n\n    if strict_pos is None:\n        # \u2705 DB pos \ub77c\ubca8\uc5d0 \ub9de\uac8c \uc790\uc720\ub86d\uac8c \ucd94\uac00 \uac00\ub2a5\n        strict_pos = {\"v\", \"verb\", \"adj\", \"adj_i\", \"adj_na\", \"i_adj\", \"adj-i\"}\n\n    correct_nf = _nfkc_str(correct)\n    cands = _uniq([_nfkc_str(c) for c in candidates if _nfkc_str(c) and _nfkc_str(c) != correct_nf])\n\n    if len(cands) < k:\n        return []\n\n    # \ub05d 1\uae00\uc790 / \ub05d 2\uae00\uc790(= \u201c\ub05d \ubaa8\uc591 + \uc55e 1\uae00\uc790\u201d)\ub97c \ud78c\ud2b8 \ucc28\ub2e8\uc6a9\uc73c\ub85c \uc0ac\uc6a9\n    s1 = _suffix(correct_nf, 1)  # ex) \u308b / \u304f / \u3044\n    s2 = _suffix(correct_nf, 2)  # ex) \u308f\u308b / \u308a\u308b / \u308b\u304f / \u304d\u3044\n\n    # \u2705 \u3044\ud615\uc6a9\uc0ac \uc790\ub3d9 \ud310\uc815(\ud55c\uc790\ud45c\uae30 \uc790\uccb4\uac00 \u301c\u3044\ub85c \ub05d\ub098\uace0, reading\ub3c4 \u301c\u3044\ub85c \ub05d\ub098\ub294 \uacbd\uc6b0)\n    jp_h = _to_hira(_nfkc_str(jp_word))\n    rd_h = _to_hira(correct_nf)\n    force_i_adj = (jp_h.endswith(\"\u3044\") and rd_h.endswith(\"\u3044\"))\n\n    # ---------- (A) \ub3d9\uc0ac/\ud615\uc6a9\uc0ac + \u3044\ud615\uc6a9\uc0ac \uc790\ub3d9: \"\ub05d2 \u2192 \ub05d1\" \uac15\uc81c ----------\n    if (pos in strict_pos) or force_i_adj:\n        same2 = _uniq([c for c in cands if _suffix(c, 2) == s2])\n        if len(same2) >= k:\n            return random.sample(same2, k)\n\n        same1 = _uniq([c for c in cands if _suffix(c, 1) == s1])\n        if len(same1) >= k:\n            # \uac00\ub2a5\ud558\uba74 \ub05d2 \ud6c4\ubcf4\ub97c \uc11e\uace0, \ubd80\uc871\ud558\uba74 \ub05d1\uc5d0\uc11c \ucc44\uc6c0\n            wrongs = same2[:]\n            rest = [c for c in same1 if c not in wrongs]\n            need = k - len(wrongs)\n            if need > 0:\n                if len(rest) >= need:\n                    wrongs += random.sample(rest, need)\n                else:\n                    # \ub05d1\uc5d0\uc11c\ub3c4 \ubd80\uc871\ud558\uba74 \uc804\uccb4\uc5d0\uc11c \ucc44\uc6c0\n                    pool_all = [c for c in cands if c not in wrongs]\n                    wrongs += random.sample(pool_all, min(need, len(pool_all)))\n            return wrongs[:k]\n\n        # \ub05d1\ub3c4 \ubd80\uc871\ud558\uba74 \uac19\uc740 \ub2e8(\ud589)\uc73c\ub85c \uc644\ud654\n        g = _vowel_group(correct_nf)\n        vg = _uniq([c for c in cands if _vowel_group(c) == g])\n        if len(vg) >= k:\n            return random.sample(vg, k)\n\n        # \uadf8\ub798\ub3c4 \ubd80\uc871\ud558\uba74 \uc804\uccb4 \ub79c\ub364 (\uc808\ub300 \uba48\ucd94\uc9c0 \uc54a\uac8c)\n        return random.sample(cands, k)\n\n    # ---------- (B) \uae30\ud0c0 \ud488\uc0ac: \ub05d \ud1b5\uc77c \uac15\uc81c X, \ub9c8\uc9c0\ub9c9 \uae00\uc790 \ubd84\uc0b0 ----------\n    base = cands[:]\n    random.shuffle(base)\n\n    wrongs = []\n    seen_last = set()\n\n    for c in base:\n        lc = _last_char(c)\n        if lc and lc not in seen_last:\n            wrongs.append(c)\n            seen_last.add(lc)\n            if len(wrongs) == k:\n                return wrongs\n\n    # \ubd80\uc871\ud558\uba74 \ub79c\ub364\uc73c\ub85c \ucc44\uc6c0\n    rest = [c for c in base if c not in wrongs]\n    if len(rest) >= (k - len(wrongs)):\n        wrongs += random.sample(rest, k - len(wrongs))\n        return wrongs\n\n    # \ucd5c\ud6c4: \uac00\ub2a5\ud55c \ub9cc\ud07c\uc774\ub77c\ub3c4 \ubc18\ud658(\uc0c1\uc704\uc5d0\uc11c \uc548\uc804\uc7a5\uce58)\n    return wrongs\n\ndef make_question(row: pd.Series, qtype: str, pool: pd.DataFrame) -> dict:\n    jp = str(row.get(\"jp_word\", \"\")).strip()\n    rd = str(row.get(\"reading\", \"\")).strip()\n    mn = str(row.get(\"meaning\", \"\")).strip()\n    lvl = str(row.get(\"level\", \"\")).strip().upper()\n    pos = str(row.get(\"pos\", \"\")).strip().lower()\n\n    # \u2705 \uac19\uc740 \ud488\uc0ac(pos)\ub9cc\uc73c\ub85c \ubcf4\uae30 \ud6c4\ubcf4 \ud480 \ub9cc\ub4e4\uae30\n    pool_pos = pool[pool[\"pos\"].astype(str).str.strip().str.lower() == pos].copy()\n\n    if qtype == \"reading\":\n        prompt = f\"{jp}\uc758 \ubc1c\uc74c\uc740?\"\n        correct = rd\n        candidates = (\n            pool_pos.loc[pool_pos[\"reading\"] != correct, \"reading\"]\n            .dropna().drop_duplicates().tolist()\n        )\n\n        # \u2705 reading\ub9cc: (\ub3d9\uc0ac/\ud615\uc6a9\uc0ac\ub294 \ub05d\ubaa8\uc591 \ud1b5\uc77c / \uadf8 \uc678\ub294 \ubd84\uc0b0) + \uc2e4\ud328 \uc2dc \uc790\ub3d9 \uc644\ud654\n        wrongs = _pick_reading_wrongs(candidates, correct, pos=pos, jp_word=jp, k=3)\n        if len(wrongs) < 3:\n            st.error(f\"\uc624\ub2f5 \ud6c4\ubcf4 \ubd80\uc871(\ubc1c\uc74c): pos={pos}, \ud6c4\ubcf4={len(candidates)}\uac1c\")\n            st.stop()\n\n\n    elif qtype == \"meaning\":\n        prompt = f\"{jp}\uc758 \ub73b\uc740?\"\n        correct = mn\n        candidates = (\n            pool_pos.loc[pool_pos[\"meaning\"] != correct, \"meaning\"]\n            .dropna().drop_duplicates().tolist()\n        )\n\n        if len(candidates) < 3:\n            st.error(f\"\uc624\ub2f5 \ud6c4\ubcf4 \ubd80\uc871(\ub73b): pos={pos}, \ud6c4\ubcf4={len(candidates)}\uac1c\")\n            st.stop()\n\n        wrongs = random.sample(candidates, 3)\n\n    elif qtype == \"kr2jp\":\n        prompt = f\"'{mn}'\uc758 \uc77c\ubcf8\uc5b4(\ud55c\uc790)\ub294?\"\n        correct = jp\n        candidates = (\n            pool_pos.loc[pool_pos[\"jp_word\"] != correct, \"jp_word\"]\n            .dropna().astype(str).str.strip().tolist()\n        )\n        candidates = [x for x in dict.fromkeys(candidates) if x]\n\n        if len(candidates) < 3:\n            st.error(f\"\uc624\ub2f5 \ud6c4\ubcf4 \ubd80\uc871(\ud55c\u2192\uc77c): pos={pos}, \ud6c4\ubcf4={len(candidates)}\uac1c\")\n            st.stop()\n\n        wrongs = random.sample(candidates, 3)\n\n    else:\n        raise ValueError(f\"Unknown qtype: {qtype}\")\n\n    choices = wrongs + [correct]\n    random.shuffle(choices)\n\n    return {\n        \"prompt\": prompt,\n        \"choices\": choices,\n        \"correct_text\": correct,\n        \"jp_word\": jp,\n        \"reading\": rd,\n        \"meaning\": mn,\n        \"level\": lvl,\n        \"pos\": pos,\n        \"qtype\": qtype,\n    }\n\n\n# ============================================================\n# \u2705 build_quiz / build_quiz_from_wrongs (\ub2f9\uc2e0 \uc6d0\ubcf8 \uc720\uc9c0)\n#    \u203b \uc544\ub798 \ud568\uc218\ub4e4\uc740 \uadf8\ub300\ub85c \ub450\uba74 \ub429\ub2c8\ub2e4.\n# ============================================================\n\ndef build_quiz(qtype: str, level: str) -> list[dict]:\n    ensure_pool_ready()\n    ensure_mastered_words_shape()\n    ensure_excluded_wrong_words_shape()\n    ensure_mastery_banner_shape()\n\n    pool = st.session_state[\"_pool\"]\n\n    level = str(level).strip().upper()\n    base_level = pool[pool[\"level\"].astype(str).str.upper() == level].copy()\n\n    if len(base_level) < N:\n        st.warning(f\"{level} \ub2e8\uc5b4\uac00 \ubd80\uc871\ud569\ub2c8\ub2e4. (\ud604\uc7ac {len(base_level)}\uac1c / \ud544\uc694 {N}\uac1c)\")\n        return []\n\n    k = mastery_key(qtype=qtype)\n    mastered = st.session_state.get(\"mastered_words\", {}).get(k, set())\n    excluded = st.session_state.get(\"excluded_wrong_words\", {}).get(k, set())\n\n    blocked = set()\n    if mastered:\n        blocked |= set(mastered)\n    if excluded:\n        blocked |= set(excluded)\n\n    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:\n        if not blocked:\n            return df\n        keys = df[\"jp_word\"].astype(str).str.strip()\n        return df[~keys.isin(blocked)].copy()\n\n    base = _filter_blocked(base_level)\n\n    if len(base) < N:\n        st.session_state.setdefault(\"mastery_done\", {})\n        st.session_state.mastery_done[k] = True\n        return []\n\n    sampled = base.sample(n=N, replace=False).reset_index(drop=True)\n    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]\n\n\ndef build_quiz_from_wrongs(wrong_list: list, qtype: str) -> list:\n    ensure_pool_ready()\n    pool = st.session_state[\"_pool\"]\n\n    wrong_words = []\n    for w in (wrong_list or []):\n        key = str(w.get(\"\ub2e8\uc5b4\", \"\")).strip()\n        if key:\n            wrong_words.append(key)\n    wrong_words = list(dict.fromkeys(wrong_words))\n\n    if not wrong_words:\n        st.warning(\"\ud604\uc7ac \uc624\ub2f5 \ub178\ud2b8\uac00 \ube44\uc5b4 \uc788\uc5b4\uc694. \ud83d\ude42\")\n        return []\n\n    retry_df = pool[pool[\"jp_word\"].isin(wrong_words)].copy()\n    if len(retry_df) == 0:\n        st.error(\"\uc624\ub2f5 \ub2e8\uc5b4\ub97c \ud480\uc5d0\uc11c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. (jp_word/reading \ub9e4\uce6d \ud655\uc778)\")\n        st.stop()\n\n    retry_df = retry_df.sample(frac=1).reset_index(drop=True)\n    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]\n\n\ndef build_quiz(qtype: str, level: str) -> list[dict]:\n    ensure_pool_ready()\n    ensure_mastered_words_shape()\n    ensure_excluded_wrong_words_shape()\n    ensure_mastery_banner_shape()\n\n    pool = st.session_state[\"_pool\"]\n\n    # \u2705 \ub808\ubca8 \ud544\ud130 (N5~N1)\n    level = str(level).strip().upper()\n    base_level = pool[pool[\"level\"].astype(str).str.upper() == level].copy()\n\n    # \ub808\ubca8 \ub370\uc774\ud130\uac00 \ub108\ubb34 \uc801\uc744 \ub54c \uc548\uc804\uc7a5\uce58\n    if len(base_level) < N:\n        st.warning(f\"{level} \ub2e8\uc5b4\uac00 \ubd80\uc871\ud569\ub2c8\ub2e4. (\ud604\uc7ac {len(base_level)}\uac1c / \ud544\uc694 {N}\uac1c)\")\n        return []\n\n    k = mastery_key(qtype=qtype)\n    mastered = st.session_state.get(\"mastered_words\", {}).get(k, set())\n    excluded = st.session_state.get(\"excluded_wrong_words\", {}).get(k, set())\n\n    blocked = set()\n    if mastered:\n        blocked |= set(mastered)\n    if excluded:\n        blocked |= set(excluded)\n\n    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:\n        if not blocked:\n            return df\n        keys = df[\"jp_word\"].astype(str).str.strip()\n        return df[~keys.isin(blocked)].copy()\n\n    base = _filter_blocked(base_level)\n\n    # \ub354 \ubf51\uc744 \ub2e8\uc5b4\uac00 \uc5c6\uc73c\uba74 \u201c\uc815\ubcf5\u201d\n    if len(base) < N:\n        st.session_state.setdefault(\"mastery_done\", {})\n        st.session_state.mastery_done[k] = True\n        return []\n\n    sampled = base.sample(n=N, replace=False).reset_index(drop=True)\n    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]\n\ndef build_quiz_from_wrongs(wrong_list: list, qtype: str) -> list:\n    ensure_pool_ready()\n    pool = st.session_state[\"_pool\"]\n\n    wrong_words = []\n    for w in (wrong_list or []):\n        key = str(w.get(\"\ub2e8\uc5b4\", \"\")).strip()\n        if key:\n            wrong_words.append(key)\n    wrong_words = list(dict.fromkeys(wrong_words))\n\n    if not wrong_words:\n        st.warning(\"\ud604\uc7ac \uc624\ub2f5 \ub178\ud2b8\uac00 \ube44\uc5b4 \uc788\uc5b4\uc694. \ud83d\ude42\")\n        return []\n\n    retry_df = pool[pool[\"jp_word\"].isin(wrong_words)].copy()\n    if len(retry_df) == 0:\n        st.error(\"\uc624\ub2f5 \ub2e8\uc5b4\ub97c \ud480\uc5d0\uc11c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. (jp_word/reading \ub9e4\uce6d \ud655\uc778)\")\n        st.stop()\n\n    retry_df = retry_df.sample(frac=1).reset_index(drop=True)\n    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]\n\n# ============================================================\n# \u2705 \ub9c8\uc774\ud398\uc774\uc9c0/\uad00\ub9ac\uc790 (\uc6d0\ubcf8 \uae30\ub2a5 \uc720\uc9c0, \ud55c\uc790\uc6a9\uc73c\ub85c \uac00\ubcbc\uc6b4 \uc870\uc815)\n# ============================================================\n\ndef render_admin_dashboard():\n    st.subheader(\"\ud83d\udcca \uad00\ub9ac\uc790 \ub300\uc2dc\ubcf4\ub4dc\")\n\n    if not is_admin():\n        st.error(\"\uc811\uadfc \uad8c\ud55c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.\")\n        st.session_state.page = \"quiz\"\n        st.stop()\n\n    if st.button(\"\u2190 \ub3cc\uc544\uac00\uae30\", use_container_width=True, key=\"btn_admin_back\"):\n        st.session_state.page = \"quiz\"\n        st.rerun()\n\n    sb_authed_local = get_authed_sb()\n    if sb_authed_local is None:\n        st.warning(\"\uc138\uc158 \ud1a0\ud070\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n        return\n\n    st.caption(\"\u203b \uc5ec\uae30\uc11c\ubd80\ud130 \ud655\uc7a5 \uac00\ub2a5(\uc804\uccb4 \uae30\ub85d \uc870\ud68c \ub4f1).\")\n\ndef render_my_dashboard():\n    st.subheader(\"\ud83d\udccc \ub0b4 \ub300\uc2dc\ubcf4\ub4dc\")\n\n    if st.button(\"\u2190 \ub3cc\uc544\uac00\uae30\", use_container_width=True, key=\"btn_my_back\"):\n        st.session_state.page = \"quiz\"\n        st.rerun()\n\n    u = st.session_state.get(\"user\")\n    if not u:\n        st.warning(\"\ub85c\uadf8\uc778 \uc815\ubcf4\uac00 \uc5c6\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n        st.session_state.page = \"quiz\"\n        st.stop()\n\n    user_id_local = getattr(u, \"id\", None)\n    if not user_id_local:\n        st.warning(\"\uc720\uc800 ID\ub97c \ucc3e\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n        st.session_state.page = \"quiz\"\n        st.stop()\n\n    sb_authed_local = get_authed_sb()\n    if sb_authed_local is None:\n        st.warning(\"\uc138\uc158 \ud1a0\ud070\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n        return\n\n    # \ud83d\uddd1\ufe0f \uc804\uccb4 \ud559\uc2b5 \uae30\ub85d \uc644\uc804 \ucd08\uae30\ud654\n    with st.expander(\"\ud83d\uddd1\ufe0f \uc804\uccb4 \ud559\uc2b5 \uae30\ub85d \uc644\uc804 \ucd08\uae30\ud654\", expanded=False):\n        st.warning(\n            \"\uc774 \uc791\uc5c5\uc740 \ub418\ub3cc\ub9b4 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\\n\"\n            \"(\ucd5c\uadfc \uae30\ub85d / \uc624\ub2f5 TOP10 / \uc9c4\ud589\uc911 \ubcf5\uc6d0\uae4c\uc9c0 \ubaa8\ub450 \ucd08\uae30\ud654\ub429\ub2c8\ub2e4.)\"\n        )\n        agree = st.checkbox(\"\ucd08\uae30\ud654\uc5d0 \ub3d9\uc758\ud569\ub2c8\ub2e4.\", key=\"chk_reset_all_agree\")\n        if st.button(\"\ud83d\uddd1\ufe0f \uc9c0\uae08 \uc644\uc804 \ucd08\uae30\ud654\", type=\"primary\", use_container_width=True, key=\"btn_reset_all_records\"):\n            if not agree:\n                st.error(\"\ucd08\uae30\ud654\uc5d0 \ub3d9\uc758\ud574 \uc8fc\uc138\uc694.\")\n                st.stop()\n\n            try:\n                def _delete_all():\n                    delete_all_learning_records(sb_authed_local, user_id_local)\n                    return True\n                run_db(_delete_all)\n\n                clear_question_widget_keys()\n                for k in [\n                    \"history\", \"wrong_counter\", \"total_counter\",\n                    \"wrong_list\", \"quiz\", \"answers\", \"submitted\",\n                    \"saved_this_attempt\", \"stats_saved_this_attempt\",\n                    \"session_stats_applied_this_attempt\",\n                    \"quiz_version\",\n                    \"mastered_words\", \"mastery_banner_shown\", \"mastery_done\",\n                    \"progress_restored\", \"pool_ready\",\n                    \"excluded_wrong_words\",\n                ]:\n                    st.session_state.pop(k, None)\n\n                st.success(\"\u2705 \uc804\uccb4 \ud559\uc2b5 \uae30\ub85d\uc774 \uc644\uc804 \ucd08\uae30\ud654\ub418\uc5c8\uc2b5\ub2c8\ub2e4.\")\n                st.session_state.page = \"quiz\"\n                st.rerun()\n\n            except Exception as e:\n                st.error(\"\ucd08\uae30\ud654 \uc2e4\ud328: RLS \uc815\ucc45(\uc0ad\uc81c \uad8c\ud55c) \ub610\ub294 \ud14c\uc774\ube14/\uceec\ub7fc \ud655\uc778\uc774 \ud544\uc694\ud569\ub2c8\ub2e4.\")\n                st.exception(e)\n\n    def _fetch():\n        return fetch_recent_attempts(sb_authed_local, user_id_local, limit=50)\n\n    try:\n        res = run_db(_fetch)\n    except Exception as e:\n        st.info(\"\uae30\ub85d\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.\")\n        st.write(str(e))\n        return\n\n    if not res.data:\n        st.info(\"\uc544\uc9c1 \uc800\uc7a5\ub41c \uae30\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \ubb38\uc81c\ub97c \ud480\uace0 \uc81c\ucd9c\ud558\uba74 \uae30\ub85d\uc774 \uc313\uc5ec\uc694.\")\n        return\n\n    hist = pd.DataFrame(res.data).copy()\n    hist[\"created_at\"] = to_kst_naive(hist[\"created_at\"])\n    hist[\"\uc720\ud615\"] = hist[\"pos_mode\"].map(lambda x: quiz_label_for_table.get(x, x))\n    hist[\"\uc815\ub2f5\ub960\"] = (hist[\"score\"] / hist[\"quiz_len\"]).fillna(0.0)\n\n    avg_rate = float(hist[\"\uc815\ub2f5\ub960\"].mean() * 100)\n    best = int(hist[\"score\"].max())\n    last_score = int(hist.iloc[0][\"score\"])\n    last_total = int(hist.iloc[0][\"quiz_len\"])\n\n    # \u2705 \ub9c8\uc774\ud398\uc774\uc9c0 \uc0c1\ub2e8 3\uce74\ub4dc (components.html\ub85c \uac15\uc81c \ub80c\ub354\ub9c1)\n    dashboard_html = f\"\"\"\n    <style>\n    .stat-grid{{\n      display:grid;\n      grid-template-columns: repeat(3, 1fr);\n      gap:12px;\n      margin: 6px 0 6px 0;\n    }}\n    .stat-card{{\n      border:1px solid rgba(120,120,120,0.25);\n      border-radius:18px;\n      padding:14px 14px;\n      background: rgba(255,255,255,0.02);\n    }}\n    .stat-label{{\n      font-size:12px;\n      font-weight:800;\n      opacity:.72;\n      line-height:1.2;\n    }}\n    .stat-value{{\n      margin-top:6px;\n      font-size:22px;\n      font-weight:900;\n      line-height:1.1;\n    }}\n    .stat-sub{{\n      margin-top:6px;\n      font-size:12px;\n      opacity:.70;\n      line-height:1.2;\n    }}\n    @media (max-width: 520px){{\n      .stat-grid{{ grid-template-columns: 1fr; }}\n      .stat-value{{ font-size:24px; }}\n    }}\n    </style>\n\n    <div class=\"jp\">\n      <div class=\"stat-grid\">\n        <div class=\"stat-card\">\n          <div class=\"stat-label\">\ucd5c\uadfc \ud3c9\uade0(\ucd5c\ub300 50\ud68c)</div>\n          <div class=\"stat-value\">{avg_rate:.0f}%</div>\n          <div class=\"stat-sub\">\uc815\ub2f5\ub960 \uae30\uc900</div>\n        </div>\n    \n        <div class=\"stat-card\">\n          <div class=\"stat-label\">\ucd5c\uace0 \uc810\uc218</div>\n          <div class=\"stat-value\">{best} / {last_total}</div>\n          <div class=\"stat-sub\">\ucd5c\uadfc \uae30\ub85d \uc911 \ucd5c\uace0</div>\n        </div>\n    \n        <div class=\"stat-card\">\n          <div class=\"stat-label\">\ucd5c\uadfc \uc810\uc218</div>\n          <div class=\"stat-value\">{last_score} / {last_total}</div>\n          <div class=\"stat-sub\">\uac00\uc7a5 \ucd5c\uadfc 1\ud68c</div>\n        </div>\n      </div>\n    </div>\n    \"\"\"\n    components.html(dashboard_html, height=330)\n\n    st.markdown(\"### \u274c \uc790\uc8fc \ud2c0\ub9b0 \ub2e8\uc5b4 TOP10 (\ucd5c\uadfc 50\ud68c)\")\n\n    counter = Counter()\n    for row in (res.data or []):\n        wl = row.get(\"wrong_list\") or []\n        if isinstance(wl, list):\n            for w in wl:\n                word = str(w.get(\"\ub2e8\uc5b4\", \"\")).strip()\n                if word:\n                    counter[word] += 1\n\n    if not counter:\n        st.caption(\"\uc544\uc9c1 \uc624\ub2f5 \ub370\uc774\ud130\uac00 \ucda9\ubd84\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uba87 \ubc88 \ub354 \ud480\uba74 TOP10\uc774 \uc0dd\uaca8\uc694 \ud83d\ude42\")\n        return\n\n    # --- TOP10 \uce74\ub4dc\ud615 CSS (\ub9c8\uc774\ud398\uc774\uc9c0\uc5d0\uc11c\ub9cc \uc4f0\ub3c4\ub85d \uc774 \ube14\ub85d \ubc14\ub85c \uc704\uc5d0 \ub123\ub294 \uac8c \uc548\uc804) ---\n    st.markdown(\"\"\"\n    <style>\n    .wt10-card{\n      border:1px solid rgba(120,120,120,0.25);\n      border-radius:18px;\n      padding:14px 16px;\n      margin:12px 0;\n      background: rgba(255,255,255,0.02);\n      display:flex;\n      align-items:center;\n      justify-content:space-between;\n      gap:14px;\n    }\n    .wt10-left{\n      display:flex;\n      flex-direction:column;\n      gap:6px;\n      min-width: 0;\n    }\n    .wt10-title{\n      font-size:18px;\n      font-weight:900;\n      line-height:1.15;\n      overflow:hidden;\n      text-overflow:ellipsis;\n      white-space:nowrap;\n    }\n    .wt10-sub{\n      font-size:13px;\n      opacity:.75;\n    }\n    .wt10-badge{\n      border:1px solid rgba(120,120,120,0.25);\n      background: rgba(255,255,255,0.03);\n      border-radius:999px;\n      padding:7px 12px;\n      font-size:13px;\n      font-weight:900;\n      white-space:nowrap;\n    }\n    </style>\n    \"\"\", unsafe_allow_html=True)\n\n    def render_wrong_top10_card(rank: int, word: str, cnt: int):\n        st.markdown(f\"\"\"\n    <div class=\"jp\">\n      <div class=\"wt10-card\">\n        <div class=\"wt10-left\">\n          <div class=\"wt10-title\">#{rank} {word}</div>\n          <div class=\"wt10-sub\">\ucd5c\uadfc 50\ud68c \uae30\uc900</div>\n        </div>\n        <div class=\"wt10-badge\">\uc624\ub2f5 {cnt}\ud68c</div>\n      </div>\n    </div>\n    \"\"\", unsafe_allow_html=True)\n\n    top10 = counter.most_common(10)\n    for i, (w, cnt) in enumerate(top10, start=1):\n        render_wrong_top10_card(i, str(w), int(cnt))\n\n    if st.button(\"\u274c \uc774 TOP10\uc73c\ub85c \uc2dc\ud5d8 \ubcf4\uae30\", type=\"primary\", use_container_width=True, key=\"btn_quiz_from_top10\"):\n        clear_question_widget_keys()\n        weak_wrong_list = [{\"\ub2e8\uc5b4\": w} for (w, _cnt) in top10]\n        retry_quiz = build_quiz_from_wrongs(weak_wrong_list, st.session_state.quiz_type)\n\n        k = mastery_key(qtype=st.session_state.quiz_type)\n        st.session_state.setdefault(\"mastery_done\", {})\n        st.session_state.mastery_done[k] = False\n\n        start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)\n        st.session_state[\"_scroll_top_once\"] = True\n        st.session_state.page = \"quiz\"\n        st.rerun()\n\ndef reset_quiz_state_only():\n    clear_question_widget_keys()\n    for k in [\"quiz\", \"answers\", \"submitted\", \"wrong_list\",\n              \"saved_this_attempt\", \"stats_saved_this_attempt\",\n              \"session_stats_applied_this_attempt\"]:\n        st.session_state.pop(k, None)\n\ndef go_quiz_from_home():\n    reset_quiz_state_only()\n    st.session_state.page = \"quiz\"\n    st.session_state[\"_scroll_top_once\"] = True\n\ndef render_home():\n    u = st.session_state.get(\"user\")\n    email = (getattr(u, \"email\", None) if u else None) or st.session_state.get(\"login_email\", \"\")\n\n    st.markdown(\n        f\"\"\"\n<div class=\"jp headbar\">\n  <div class=\"headtitle\">\u2728\ud558\ud14c\ub098\uc77c\ubcf8\uc5b4 \ud55c\uc790\uc815\ubcf5</div>\n  <div class=\"headhello\">\ud658\uc601\ud569\ub2c8\ub2e4 \ud83d\ude42 <span class=\"mail\">{email}</span></div>\n</div>\n\"\"\",\n        unsafe_allow_html=True\n    )\n\n    quotes = [\n        \"\ubc30\uc6c0\uc740 \ub9e4\uc77c \uc0c8\ub85c \uc2dc\uc791\ud574\ub3c4 \ub2a6\uc9c0 \uc54a\ub2e4.\",\n        \"\uc624\ub298\uc758 \ud55c \ubb38\uc81c\ub294 \ub0b4\uc77c\uc758 \uc790\uc2e0\uac10\uc774\ub2e4.\",\n        \"\uc870\uae08\uc774\ub77c\ub3c4 \uc190\uc744 \uc6c0\uc9c1\uc778 \ub0a0\uc740 \uc2e4\ud328\uac00 \uc544\ub2c8\ub2e4.\",\n        \"\uc644\ubcbd\ubcf4\ub2e4 \u2018\uacc4\uc18d\u2019\uc774 \ub354 \uac15\ud558\ub2e4.\",\n        \"\ub8e8\ud2f4\uc740 \uc791\uac8c, \uc9c0\uc18d\uc740 \uae38\uac8c.\",\n    ]\n    q = random.choice(quotes)\n\n    st.markdown(\n        f\"\"\"\n<div class=\"jp\" style=\"\n  margin-top:1px;\n  border:1px solid rgba(120,120,120,0.18);\n  border-radius:18px; padding:16px; background:rgba(255,255,255,0.03);\">\n  <div style=\"font-weight:900; font-size:14px; opacity:.75;\">\uc624\ub298\uc758 \ub9d0</div>\n  <div style=\"margin-top:6px; font-weight:900; font-size:20px; line-height:1.3;\">{q}</div>\n  <div style=\"margin-top:10px; opacity:.80; font-size:13px; line-height:1.55;\">\n    \uc77c\ubcf8\uc5b4\uacf5\ubd80, \uac00\ubccd\uac8c \uc2dc\uc791\ud574 \ubcfc\uae4c\uc694?\n  </div>\n</div>\n\"\"\",\n        unsafe_allow_html=True,\n    )\n    \n    st.markdown(\"<div style='height:10px'></div>\", unsafe_allow_html=True)\n    st.divider()\n    \n    c1, c2, c3 = st.columns([5, 3, 3])\n    with c1:\n        st.button(\"\u25b6 \uc624\ub298\uc758 \ud034\uc988 \uc2dc\uc791\", type=\"primary\", use_container_width=True,\n                  key=\"btn_home_start\", on_click=go_quiz_from_home)\n    with c2:\n        st.button(\"\ud83d\udccc \ub9c8\uc774\ud398\uc774\uc9c0\", use_container_width=True,\n                  key=\"btn_home_my\", on_click=nav_to, args=(\"my\",))\n    with c3:\n        st.button(\"\ud83d\udeaa \ub85c\uadf8\uc544\uc6c3\", use_container_width=True,\n                  key=\"btn_home_logout\", on_click=nav_logout)\n\n# ============================================================\n# \u2705 \uc571 \uc2dc\uc791: refresh \u2192 \ub85c\uadf8\uc778 \uac15\uc81c \u2192 \ud398\uc774\uc9c0 \uc124\uc815\n# ============================================================\nok = refresh_session_from_cookie_if_needed(force=False)\nif not ok and (cookies.get(\"refresh_token\") or cookies.get(\"access_token\")):\n    clear_auth_everywhere()\n    st.caption(\"\uc138\uc158 \ubcf5\uc6d0\uc5d0 \uc2e4\ud328\ud574\uc11c \ub85c\uadf8\uc778\uc744 \ub2e4\uc2dc \uc694\uccad\ud569\ub2c8\ub2e4.\")\n\nrequire_login()\n\nALLOWED_PAGES = {\"home\", \"quiz\", \"my\", \"admin\"}\nif \"page\" not in st.session_state:\n    st.session_state.page = \"home\"\nif st.session_state.get(\"page\") not in ALLOWED_PAGES:\n    st.session_state.page = \"home\"\n\nuser = st.session_state.user\nuser_id = user.id\nuser_email = getattr(user, \"email\", None) or st.session_state.get(\"login_email\")\nsb_authed = get_authed_sb()\n\ntry:\n    available_types = get_available_quiz_types() if sb_authed is not None else QUIZ_TYPES_USER\nexcept Exception:\n    available_types = QUIZ_TYPES_USER\n\n# progress \uc790\ub3d9\ubcf5\uc6d0 OFF (\uc6d0\ubcf8 \uc720\uc9c0)\nst.session_state.progress_restored = True\n\nif \"level\" not in st.session_state:\n    st.session_state.level = \"N5\"\n\n# title\nif st.session_state.get(\"page\") != \"home\":\n    u = st.session_state.get(\"user\")\n    email = (getattr(u, \"email\", None) if u else None) or st.session_state.get(\"login_email\", \"\")\n    st.markdown(\n        f\"\"\"\n<div class=\"jp headbar\">\n  <div class=\"headtitle\">\u2728 \ud55c\uc790 \ud034\uc988</div>\n  <div class=\"headhello\">\ud658\uc601\ud569\ub2c8\ub2e4 \ud83d\ude42 <span class=\"mail\">{email}</span></div>\n</div>\n\"\"\",\n        unsafe_allow_html=True\n    )\n\n# \ud504\ub85c\ud544/\ucd9c\uc11d\nif sb_authed is not None:\n    ensure_profile(sb_authed, user)\n    att = mark_attendance_once(sb_authed)\n    if att:\n        st.session_state[\"streak_count\"] = int(att.get(\"streak_count\", 0) or 0)\n        st.session_state[\"did_attend_today\"] = bool(att.get(\"did_attend\", False))\nelse:\n    st.caption(\"\uc138\uc158 \ud1a0\ud070\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. (sb_authed=None) \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n\n# ============================================================\n# \u2705 \ub77c\uc6b0\ud305\n# ============================================================\nif st.session_state.page == \"home\":\n    render_home()\n    st.stop()\n\nif st.session_state.page == \"admin\":\n    if not is_admin():\n        st.session_state.page = \"quiz\"\n        st.warning(\"\uad00\ub9ac\uc790 \uad8c\ud55c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.\")\n        st.rerun()\n    render_admin_dashboard()\n    st.stop()\n\nif st.session_state.page == \"my\":\n    try:\n        render_my_dashboard()\n    except Exception:\n        st.error(\"\ub9c8\uc774\ud398\uc774\uc9c0\uc5d0\uc11c \uc608\uc678\uac00 \ubc1c\uc0dd\ud588\uc2b5\ub2c8\ub2e4. \uc544\ub798 Traceback\uc744 \ud655\uc778\ud574 \uc8fc\uc138\uc694.\")\n        st.code(traceback.format_exc())\n    st.stop()\n\n# quiz page\nrender_topcard()\nrender_sound_toggle()  # \ud83d\udd0a \uc18c\ub9ac ON/OFF \ubc84\ud2bc(\ucd5c\ucd08 1\ud68c \ud074\ub9ad \ud544\uc694)\n\n\n# ============================================================\n# \u2705 \uc0c1\ub2e8: \uc624\ub298\uc758 \ubaa9\ud45c + \ucd9c\uc11d \ubc30\uc9c0\n# ============================================================\nstreak = st.session_state.get(\"streak_count\")\ndid_today = st.session_state.get(\"did_attend_today\")\n\nif streak is not None:\n    if did_today:\n        st.success(f\"\u2705 \uc624\ub298 \ucd9c\uc11d \uc644\ub8cc!  (\uc5f0\uc18d {streak}\uc77c)\")\n    else:\n        st.caption(f\"\uc5f0\uc18d \ucd9c\uc11d {streak}\uc77c\")\n\n    if streak >= 30:\n        st.info(\"\ud83d\udd25 30\uc77c \uc5f0\uc18d \ub2ec\uc131! \uc9c4\uc9dc \ub808\uc804\ub4dc\u2026\")\n    elif streak >= 7:\n        st.info(\"\ud83c\udfc5 7\uc77c \uc5f0\uc18d \ub2ec\uc131! \ud750\ub984\uc774 \uc7a1\ud614\uc5b4\uc694.\")\n\nif \"today_goal\" not in st.session_state:\n    st.session_state.today_goal = \"\uc624\ub298\uc740 10\ubb38\ud56d 1\ud68c \uc644\uc8fc\"\nif \"today_goal_done\" not in st.session_state:\n    st.session_state.today_goal_done = False\n\nwith st.container():\n    st.markdown(\"### \ud83c\udfaf \uc624\ub298\uc758 \ubaa9\ud45c(\ub8e8\ud2f4)\")\n    c1, c2 = st.columns([7, 3])\n    with c1:\n        st.session_state.today_goal = st.text_input(\n            \"\ubaa9\ud45c \ubb38\uc7a5\",\n            value=st.session_state.today_goal,\n            label_visibility=\"collapsed\",\n            placeholder=\"\uc608) \uc624\ub298\uc740 10\ubb38\ud56d 2\ud68c + \uc624\ub2f5\ub9cc \ub2e4\uc2dc\ud480\uae30 1\ud68c\",\n        )\n    with c2:\n        st.session_state.today_goal_done = st.checkbox(\"\ub2ec\uc131\", value=bool(st.session_state.today_goal_done))\n\n    if st.session_state.today_goal_done:\n        st.success(\"\uc88b\uc544\uc694. \uc624\ub298 \ub8e8\ud2f4 \uc644\ub8cc \u2705\")\n    else:\n        st.caption(\"\uac00\ubccd\uac8c\ub77c\ub3c4 \uccb4\ud06c\ud558\uba74 \ub8e8\ud2f4\uc774 \ub04a\uae30\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4.\")\n\nst.divider()\n\n# ============================================================\n# \u2705 \uc138\uc158 \ucd08\uae30\ud654\n# ============================================================\nif \"quiz_version\" not in st.session_state:\n    st.session_state.quiz_version = 0\nif \"submitted\" not in st.session_state:\n    st.session_state.submitted = False\nif \"wrong_list\" not in st.session_state:\n    st.session_state.wrong_list = []\nif \"saved_this_attempt\" not in st.session_state:\n    st.session_state.saved_this_attempt = False\nif \"stats_saved_this_attempt\" not in st.session_state:\n    st.session_state.stats_saved_this_attempt = False\nif \"session_stats_applied_this_attempt\" not in st.session_state:\n    st.session_state.session_stats_applied_this_attempt = False\nif \"history\" not in st.session_state:\n    st.session_state.history = []\nif \"progress_dirty\" not in st.session_state:\n    st.session_state.progress_dirty = False\nif \"wrong_counter\" not in st.session_state:\n    st.session_state.wrong_counter = {}\nif \"total_counter\" not in st.session_state:\n    st.session_state.total_counter = {}\n\nensure_mastered_words_shape()\nensure_excluded_wrong_words_shape()\nensure_mastery_banner_shape()\n\n# ============================================================\n# \u2705 \uc0c1\ub2e8 UI: \ub808\ubca8 \ubc84\ud2bc(N5~N1) \u2192 \uc720\ud615 \ubc84\ud2bc(\uce74\ub4dc\ud615) \u2192 \ucea1\uc158 \u2192 divider\n# ============================================================\n\ndef on_pick_level(lv: str):\n    lv = str(lv).strip().upper()\n    if lv == st.session_state.level:\n        return\n    st.session_state.level = lv\n\n    clear_question_widget_keys()\n    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)\n    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)\n\n    st.session_state[\"_scroll_top_once\"] = True\n    \ndef on_pick_qtype(qt: str):\n    qt = str(qt).strip()\n    if qt == st.session_state.quiz_type:\n        return\n    st.session_state.quiz_type = qt\n\n    clear_question_widget_keys()\n    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)\n    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)\n\n    st.session_state[\"_scroll_top_once\"] = True\n  \nst.markdown('<div class=\"qtypewrap\">', unsafe_allow_html=True)\n\n# ----------------------------\n# 1) \ub808\ubca8 \ubc84\ud2bc(N5~N1) \uba3c\uc800\n# ----------------------------\nlevel_cols = st.columns(len(LEVEL_OPTIONS), gap=\"small\")\nfor i, lv in enumerate(LEVEL_OPTIONS):\n    is_selected_lv = (lv == st.session_state.level)\n    btn_lv_type = \"primary\" if is_selected_lv else \"secondary\"\n    icon_lv = \"\u2705 \" if is_selected_lv else \"\"\n    label_lv = LEVEL_LABEL_MAP.get(lv, lv)\n\n    with level_cols[i]:\n        st.button(\n            f\"{icon_lv}{label_lv}\",\n            use_container_width=True,\n            type=btn_lv_type,\n            key=f\"btn_level_{lv}\",\n            on_click=on_pick_level,\n            args=(lv,),\n        )\n\nst.markdown('<div class=\"qtype_hint jp\">\u2728\ub808\ubca8\uc744 \uc120\ud0dd\ud558\uc138\uc694</div>', unsafe_allow_html=True)\n\n# ----------------------------\n# 2) \uc720\ud615 \ubc84\ud2bc(\ubc1c\uc74c/\ub73b/\ud55c\u2192\uc77c)\n# ----------------------------\ntype_cols = st.columns(len(available_types), gap=\"small\")\nfor i, qt in enumerate(available_types):\n    is_selected = (qt == st.session_state.quiz_type)\n    btn_type = \"primary\" if is_selected else \"secondary\"\n    icon = \"\u2705 \" if is_selected else \"\"\n    label = quiz_label_map.get(qt, qt)\n\n    with type_cols[i]:\n        st.button(\n            f\"{icon}{label}\",\n            use_container_width=True,\n            type=btn_type,\n            key=f\"btn_qtype_{qt}\",\n            on_click=on_pick_qtype,\n            args=(qt,),\n        )\n\nst.markdown('<div class=\"qtype_hint jp\">\u2728\uc720\ud615\uc744 \uc120\ud0dd\ud558\uc138\uc694</div>', unsafe_allow_html=True)\n\nst.markdown('</div>', unsafe_allow_html=True)\n\n# \u2705 divider \uac04\uaca9\uc740 tight-divider \ub798\ud37c\ub85c\nst.markdown('<div class=\"tight-divider\">', unsafe_allow_html=True)\nst.divider()\nst.markdown('</div>', unsafe_allow_html=True)\n\n# ============================================================\n# \u2705 \ubc84\ud2bc: \uc0c8 \ubb38\uc81c / \ub9de\ud78c \ub2e8\uc5b4 \uc81c\uc678 \ucd08\uae30\ud654\n# ============================================================\ncbtn1, cbtn2 = st.columns(2)\n\nwith cbtn1:\n    if st.button(\"\ud83d\udd04 \uc0c8 \ubb38\uc81c(\ub79c\ub364 10\ubb38\ud56d)\", use_container_width=True, key=\"btn_new_random_10\"):\n        k_now = mastery_key()\n        if st.session_state.get(\"mastery_done\", {}).get(k_now, False):\n            st.session_state[\"_scroll_top_once\"] = True\n            st.rerun()\n\n        clear_question_widget_keys()\n        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)\n        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)\n        st.session_state[\"_scroll_top_once\"] = True\n        st.rerun()\n\nwith cbtn2:\n    if st.button(\"\u2705 \ub9de\ud78c \ub2e8\uc5b4 \uc81c\uc678 \ucd08\uae30\ud654\", use_container_width=True, key=\"btn_reset_mastered_current_type\"):\n        ensure_mastered_words_shape()\n        k_now = mastery_key()\n        st.session_state.mastered_words[k_now] = set()\n        st.session_state.mastery_banner_shown[k_now] = False\n        st.session_state.mastery_done[k_now] = False\n\n        clear_question_widget_keys()\n        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)\n        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)\n\n        st.success(f\"\ucd08\uae30\ud654 \uc644\ub8cc (\uc720\ud615: {quiz_label_map[st.session_state.quiz_type]})\")\n        st.session_state[\"_scroll_top_once\"] = True\n        st.rerun()\n\n# \uc815\ubcf5 \uc548\ub0b4\nk_now = mastery_key()\nif st.session_state.get(\"mastery_done\", {}).get(k_now, False):\n    st.success(\"\ud83c\udfc6 \uc774 \uc720\ud615\uc744 \uc644\uc804\ud788 \uc815\ubcf5\ud588\uc5b4\uc694!\")\n    st.caption(\"\ud83d\udc49 \ub2e4\ub978 \uc720\ud615\uc744 \uc120\ud0dd\ud558\uac70\ub098, '\ub9de\ud78c \ub2e8\uc5b4 \uc81c\uc678 \ucd08\uae30\ud654'\ub85c \ub2e4\uc2dc \uc2dc\uc791\ud560 \uc218 \uc788\uc5b4\uc694.\")\n\n# ============================================================\n# \u2705 (\uc911\uc694) UI\ub294 \uba3c\uc800 \ubcf4\uc5ec\uc8fc\uace0, \ud034\uc988\uac00 \uc5c6\uc73c\uba74 \uc5ec\uae30\uc11c\ub9cc \uba48\ucd98\ub2e4\n# ============================================================\nif \"quiz\" not in st.session_state or not isinstance(st.session_state.quiz, list):\n    st.session_state.quiz = []\n\n# \uc544\uc9c1 \ud034\uc988\uac00 \uc5c6\ub2e4\uba74 1\ud68c\ub9cc \uc0dd\uc131 \uc2dc\ub3c4 (UI\ub294 \uc774\ubbf8 \uc704\uc5d0\uc11c \ub2e4 \ubcf4\uc5ec\uc900 \uc0c1\ud0dc)\nk_now = mastery_key()\nis_mastered_done = bool(st.session_state.get(\"mastery_done\", {}).get(k_now, False))\n\nif (not is_mastered_done) and len(st.session_state.quiz) == 0:\n    clear_question_widget_keys()\n    st.session_state.quiz = build_quiz(st.session_state.quiz_type, st.session_state.level) or []\n    st.session_state.submitted = False\n\n# \uadf8\ub798\ub3c4 0\uac1c\uba74: \ubc84\ud2bc\uc740 \uc774\ubbf8 \ubcf4\uc774\ub294 \uc0c1\ud0dc \u2192 \uc548\ub0b4\ub9cc \ud558\uace0 \uba48\ucda4\nif len(st.session_state.quiz) == 0:\n    st.info(\"\uc774 \ub808\ubca8\uc5d0 \ucd9c\uc81c\ud560 \ub2e8\uc5b4\uac00 \uc5c6\uc5b4\uc694. \ub2e4\ub978 \ub808\ubca8\uc744 \uc120\ud0dd\ud558\uac70\ub098, CSV\uc758 level \uac12\uc744 \ud655\uc778\ud574 \uc8fc\uc138\uc694.\")\n    st.stop()\n\n# ============================================================\n# \u2705 answers \uae38\uc774 \uc790\ub3d9 \ub9de\ucda4\n# ============================================================\nif \"quiz\" not in st.session_state or not isinstance(st.session_state.quiz, list):\n    st.session_state.quiz = []\n\nif len(st.session_state.quiz) == 0:\n    st.session_state.quiz = build_quiz(st.session_state.quiz_type, st.session_state.level) or []\n\nquiz_len = len(st.session_state.quiz)\nif \"answers\" not in st.session_state or not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != quiz_len:\n    st.session_state.answers = [None] * quiz_len\n\n# \uc815\ubcf5 \uc0c1\ud0dc\uba74 \ubb38\uc81c \uc601\uc5ed \ucc28\ub2e8\nk_now = mastery_key()\nif bool(st.session_state.get(\"mastery_done\", {}).get(k_now, False)):\n    st.stop()\n\n# ============================================================\n# \u2705 \ubb38\uc81c \ud45c\uc2dc (\ub3d9\uadf8\ub780 \ubc30\uc9c0: \u2460 \u2461 \u2462 ... + \uac19\uc740 \uc904)\n# ============================================================\ncircled_nums = \"\u2460\u2461\u2462\u2463\u2464\u2465\u2466\u2467\u2468\u2469\u246a\u246b\u246c\u246d\u246e\u246f\u2470\u2471\u2472\u2473\u3251\u3252\u3253\u3254\u3255\u3256\u3257\u3258\u3259\u325a\u325b\u325c\u325d\u325e\u325f\u32b1\u32b2\u32b3\u32b4\u32b5\u32b6\u32b7\u32b8\u32b9\u32ba\u32bb\u32bc\u32bd\u32be\u32bf\"\n\nfor idx, q in enumerate(st.session_state.quiz):\n    badge = circled_nums[idx] if idx < len(circled_nums) else f\"({idx+1})\"\n\n    st.markdown(\n        f\"\"\"\n<div class=\"jp\" style=\"display:flex; align-items:baseline; gap:5px; margin: 10px 0 8px 0;\">\n  <div style=\"\n    flex:0 0 auto;\n    font-size:20px;\n    line-height:1;\n    font-weight:900;   /* \u2190 \uc774 \uc904 \ucd94\uac00 */\n    /* \u2705 \ubbf8\uc138 \ubcf4\uc815 (\ud544\uc694 \uc2dc \uc22b\uc790\ub9cc \uc870\uc808) */\n    transform: translateY(1px);\n  \">{badge}</div>\n\n  <div style=\"\n    flex:1 1 auto;\n    font-size:18px;\n    font-weight:500;\n    line-height:1.35;\n  \">{q[\"prompt\"]}</div>\n</div>\n\"\"\",\n    unsafe_allow_html=True\n)\n    widget_key = f\"q_{st.session_state.quiz_version}_{idx}\"\n\n    prev = st.session_state.answers[idx]\n    default_index = None\n    if prev is not None and prev in q[\"choices\"]:\n        default_index = q[\"choices\"].index(prev)\n\n    choice = st.radio(\n        label=\"\ubcf4\uae30\",\n        options=q[\"choices\"],\n        index=default_index,\n        key=widget_key,\n        label_visibility=\"collapsed\",\n        on_change=mark_progress_dirty,\n    )\n    st.session_state.answers[idx] = choice\n\nsync_answers_from_widgets()\n\n# ============================================================\n# \u2705 \uc81c\ucd9c/\ucc44\uc810\n# ============================================================\nquiz_len = len(st.session_state.quiz)\nall_answered = (quiz_len > 0) and all(a is not None for a in st.session_state.answers)\n\nif st.button(\"\u2705 \uc81c\ucd9c\ud558\uace0 \ucc44\uc810\ud558\uae30\", disabled=not all_answered, type=\"primary\", use_container_width=True, key=\"btn_submit\"):\n    st.session_state.submitted = True\n    st.session_state.session_stats_applied_this_attempt = False\n\nif not all_answered:\n    st.info(\"\ubaa8\ub4e0 \ubb38\uc81c\uc5d0 \ub2f5\uc744 \uc120\ud0dd\ud558\uba74 \uc81c\ucd9c \ubc84\ud2bc\uc774 \ud65c\uc131\ud654\ub429\ub2c8\ub2e4.\")\n\n# ============================================================\n# \u2705 \uc81c\ucd9c \ud6c4 \ud654\uba74\n# ============================================================\nif st.session_state.submitted:\n    show_post_ui = (SHOW_POST_SUBMIT_UI == \"Y\") or is_admin()\n\n    ensure_mastered_words_shape()\n    ensure_excluded_wrong_words_shape()\n\n    current_type = st.session_state.quiz_type\n    k_now = mastery_key()\n\n    score = 0\n    wrong_list = []\n\n    for idx, q in enumerate(st.session_state.quiz):\n        picked = st.session_state.answers[idx]\n        correct = q[\"correct_text\"]\n        word_key = str(q.get(\"jp_word\", \"\")).strip()\n\n        if picked == correct:\n            score += 1\n            if word_key:\n                st.session_state.mastered_words.setdefault(k_now, set()).add(word_key)\n        else:\n            # \u2705 \uc624\ub2f5\ub178\ud2b8 \ucc44\uc6b0\uae30\n            wrong_list.append({\n                \"No\": idx + 1,\n                \"\ubb38\uc81c\": str(q.get(\"prompt\", \"\")),\n                \"\ub0b4 \ub2f5\": \"\" if picked is None else str(picked),\n                \"\uc815\ub2f5\": str(correct),\n                \"\ub2e8\uc5b4\": str(q.get(\"jp_word\", \"\")).strip(),\n                \"\uc77d\uae30\": str(q.get(\"reading\", \"\")).strip(),\n                \"\ub73b\": str(q.get(\"meaning\", \"\")).strip(),\n                \"\uc720\ud615\": current_type,\n            })\n\n    st.session_state.wrong_list = wrong_list\n\n    quiz_len = len(st.session_state.quiz)\n    st.success(f\"\uc810\uc218: {score} / {quiz_len}\")\n    ratio = score / quiz_len if quiz_len else 0\n\n    # \u2705 \uc810\uc218 \uae30\ubc18 SFX (\uc81c\ucd9c \uc9c1\ud6c4 1\ud68c)\n    if ratio == 1:\n        sfx(\"perfect\")\n    elif ratio < 1:\n        sfx(\"wrong\")  # (\ubd80\ubd84\uc624\ub2f5\uc774 \uc788\uc73c\uba74 '\uc090~' \ud55c \ubc88)\n    \n    if ratio == 1:\n        st.balloons()\n        st.success(\"\ud83c\udf89 \uc644\ubcbd\ud574\uc694! \uc804\ubd80 \uc815\ub2f5\uc785\ub2c8\ub2e4. \uc815\ub9d0 \uc798\ud588\uc5b4\uc694!\")\n        st.caption(\"\u203b \uc815\ubcf5 \ud310\uc815\uc740 \u2018\ub354 \uc774\uc0c1 \ucd9c\uc81c\ud560 \ub2e8\uc5b4\uac00 \uc5c6\uc744 \ub54c\u2019 \uc790\ub3d9\uc73c\ub85c \ud45c\uc2dc\ub429\ub2c8\ub2e4.\")\n    elif ratio >= 0.7:\n        st.info(\"\ud83d\udc4d \uc798\ud558\uace0 \uc788\uc5b4\uc694! \uc870\uae08\ub9cc \ub354 \ub2e4\ub4ec\uc73c\uba74 \uc644\ubcbd\ud574\uc9c8 \uac70\uc608\uc694.\")\n    else:\n        st.warning(\"\ud83d\udcaa \uad1c\ucc2e\uc544\uc694! \ud2c0\ub9b0 \ubb38\uc81c\ub294 \uc131\uc7a5\uc758 \uc7ac\ub8cc\uc608\uc694. \ub2e4\uc2dc \ud55c \ubc88 \ub3c4\uc804\ud574\ubd10\uc694.\")\n\n    # \u2705 DB \uc800\uc7a5\n    sb_authed_local = get_authed_sb()\n    if sb_authed_local is None:\n        if show_post_ui:\n            st.warning(\"DB \uc800\uc7a5/\uc870\ud68c\uc6a9 \ud1a0\ud070\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \ub2e4\uc2dc \ub85c\uadf8\uc778\ud574 \uc8fc\uc138\uc694.\")\n    else:\n        if not st.session_state.saved_this_attempt:\n            def _save():\n                return save_attempt_to_db(\n                    sb_authed=sb_authed_local,\n                    user_id=user_id,\n                    user_email=user_email,\n                    level=st.session_state.level,\n                    quiz_type=current_type,\n                    quiz_len=quiz_len,\n                    score=score,\n                    wrong_list=wrong_list,\n                )\n            try:\n                run_db(_save)\n                st.session_state.saved_this_attempt = True\n            except Exception as e:\n                if show_post_ui:\n                    st.warning(\"DB \uc800\uc7a5\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4. (\ud14c\uc774\ube14/\uceec\ub7fc/\uad8c\ud55c/RLS \uc815\ucc45 \ud655\uc778 \ud544\uc694)\")\n                    st.write(str(e))\n\n        if not st.session_state.stats_saved_this_attempt:\n            def _save_stats_bulk():\n                sync_answers_from_widgets()\n                items = build_word_results_bulk_payload(\n                    quiz=st.session_state.quiz,\n                    answers=st.session_state.answers,\n                    quiz_type=current_type,\n                    level=st.session_state.level,\n                )\n                if not items:\n                    return None\n                return sb_authed_local.rpc(\"record_word_results_bulk\", {\"p_items\": items}).execute()\n\n            try:\n                run_db(_save_stats_bulk)\n                st.session_state.stats_saved_this_attempt = True\n                if show_post_ui:\n                    st.success(\"\u2705 \ub2e8\uc5b4 \ud1b5\uacc4(bulk) \uc800\uc7a5 \uc131\uacf5\")\n            except Exception as e:\n                if show_post_ui:\n                    st.error(\"\u274c \ub2e8\uc5b4 \ud1b5\uacc4(bulk) \uc800\uc7a5 \uc2e4\ud328\")\n                    st.exception(e)\n\n        if show_post_ui:\n            st.subheader(\"\ud83d\udccc \ub0b4 \ucd5c\uadfc \uae30\ub85d\")\n            def _fetch_hist():\n                return fetch_recent_attempts(sb_authed_local, user_id, limit=10)\n\n            try:\n                res = run_db(_fetch_hist)\n                if not res.data:\n                    st.info(\"\uc544\uc9c1 \uc800\uc7a5\ub41c \uae30\ub85d\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \ubb38\uc81c\ub97c \ud480\uace0 \uc81c\ucd9c\ud558\uba74 \uae30\ub85d\uc774 \uc313\uc5ec\uc694.\")\n                else:\n                    hist = pd.DataFrame(res.data).copy()\n                    hist[\"created_at\"] = to_kst_naive(hist[\"created_at\"])\n                    hist[\"\uc720\ud615\"] = hist[\"pos_mode\"].map(lambda x: quiz_label_for_table.get(x, x))\n                    hist[\"\uc815\ub2f5\ub960\"] = (hist[\"score\"] / hist[\"quiz_len\"]).fillna(0.0)\n\n                    avg_rate = float(hist[\"\uc815\ub2f5\ub960\"].mean() * 100)\n                    best = int(hist[\"score\"].max())\n                    last_score = int(hist.iloc[0][\"score\"])\n                    last_total = int(hist.iloc[0][\"quiz_len\"])\n\n                    # \u2705 \ub9c8\uc774\ud398\uc774\uc9c0 \uc0c1\ub2e8 3\uce74\ub4dc (components.html\ub85c \uac15\uc81c \ub80c\ub354\ub9c1)\n                    dashboard_html = f\"\"\"\n                    <style>\n                    .stat-grid{{\n                      display:grid;\n                      grid-template-columns: repeat(3, 1fr);\n                      gap:12px;\n                      margin: 6px 0 6px 0;\n                    }}\n                    .stat-card{{\n                      border:1px solid rgba(120,120,120,0.25);\n                      border-radius:18px;\n                      padding:14px 14px;\n                      background: rgba(255,255,255,0.02);\n                    }}\n                    .stat-label{{\n                      font-size:12px;\n                      font-weight:800;\n                      opacity:.72;\n                      line-height:1.2;\n                    }}\n                    .stat-value{{\n                      margin-top:6px;\n                      font-size:22px;\n                      font-weight:900;\n                      line-height:1.1;\n                    }}\n                    .stat-sub{{\n                      margin-top:6px;\n                      font-size:12px;\n                      opacity:.70;\n                      line-height:1.2;\n                    }}\n                    @media (max-width: 520px){{\n                      .stat-grid{{ grid-template-columns: 1fr; }}\n                      .stat-value{{ font-size:24px; }}\n                    }}\n                    </style>\n\n                    <div class=\"jp\">\n                      <div class=\"stat-grid\">\n                        <div class=\"stat-card\">\n                          <div class=\"stat-label\">\ucd5c\uadfc \ud3c9\uade0(\ucd5c\ub300 50\ud68c)</div>\n                          <div class=\"stat-value\">{avg_rate:.0f}%</div>\n                          <div class=\"stat-sub\">\uc815\ub2f5\ub960 \uae30\uc900</div>\n                        </div>\n\n                        <div class=\"stat-card\">\n                          <div class=\"stat-label\">\ucd5c\uace0 \uc810\uc218</div>\n                          <div class=\"stat-value\">{best} / {last_total}</div>\n                          <div class=\"stat-sub\">\ucd5c\uadfc \uae30\ub85d \uc911 \ucd5c\uace0</div>\n                        </div>\n\n                        <div class=\"stat-card\">\n                          <div class=\"stat-label\">\ucd5c\uadfc \uc810\uc218</div>\n                          <div class=\"stat-value\">{last_score} / {last_total}</div>\n                          <div class=\"stat-sub\">\uac00\uc7a5 \ucd5c\uadfc 1\ud68c</div>\n                        </div>\n                      </div>\n                    </div>\n                    \"\"\"\n    \n                    components.html(dashboard_html, height=330)\n\n            except Exception as e:\n                st.info(\"\uae30\ub85d\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4.\")\n                st.write(str(e))\n\n    # \u2705 \uc138\uc158 \ud1b5\uacc4(\ub85c\uceec \uce74\uc6b4\ud130) \uc801\uc6a9\uc740 '1\ubc88\ub9cc'\n    if not st.session_state.session_stats_applied_this_attempt:\n        st.session_state.history.append({\"type\": current_type, \"score\": score, \"total\": quiz_len})\n\n        for idx, q in enumerate(st.session_state.quiz):\n            word_key = str(q.get(\"jp_word\", \"\")).strip()\n            if word_key:\n                st.session_state.total_counter[word_key] = st.session_state.total_counter.get(word_key, 0) + 1\n                if st.session_state.answers[idx] != q[\"correct_text\"]:\n                    st.session_state.wrong_counter[word_key] = st.session_state.wrong_counter.get(word_key, 0) + 1\n\n        st.session_state.session_stats_applied_this_attempt = True\n\n# ============================================================\n# \u2705 \uc624\ub2f5\ub178\ud2b8 + \ub2e4\uc2dc\ud480\uae30\n# ============================================================\nif st.session_state.submitted and st.session_state.wrong_list:\n    st.subheader(\"\u274c \uc624\ub2f5 \ub178\ud2b8\")\n\n    st.markdown(\n        \"\"\"\n<style>\n.wrong-card{\n  border: 1px solid rgba(120,120,120,0.25);\n  border-radius: 16px;\n  padding: 14px 14px;\n  margin-bottom: 10px;\n  background: rgba(255,255,255,0.02);\n}\n.wrong-top{\n  display:flex;\n  align-items:flex-start;\n  justify-content:space-between;\n  gap:12px;\n  margin-bottom: 8px;\n}\n.wrong-title{ font-weight: 900; font-size: 15px; margin-bottom: 4px; }\n.wrong-sub{ opacity: 0.8; font-size: 12px; }\n.tag{\n  display:inline-flex;\n  align-items:center;\n  gap:6px;\n  padding: 5px 9px;\n  border-radius: 999px;\n  font-size: 12px;\n  font-weight: 700;\n  border: 1px solid rgba(120,120,120,0.25);\n  background: rgba(255,255,255,0.03);\n  white-space: nowrap;\n}\n.ans-row{\n  display:grid;\n  grid-template-columns: 72px 1fr;\n  gap:10px;\n  margin-top:6px;\n  font-size: 13px;\n}\n.ans-k{ opacity: 0.7; font-weight: 700; }\n</style>\n\"\"\",\n        unsafe_allow_html=True,\n    )\n\n    def _s(v):\n        return \"\" if v is None else str(v)\n\n    for w in st.session_state.wrong_list:\n        no = _s(w.get(\"No\"))\n        qtext = _s(w.get(\"\ubb38\uc81c\"))\n        picked = _s(w.get(\"\ub0b4 \ub2f5\"))\n        correct = _s(w.get(\"\uc815\ub2f5\"))\n        word = _s(w.get(\"\ub2e8\uc5b4\"))\n        reading = _s(w.get(\"\uc77d\uae30\"))\n        meaning = _s(w.get(\"\ub73b\"))\n        mode = quiz_label_map.get(w.get(\"\uc720\ud615\"), w.get(\"\uc720\ud615\", \"\"))\n\n        st.markdown(\n            f\"\"\"\n        <div class=\"jp\">\n          <div class=\"wrong-card\">\n            <div class=\"wrong-top\">\n              <div>\n              <div class=\"wrong-title\">Q{no}. {word}</div>\n              <div class=\"wrong-sub\">{qtext} \u00b7 \uc720\ud615: {mode}</div>\n            </div>\n            <div class=\"tag\">\uc624\ub2f5</div>\n          </div>\n\n          <div class=\"ans-row\"><div class=\"ans-k\">\ub0b4 \ub2f5</div><div>{picked}</div></div>\n          <div class=\"ans-row\"><div class=\"ans-k\">\uc815\ub2f5</div><div><b>{correct}</b></div></div>\n          <div class=\"ans-row\"><div class=\"ans-k\">\ubc1c\uc74c</div><div>{reading}</div></div>\n          <div class=\"ans-row\"><div class=\"ans-k\">\ub73b</div><div>{meaning}</div></div>\n        </div>\n        \"\"\",\n           unsafe_allow_html=True,\n        )\n\n    if st.button(\"\u274c \ud2c0\ub9b0 \ubb38\uc81c\ub9cc \ub2e4\uc2dc \ud480\uae30\", type=\"primary\", use_container_width=True, key=\"btn_retry_wrongs_bottom\"):\n        clear_question_widget_keys()\n        retry_quiz = build_quiz_from_wrongs(st.session_state.wrong_list, st.session_state.quiz_type)\n        start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)\n        st.session_state[\"_scroll_top_once\"] = True\n        st.rerun()\n\n# \ub2e4\uc74c 10\ubb38\ud56d\nif st.session_state.submitted:\n    if st.button(\"\u2705 \ub2e4\uc74c 10\ubb38\ud56d \uc2dc\uc791\ud558\uae30\", type=\"primary\", use_container_width=True, key=\"btn_next_10\"):\n        clear_question_widget_keys()\n        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)\n        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)\n        st.session_state[\"_scroll_top_once\"] = True\n        st.rerun()\n\n    show_naver_talk = (SHOW_NAVER_TALK == \"N\") or is_admin()\n    if show_naver_talk:\n        render_naver_talk()\n"

def render_kanji_app(supabase, user_email, user_id, user_plan):
    """✅ '한자' 선택 시, 사용자가 제공한 app.py(한자 앱)를 그대로 기동합니다."""
    _g = {
        "__name__": "__hatena_kanji_app__",
        "__file__": __file__,
    }
    # app.py 내부에서 streamlit을 import 하므로 여기서는 그대로 exec만 수행합니다.
    exec(KANJI_APP_CODE, _g, _g)
def render_home():
    """✅ 홈 대시보드: 학습 앱(단어/한자/회화) 선택 → 선택된 앱의 홈으로 진입"""
    st.title("하테나 일본어")
    st.caption("오늘도 가볍게 10분부터 시작해요.")

    # ✅ 앱 선택 상태
    if "app_mode" not in st.session_state:
        st.session_state["app_mode"] = None  # "word" | "kanji" | "conv"

    # ✅ 선택 UI
    st.subheader("무엇을 할까요?")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("📝 단어", use_container_width=True):
            st.session_state["app_mode"] = "word"
            st.session_state["page"] = "home"
            st.rerun()
    with c2:
        if st.button("🈶 한자", use_container_width=True):
            st.session_state["app_mode"] = "kanji"
            st.session_state["page"] = "home"
            st.rerun()
    with c3:
        if st.button("💬 회화 훈련", use_container_width=True):
            st.session_state["app_mode"] = "conv"
            st.session_state["page"] = "home"
            st.rerun()

    mode = st.session_state.get("app_mode")

    # ✅ 아직 선택 전이면 여기서 종료
    if not mode:
        st.info("위에서 학습을 선택해 주세요.")
        return

    # ✅ 선택된 앱 표시 + 변경 버튼
    label = {"word":"단어", "kanji":"한자", "conv":"회화 훈련"}.get(mode, str(mode))
    st.markdown(f"**선택된 학습:** {label}")
    if st.button("↩️ 다른 학습 선택", use_container_width=True):
        st.session_state["app_mode"] = None
        st.session_state["page"] = "home"
        st.rerun()

    st.divider()

    # ✅ 단어 앱: 기존(사용자 제공) 전체 코드 흐름 진입
    if mode == "word":
        render_word_home()
        return

    # ✅ 한자/회화: 추후 확장(현재는 자리만 잡아둠)
    if mode == "kanji":
        u = st.session_state.get("user")
        sb_authed_local = get_authed_sb()
        user_email = getattr(u, "email", None) if u else None
        user_id = getattr(u, "id", None) if u else None
        render_kanji_app(sb_authed_local, user_email, user_id, get_user_plan())
        return

    if mode == "conv":
        st.warning("회화 훈련은 다음 단계에서 붙일게요. (AI 대화/롤플레이/표현 드릴) 형태로 확장 가능합니다.")
        st.markdown("- 다음: 상황별 롤플레이 / 음성(TTS) / 오늘의 한 문장")
        return


def render_word_home():
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")

    # ✅ (1) 타이틀/환영
    st.markdown(
        f"""
<div class="jp headbar">
  <div class="headtitle">✨ 왕초보 탈출 하테나일본어</div>
  <div class="headhello">환영합니다 🙂 <span class="mail">{email}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ✅ (2) 오늘의 학습 리포트: 홈에서만 / 타이틀 다음, 오늘의 말 위
    try:
        sb_authed = get_authed_sb()
        user_id = getattr(u, "id", None) if u else None
        if sb_authed and user_id:
            render_today_report_db_only(sb_authed, user_id)
    except Exception:
        # 리포트 실패해도 홈 화면은 멈추지 않게
        pass

    # ✅ (3) 오늘의 말
    quotes = [
        "오늘 10문항이면 충분해요.",
        "루틴은 작게, 지속은 길게.",
        "정답보다 중요한 건 ‘계속’입니다.",
        "단어가 쌓이면 문장이 열립니다.",
        "오늘의 한 번이 내일의 자신감이에요.",
    ]
    q = random.choice(quotes)

    st.markdown(
        f"""
<div class="jp" style="
  margin-top:1px;
  border:1px solid rgba(120,120,120,0.18);
  border-radius:18px; padding:16px; background:rgba(255,255,255,0.03);">
  <div style="font-weight:900; font-size:14px; opacity:.75;">오늘의 말</div>
  <div style="margin-top:6px; font-weight:900; font-size:20px; line-height:1.3;">{q}</div>
  <div style="margin-top:10px; opacity:.80; font-size:13px; line-height:1.55;">
    품사 하나씩만 잡아도, 말이 빨라집니다.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.divider()

    c1, c2, c3 = st.columns([5, 3, 3])
    with c1:
        st.button("▶ 오늘의 퀴즈 시작", type="primary", use_container_width=True,
                  key="btn_home_start", on_click=go_quiz_from_home)
                  
    with c2:
        st.button("📌 마이페이지", use_container_width=True,
                  key="btn_home_my", on_click=nav_to, args=("my",))
    with c3:
        st.button("🚪 로그아웃", use_container_width=True,
                  key="btn_home_logout", on_click=nav_logout)


# ============================================================
# ✅ 오늘의 학습 리포트 (DB only / quiz_attempts 기반)
#   - 로그인 유저만 표시
#   - 오늘 푼 문항 / 정답률 / 오늘 오답 / 연속 학습(streak)
#   - 가장 많이 틀린 모드(pos_mode)
# ============================================================

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter
import html
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

import streamlit as st

KST = ZoneInfo("Asia/Seoul")

def _parse_dt_any(x) -> datetime | None:
    """Supabase created_at 파싱(ISO 문자열/datetime 모두 대응)."""
    if x is None:
        return None
    if isinstance(x, datetime):
        dt = x
    else:
        s = str(x).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def fetch_attempts_between(supabase, user_id: str, start_utc: datetime, end_utc: datetime) -> list[dict]:
    """기간 내 attempts 가져오기 (created_at은 보통 UTC timestamptz)."""
    try:
        res = (
            supabase.table("quiz_attempts")
            .select("created_at, quiz_len, score, wrong_count, pos_mode")
            .eq("user_id", user_id)
            .gte("created_at", start_utc.isoformat())
            .lt("created_at", end_utc.isoformat())
            .order("created_at", desc=False)
            .execute()
        )
        return res.data or []
    except Exception:
        return []

def _kst_day_key(dt_utc: datetime) -> str:
    """UTC dt -> KST 날짜키(YYYY-MM-DD)."""
    k = dt_utc.astimezone(KST)
    return k.strftime("%Y-%m-%d")

def build_today_report_from_rows(today_rows: list[dict], recent_rows: list[dict]) -> dict:
    # ✅ 오늘 집계
    today_total = 0
    today_correct = 0
    today_wrong = 0
    wrong_mode_counter = Counter()

    for r in (today_rows or []):
        qlen = int(r.get("quiz_len") or 0)
        score = int(r.get("score") or 0)

        wc_raw = r.get("wrong_count")
        if wc_raw is None or wc_raw == "":
            wc = max(0, qlen - score)
        else:
            wc = int(wc_raw or 0)

        mode = str(r.get("pos_mode") or "-")

        today_total += qlen
        today_correct += score
        today_wrong += wc

        if wc > 0:
            wrong_mode_counter[mode] += wc

    accuracy = 0
    if today_total > 0:
        accuracy = int(round((today_correct / today_total) * 100))

    top_wrong_mode = "-"
    if wrong_mode_counter:
        top_wrong_mode = wrong_mode_counter.most_common(1)[0][0]

    # ✅ 연속 학습(streak)
    day_has = set()
    for r in (recent_rows or []):
        dt = _parse_dt_any(r.get("created_at"))
        if not dt:
            continue
        day_has.add(_kst_day_key(dt))

    streak = 0
    cur = datetime.now(KST).date()
    for _ in range(90):  # 최대 90일만 체크
        key = cur.strftime("%Y-%m-%d")
        if key in day_has:
            streak += 1
            cur = cur - timedelta(days=1)
        else:
            break

    return {
        "today_total": int(today_total),
        "today_correct": int(today_correct),
        "today_wrong": int(today_wrong),
        "accuracy": int(accuracy),
        "top_wrong_mode": str(top_wrong_mode),
        "streak": int(streak),
    }

def render_today_report_db_only(sb_authed, user_id: str):
    """한 방에: fetch -> build -> render (DB only)"""
    try:
        now_kst = datetime.now(KST)
        start_kst = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
        end_kst = start_kst + timedelta(days=1)

        # DB는 UTC timestamptz인 경우가 많으니 UTC로 변환해서 조회
        start_utc = start_kst.astimezone(timezone.utc)
        end_utc = end_kst.astimezone(timezone.utc)

        today_rows = fetch_attempts_between(sb_authed, user_id, start_utc, end_utc)

        # streak 계산용 최근 60일
        recent_start_utc = (start_kst - timedelta(days=60)).astimezone(timezone.utc)
        recent_rows = fetch_attempts_between(sb_authed, user_id, recent_start_utc, end_utc)

        rep = build_today_report_from_rows(today_rows, recent_rows)

        is_pro_user = is_pro()

        if not is_pro_user:
            st.caption("🔒 상세 학습 리포트는 PRO에서 확인할 수 있어요.")

        def mask_value(val, suffix=""):
            if is_pro_user:
                return f"{val}{suffix}"
            return f"<span style='filter: blur(6px); user-select:none;'>{val}</span>{suffix}"               


        total = rep["today_total"]
        acc = rep["accuracy"]
        wrong = rep["today_wrong"]
        streak = rep["streak"]
        top_mode = mode_label(rep["top_wrong_mode"])

        # ✅ 표시용 (PRO 아니면 blur 처리)
        total_display = mask_value(total)
        acc_display = mask_value(acc, "%")
        wrong_display = mask_value(wrong)
        streak_display = mask_value(streak, "일")


        # 오늘 학습 없으면 조용히
        if total <= 0:
            st.caption("오늘의 학습 리포트: 아직 학습 기록이 없어요 🙂")
            return

        st.markdown(
            f"""
<div class="jp" style="
  border:1px solid rgba(120,120,120,0.18);
  border-radius:18px;
  padding:14px 14px;
  background: rgba(255,255,255,0.03);
  margin: 6px 0 10px 0;
">
  <div style="font-weight:900; font-size:14px; opacity:.75;">📈 오늘의 학습 리포트</div>
  <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
    <div style="flex:1 1 120px; min-width:120px;">
      <div style="font-size:12px; opacity:.7; font-weight:800;">오늘 푼 문항</div>
      <div style="font-size:22px; font-weight:900; line-height:1.1;">{mask_value(total)}</div>
    </div>
    <div style="flex:1 1 120px; min-width:120px;">
      <div style="font-size:12px; opacity:.7; font-weight:800;">정답률</div>
      <div style="font-size:22px; font-weight:900; line-height:1.1;">{mask_value(acc, "%")}</div>
    </div>
    <div style="flex:1 1 120px; min-width:120px;">
      <div style="font-size:12px; opacity:.7; font-weight:800;">오늘 오답</div>
      <div style="font-size:22px; font-weight:900; line-height:1.1;">{mask_value(wrong)}</div>
    </div>
    <div style="flex:1 1 160px; min-width:160px;">
      <div style="font-size:12px; opacity:.7; font-weight:800;">연속 학습</div>
      <div style="font-size:22px; font-weight:900; line-height:1.1;">{mask_value(streak, "일")}</div>
    </div>
  </div>
  <div style="margin-top:8px; font-size:12px; opacity:.78; line-height:1.4;">
    오늘 가장 많이 틀린 모드: <b>{html.escape(str(top_mode))}</b>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    except Exception:
        # 리포트가 실패해도 앱이 멈추면 안 됨
        st.caption("오늘 리포트를 불러오지 못했어요.")
# ============================================================
# ✅ App Start: refresh → login → routing
# ============================================================
ok = refresh_session_from_cookie_if_needed(force=False)
if not ok and (cookies.get("refresh_token") or cookies.get("access_token")):
    clear_auth_everywhere()
    st.caption("세션 복원에 실패해서 로그인을 다시 요청합니다.")

require_login()

ALLOWED_PAGES = {"home", "quiz", "my", "admin"}
if "page" not in st.session_state:
    st.session_state.page = "home"
if st.session_state.get("page") not in ALLOWED_PAGES:
    st.session_state.page = "home"

user = st.session_state.get("user")
user_id = getattr(user, "id", None) if user else None
user_email = getattr(user, "email", None) if user else None
user_email = user_email or st.session_state.get("login_email")

sb_authed = get_authed_sb()

# ✅ PRO 캐시가 다른 유저에게 넘어가는 것 방지 (먼저!)
cached_uid = st.session_state.get("plan_cached_user_id")
if cached_uid != user_id:
    st.session_state.pop("plan_cached", None)
    st.session_state["plan_cached_user_id"] = user_id

# ✅ 로그인 유저 + authed 클라 둘 다 있을 때만 리포트 표시
# if sb_authed and user_id:
#    render_today_report_db_only(sb_authed, user_id)

# ✅ pos_group 기반 available_types 적용
try:
    if sb_authed is not None:
        available_types = get_available_quiz_types_for_pos(st.session_state.get("pos_group", "noun"))
    else:
        base_types = QUIZ_TYPES_USER
        g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
        available_types = [t for t in base_types if t in ("meaning", "kr2jp")] if g_now in POS_ONLY_2TYPES else base_types
except Exception:
    g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
    available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER

# ✅ 현재 선택된 유형이 pos_group에서 허용되지 않으면 meaning으로 강제
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

if sb_authed is not None and not st.session_state.get("progress_restored"):
    try:
        restore_progress_from_db(sb_authed, user_id)
    except Exception:
        pass
    st.session_state.progress_restored = True

# ✅ 복원 후에도 pos_group/available_types 재동기화
try:
    available_types = get_available_quiz_types_for_pos(st.session_state.get("pos_group", "noun")) if sb_authed is not None else available_types
except Exception:
    pass
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

if st.session_state.get("page") != "home":
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")
    st.markdown(
        f"""
<div class="jp headbar">
  <div class="headtitle">✨ 왕초보 탈출 하테나일본어</div>
  <div class="headhello">환영합니다 🙂 <span class="mail">{email}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )

if sb_authed is not None:
    ensure_profile(sb_authed, user)
    att = mark_attendance_once(sb_authed)
    if att:
        st.session_state["streak_count"] = int(att.get("streak_count", 0) or 0)
        st.session_state["did_attend_today"] = bool(att.get("did_attend", False))

# ============================================================
# ✅ Routing
# ============================================================
if st.session_state.page == "home":
    render_home()
    st.stop()

if st.session_state.page == "admin":
    if not is_admin():
        st.session_state.page = "quiz"
        st.warning("관리자 권한이 없습니다.")
        st.rerun()
    render_admin_dashboard()
    st.stop()

if st.session_state.page == "my":
    try:
        render_my_dashboard()
    except Exception:
        st.error("마이페이지에서 예외가 발생했습니다. 아래 Traceback을 확인해 주세요.")
        st.code(traceback.format_exc())
    st.stop()

# ============================================================
# ✅ PAYWALL CHECK (render_topcard() 보다 위에서 1번만!)
#   - FREE: 하루 30문항 제한, PRO: 무제한
# ============================================================
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
FREE_LIMIT = 30

def render_paywall(daily_solved: int):
    st.error("🔒 오늘 무료 학습량을 모두 사용하셨어요.")
    st.caption(f"오늘 푼 문항: {daily_solved} / {FREE_LIMIT}")
    st.info("PRO로 업그레이드하면 오늘도 계속 풀 수 있어요.")
    if st.button("💎 PRO 신청/문의", use_container_width=True, key="btn_paywall_go_pro"):
        st.session_state["_scroll_top_once"] = True
        st.markdown(f"<meta http-equiv='refresh' content='0;url={NAVER_TALK_URL}'>", unsafe_allow_html=True)

def get_daily_solved_from_db(sb_authed_local, user_id: str) -> int:
    """오늘(KST) 푼 문항 수 합계 (quiz_attempts.quiz_len 합산)"""
    now = datetime.now(KST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # created_at이 timestamptz라면, KST start를 ISO로 넣어도 대부분 정상 필터됩니다.
    start_iso = start.isoformat()

    res = (
        sb_authed_local.table("quiz_attempts")
        .select("quiz_len")
        .eq("user_id", user_id)
        .gte("created_at", start_iso)
        .execute()
    )
    rows = res.data or []
    return int(sum(int(r.get("quiz_len") or 0) for r in rows))

# ✅ 잠금 판단
is_locked = False
daily_solved = 0

if not is_pro():
    sb_authed_local = get_authed_sb()
    if sb_authed_local is not None:
        daily_solved = get_daily_solved_from_db(sb_authed_local, user_id)
        is_locked = (daily_solved >= FREE_LIMIT)

if is_locked:
    render_paywall(daily_solved)
    st.stop()

# ✅ 오늘 푼 문항 수(total) 정의: 목표 UI/DEBUG에서 공통 사용
total = 0
try:
    sb_authed_local = get_authed_sb()
    if sb_authed_local is not None and user_id:
        total = get_daily_solved_from_db(sb_authed_local, user_id)  # 오늘 푼 문항 수
except Exception:
    total = 0

# ============================================================
# ✅ Quiz Page
# ============================================================
def render_plan_banner():
    plan = get_user_plan()
    if plan == "pro":
        st.success("✨ PRO 이용 중입니다.")
        return

    st.info("🔒 일부 기능은 PRO에서 열립니다. (예: 오답만 다시풀기, 발음 버튼, 패턴카드 확장 등)")
    if st.button("💎 PRO 신청/문의", use_container_width=True, key="btn_go_pro"):
        st.session_state["_scroll_top_once"] = True
        st.markdown(f"<meta http-equiv='refresh' content='0;url={NAVER_TALK_URL}'>", unsafe_allow_html=True)

# ✅ 호출은 정의 아래에서
render_topcard()
render_plan_banner()
render_sound_toggle()

streak = st.session_state.get("streak_count")
did_today = st.session_state.get("did_attend_today")
if streak is not None:
    if did_today:
        st.success(f"✅ 오늘 출석 완료!  (연속 {streak}일)")
    else:
        st.caption(f"연속 출석 {streak}일")
    if streak >= 30:
        st.info("🔥 30일 연속 달성!")
    elif streak >= 7:
        st.info("🏅 7일 연속 달성!")

# --- (A) 기존 "오늘의 목표(루틴)" 섹션 ---
if "today_goal_text" not in st.session_state:
    st.session_state.today_goal_text = "오늘은 10문항 1회 완주"
if "today_goal_done" not in st.session_state:
    st.session_state.today_goal_done = False

# ============================================================
# ✅ [PATCH] 🎯 오늘 목표 자동 연동 + 진행률 도표(프로그레스 바)
# - 목표 1회=10문항, 2회=20문항...
# - today_total(= total) 기준으로 자동 ✅달성/⏳진행중
# - ✅ “오늘 목표” 박스 안에 진행률 도표 + % 표시
# - ✅ 세그먼트 카드/목표 카드 톤(테두리/라운드/그림자) 통일
# ============================================================

st.markdown("""
<style>
/* ✅ goal 세그먼트 전용 앵커 */
#goal_seg_anchor + div[data-testid="stSegmentedControl"]{
  padding: 10px 12px;
  border: 1px solid rgba(49,51,63,.12);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 1px 0 rgba(0,0,0,.02);
  margin-bottom: 10px;
}
#goal_seg_anchor + div[data-testid="stSegmentedControl"] [role="group"]{
  display:flex !important;
  width:100% !important;
  gap: 8px !important;
}
#goal_seg_anchor + div[data-testid="stSegmentedControl"] button{
  flex: 1 1 0 !important;
  min-width: 0 !important;
  text-align: center !important;
  padding: 12px 10px !important;
  font-size: 15px !important;
  border-radius: 12px !important;
  border: 1px solid rgba(49,51,63,.12) !important;
}
#goal_seg_anchor + div[data-testid="stSegmentedControl"] button[aria-pressed="true"]{
  border: 1px solid rgba(255,0,0,.35) !important;
  box-shadow: 0 0 0 2px rgba(255,0,0,.08) inset;
}
</style>
""", unsafe_allow_html=True)

# ✅ 앵커는 segmented_control "바로 직전"에 둬야 함
st.markdown('<div id="goal_seg_anchor"></div>', unsafe_allow_html=True)


# ✅ 1) 목표(세션) 설정값
if "goal_sessions" not in st.session_state:
    st.session_state.goal_sessions = 1  # 기본 1회(=10문항)

target_questions = st.slider(
    "오늘 목표",
    min_value=10, max_value=60, step=10,
    value=st.session_state.get("target_questions", 10),
)
st.session_state["target_questions"] = target_questions


# ✅ 2) 오늘 푼 문항수(기존 total 변수 재사용)
today_total = int(total)  # ← 기존 코드에서 total이 "오늘 푼 문항"이면 그대로 OK

goal_done = today_total >= target_questions
goal_percent = int(min(100, (today_total / max(1, target_questions)) * 100))
remain = max(0, target_questions - today_total)

goal_msg = "오늘 목표 달성! 내일도 루틴 이어가요 🔥" if goal_done else f"남은 문항: {remain}"


# ✅ 3) 자동 목표 UI (진행률 도표 포함)
import streamlit.components.v1 as components

card_html = f"""
<div class="jp" style="
  border:1px solid rgba(49,51,63,.12);
  border-radius:18px;
  padding:14px 14px;
  background:#fff;
  box-shadow: 0 1px 0 rgba(0,0,0,.02);
  margin: 6px 0 10px 0;
  font-family: inherit;
">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="font-weight:900; font-size:14px; opacity:.80;">🎯 오늘 목표</div>
    <div style="font-size:12px; font-weight:900; opacity:.85;">
      {"✅ 달성" if goal_done else "⏳ 진행중"}
    </div>
  </div>

  <div style="margin-top:10px; display:flex; gap:12px; flex-wrap:wrap; align-items:center;">
    <div style="font-size:13px; font-weight:800; opacity:.85;">
      목표: <b>{target_questions}</b>문항
    </div>
    <div style="font-size:13px; font-weight:800; opacity:.85;">
      진행: <b>{today_total}</b> / {target_questions}문항
    </div>
    <div style="font-size:13px; font-weight:900; opacity:.85;">
      {goal_percent}%
    </div>
  </div>

  <div style="margin-top:10px;">
    <div style="height:10px; border-radius:999px; background: rgba(0,0,0,0.07); overflow:hidden;">
      <div style="height:100%; width:{goal_percent}%; background: rgba(0,0,0,0.25);"></div>
    </div>

    <div style="margin-top:10px; font-size:12.5px; opacity:.72; font-weight:700;">
      {goal_msg}
    </div>
  </div>
</div>
"""

# height는 카드 높이에 맞춰 적당히
components.html(card_html, height=140)


st.divider()

# ============================================================
# ✅ 이하: 기존 세션 상태 초기화/shape ensure (그대로 유지)
# ============================================================

if "quiz_version" not in st.session_state:
    st.session_state.quiz_version = 0
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "wrong_list" not in st.session_state:
    st.session_state.wrong_list = []
if "saved_this_attempt" not in st.session_state:
    st.session_state.saved_this_attempt = False
if "stats_saved_this_attempt" not in st.session_state:
    st.session_state.stats_saved_this_attempt = False
if "session_stats_applied_this_attempt" not in st.session_state:
    st.session_state.session_stats_applied_this_attempt = False
if "history" not in st.session_state:
    st.session_state.history = []
if "progress_dirty" not in st.session_state:
    st.session_state.progress_dirty = False
if "wrong_counter" not in st.session_state:
    st.session_state.wrong_counter = {}
if "total_counter" not in st.session_state:
    st.session_state.total_counter = {}

ensure_mastered_words_shape()
ensure_excluded_wrong_words_shape()
ensure_mastery_banner_shape()


# ============================================================
# ✅ 상단 UI: 품사 버튼 → (기타 expander + 적용 버튼) → 유형 버튼 → 캡션 → divider
# ============================================================
def on_pick_pos_group(ps: str):
    ps = str(ps).strip().lower()
    if ps == st.session_state.pos_group:
        return
    st.session_state.pos_group = ps

    # ✅ 제한 그룹이면 reading 선택 상태를 자동 해제
    if ps in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
        st.session_state.quiz_type = "meaning"

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    st.session_state["_scroll_top_once"] = True

def on_pick_qtype(qt: str):
    qt = str(qt).strip()
    if qt == st.session_state.quiz_type:
        return
    st.session_state.quiz_type = qt

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    st.session_state["_scroll_top_once"] = True

# ✅ 현재 pos_group 기준으로 유형 리스트 재계산(표시 직전에!)
try:
    if sb_authed is not None:
        available_types = get_available_quiz_types_for_pos(st.session_state.get("pos_group", "noun"))
    else:
        g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
        available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER
except Exception:
    g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
    available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER

# ✅ 선택된 유형이 현재 pos_group에서 허용되지 않으면 meaning으로 강제
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

st.markdown('<div class="qtypewrap">', unsafe_allow_html=True)

st.markdown('<div class="qtype_hint jp">✨품사를 선택하세요</div>', unsafe_allow_html=True)

# ✅ 품사 그룹 버튼(5개)
pos_cols = st.columns(5, gap="small")
for i, ps in enumerate(POS_GROUP_OPTIONS):
    with pos_cols[i]:
        is_sel = (ps == st.session_state.pos_group)
        st.button(
            ("✅ " if is_sel else "") + POS_LABEL_MAP.get(ps, ps),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_posg_{ps}",
            on_click=on_pick_pos_group,
            args=(ps,),
        )

# ✅ B안: 기타 선택 시에만 세부 선택 expander + 적용 버튼
if st.session_state.pos_group == "other":
    with st.expander("기타 세부 선택 (부사/조사/접속사/감탄사)", expanded=True):
        cols = st.columns(2)
        for j, p in enumerate(OTHER_POS_OPTIONS):
            with cols[j % 2]:
                checked = (p in st.session_state.other_pos_selected)
                new_checked = st.checkbox(OTHER_POS_LABEL_MAP[p], value=checked, key=f"chk_other_{p}")
                if new_checked:
                    st.session_state.other_pos_selected.add(p)
                else:
                    st.session_state.other_pos_selected.discard(p)

        if st.button("🔄 기타 선택 적용(새 문제)", use_container_width=True, key="btn_apply_other"):
            # ✅ 기타는 reading 불가
            if st.session_state.quiz_type == "reading":
                st.session_state.quiz_type = "meaning"

            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

st.markdown('<div class="qtype_hint jp">✨유형을 선택하세요</div>', unsafe_allow_html=True)

# ✅ 유형 버튼
type_cols = st.columns(len(available_types), gap="small")
for i, qt in enumerate(available_types):
    with type_cols[i]:
        is_sel = (qt == st.session_state.quiz_type)
        st.button(
            ("✅ " if is_sel else "") + quiz_label_map.get(qt, qt),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_qtype_{qt}",
            on_click=on_pick_qtype,
            args=(qt,),
        )

st.markdown("</div>", unsafe_allow_html=True)

# ✅ 필수패턴(카드)
with st.expander("📌 필수패턴 (카드로 빠르게 익히기)", expanded=False):
    if is_pro():
        render_pattern_cards()
    else:
        st.caption("🔒 PRO에서 품사별 패턴 카드 전체가 열립니다.")
        # 무료 체험: 1장만
        render_pattern_cards()

st.markdown('<div class="tight-divider">', unsafe_allow_html=True)
st.divider()
st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# ✅ FREE 사용량 기록 (현재는 제한 OFF라 no-op)
# ============================================================
def add_free_used(n: int):
    """FREE 제한을 다시 켤 때를 대비해 남겨둠. 현재는 아무 것도 하지 않음."""
    return

# ============================================================
# ✅ 버튼: 새 문제(랜덤10) / 맞힌 단어 제외 초기화  (복붙 버전)
#   - 기존 "쓸데없는 새 문제" 버튼 제거
#   - "🔄 새 문제(랜덤 10문항)"을 왼쪽(원래 자리)로 이동
# ============================================================

def should_lock_quiz() -> bool:
    if is_pro():
        return False
    return False  # FREE 제한 없앴으면 잠금 없음

locked = should_lock_quiz()

cbtn1, cbtn2 = st.columns(2)

with cbtn1:
    if st.button(
        "🔄 새 문제(랜덤 10문항)",
        use_container_width=True,
        key="btn_new_random_10",
        disabled=locked
    ):
        clear_question_widget_keys()
    
        # ✅ 새 퀴즈 시작 = 제출 카운트 플래그 리셋
        st.session_state["_counted_today"] = False

        # ✅ 콤보 알림 단계 리셋(오늘 최고 콤보 기록은 유지)
        st.session_state["combo_last_notice"] = 0
    
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
        mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
        st.session_state["_scroll_top_once"] = True
        st.rerun()
        

def reset_mastery_current():
    k = mastery_key()
    st.session_state.setdefault("seen_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("mastered_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("excluded_wrong_words", {}).setdefault(k, set()).clear()
    st.session_state.setdefault("mastery_done", {})[k] = False
    st.session_state.setdefault("mastery_banner_shown", {})[k] = False

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    st.session_state["_scroll_top_once"] = True
    st.rerun()

with cbtn2:
    if st.button("맞힌 단어 제외 초기화", disabled=locked, use_container_width=True, key="btn_reset_mastery"):
        reset_mastery_current()


    # locked가 항상 False라면 이 캡션은 사실상 안 뜸(있어도 무방)
    if locked:
        st.caption("🔒 무료는 하루 30문항(3세트)까지입니다. PRO로 업그레이드하면 계속 풀 수 있어요.")

k_now = mastery_key()
if st.session_state.get("mastery_done", {}).get(k_now, False):
    st.success("🏆 이 품사/유형을 완전히 정복했어요!")

    
# ============================================================
# ✅ 퀴즈 생성(없으면 1회 자동 생성)
# ============================================================

k_now = mastery_key()  # ✅ 먼저!

if "quiz" not in st.session_state or not isinstance(st.session_state.quiz, list):
    st.session_state.quiz = []

is_mastered_done = bool(st.session_state.get("mastery_done", {}).get(k_now, False))

if (not is_mastered_done) and len(st.session_state.quiz) == 0:
    if is_locked:
        render_paywall(daily_solved)
        st.stop()

    clear_question_widget_keys()
    new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group) or []
    start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
    mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)

if len(st.session_state.quiz) == 0:
    if bool(st.session_state.get("mastery_done", {}).get(k_now, False)):
        st.success("✅ 이 설정에서 새로 출제할 문제가 더 이상 없습니다.")
        st.caption("👉 ‘출제 이력 초기화(다시 시작)’를 누르거나, 다른 품사·유형을 선택해 주세요.")
        st.caption("👉 틀린 문제는 마이페이지에서 ‘틀린 문제만 다시 풀기’로 복습하세요~")
        st.stop()

    st.info("현재는 이 설정으로 낼 문제가 없어요. 다른 품사/유형으로 바꿔서 시작해 주세요.")
    st.stop()

quiz_len = len(st.session_state.quiz)
if "answers" not in st.session_state or not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != quiz_len:
    st.session_state.answers = [None] * quiz_len

if bool(st.session_state.get("mastery_done", {}).get(k_now, False)):
    st.stop()


def _esc_html(x) -> str:
    x = "" if x is None else str(x)
    return (x.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;"))


# ============================================================
# ✅ 오늘 목표(Progress) - 세션 기반 (DB 없이)
#   - 상단(1곳)만 사용
#   - 하단은 SHOW_BOTTOM_GOAL=False면 절대 렌더링 안 됨
# ============================================================

SHOW_BOTTOM_GOAL = False  # ✅ 하단을 완전히 숨기려면 False 유지

def get_today_done_count() -> int:
    return int(st.session_state.get("today_done", 0))

def add_done_count(n: int):
    st.session_state["today_done"] = get_today_done_count() + int(n)

def reset_today_done():
    st.session_state["today_done"] = 0

def get_today_goal_default() -> int:
    return 10

# ✅ 누적용 상태(필요하면 유지)
if "counted_qids" not in st.session_state:
    st.session_state["counted_qids"] = set()
if "is_graded" not in st.session_state:
    st.session_state["is_graded"] = False

def render_today_goal_progress():
    st.markdown("### 🎯 오늘 목표 진행률")

    goal = int(st.session_state.get("today_goal", get_today_goal_default()))
    done = get_today_done_count()

    ratio = 0.0 if goal <= 0 else min(max(done / goal, 0.0), 1.0)

    st.progress(ratio)
    st.caption(f"진행: **{done} / {goal}문항** ({int(ratio*100)}%)")

    if done >= goal and goal > 0:
        st.success("🔥 오늘 목표 달성!")

    if st.button("🔁 오늘 목표 리셋", use_container_width=True, key="btn_reset_today_goal"):
        reset_today_done()
        st.rerun()

    st.divider()

# ============================================================
# ✅ 하단 렌더링(숨김)
#   - 아래 조건부 블록만 남기고, "직접 호출"은 절대 하지 마세요.
# ============================================================

if SHOW_BOTTOM_GOAL:
    render_today_goal_progress()


# ============================================================
# ✅ 문제 표시 (동그란 배지: ① ② ③ ... + 같은 줄)
# ============================================================
circled_nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"

for idx, q in enumerate(st.session_state.quiz):
    badge = circled_nums[idx] if idx < len(circled_nums) else f"({idx+1})"

    st.markdown(
        f"""
<div class="jp" style="display:flex; align-items:baseline; gap:5px; margin: 10px 0 8px 0;">
  <div style="
    flex:0 0 auto;
    font-size:20px;
    line-height:1;
    font-weight:900;
    transform: translateY(1px);
  ">{badge}</div>

  <div style="
    flex:1 1 auto;
    font-size:18px;
    font-weight:500;
    line-height:1.35;
  ">{q["prompt"]}</div>
</div>
""",
        unsafe_allow_html=True
    )

    if st.session_state.get("quiz_type") == "meaning":
        tts_text = (q.get("reading") or q.get("jp_word") or "").strip()

        # ✅ PRO만 버튼 렌더링 (무료는 루프 안에서 아무것도 안 찍음)
        if is_pro():
            render_pronounce_button(
                tts_text,
                uid=f"{st.session_state.quiz_version}_{idx}",
                label="🔊 발음"
            )

    widget_key = f"q_{st.session_state.quiz_version}_{idx}"

    prev = st.session_state.answers[idx]
    default_index = None
    if prev is not None and prev in q["choices"]:
        default_index = q["choices"].index(prev)

    choice = st.radio(
        label="보기",
        options=q["choices"],
        index=default_index,
        key=widget_key,
        label_visibility="collapsed",
        on_change=mark_progress_dirty,
    )
    st.session_state.answers[idx] = choice

sync_answers_from_widgets()


# ============================================================
# ✅ 제출/채점
# ============================================================
quiz_len = len(st.session_state.quiz)

# ✅ "지금 선택된 값"을 세션에서 읽어서 all_answered 판단
selected_now = []
for idx, q in enumerate(st.session_state.quiz):
    widget_key = f"q_{st.session_state.quiz_version}_{idx}"
    selected_now.append(st.session_state.get(widget_key, None))

all_answered = (quiz_len > 0) and all(a is not None for a in selected_now)

if st.button(
    "✅ 제출하고 채점하기",
    disabled=not all_answered,
    type="primary",
    use_container_width=True,
    key="btn_submit",
):
    st.session_state.submitted = True
    st.session_state.session_stats_applied_this_attempt = False

    # ✅ 제출 시점에만 answers에 확정 반영
    st.session_state.answers = selected_now

    # ✅ 중복 카운트 방지
    if not st.session_state.get("_counted_today", False):
        add_done_count(int(st.session_state.get("quiz_len", 10)))
        st.session_state["_counted_today"] = True

if not all_answered:
    st.info("모든 문제에 답을 선택하면 제출 버튼이 활성화됩니다.")


# ============================================================
# ✅ 제출 후 화면
# ============================================================
if st.session_state.submitted:
    show_post_ui = (SHOW_POST_SUBMIT_UI == "Y") or is_admin()

    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()

    current_type = st.session_state.quiz_type
    current_pos_group = st.session_state.pos_group
    k_now = mastery_key()

    score = 0
    wrong_list = []

    for idx, q in enumerate(st.session_state.quiz):
        picked = st.session_state.answers[idx]
        correct = q["correct_text"]
        word_key = str(q.get("jp_word", "")).strip()

        if picked == correct:
            score += 1
            if word_key:
                st.session_state.mastered_words.setdefault(k_now, set()).add(word_key)
        else:
            wrong_list.append({
                "No": idx + 1,
                "문제": str(q.get("prompt", "")),
                "내 답": "" if picked is None else str(picked),
                "정답": str(correct),
                "단어": str(q.get("jp_word", "")).strip(),
                "읽기": str(q.get("reading", "")).strip(),
                "뜻": str(q.get("meaning", "")).strip(),
                "품사": current_pos_group,   # ✅ 그룹 저장
                "유형": current_type,
            })

    st.session_state.wrong_list = wrong_list

    st.success(f"점수: {score} / {quiz_len}")

    # ✅ FREE 제한 카운트 누적 (제출 1회 = quiz_len 소비)
    #    같은 제출 화면에서 rerun이 여러 번 나도 중복 누적되지 않도록 1회만 적용
    if "free_limit_applied_this_attempt" not in st.session_state:
        st.session_state.free_limit_applied_this_attempt = False

    if not st.session_state.free_limit_applied_this_attempt:
        add_free_used(quiz_len)  # 보통 10
        st.session_state.free_limit_applied_this_attempt = True

    ratio = score / quiz_len if quiz_len else 0

    if ratio == 1:
        sfx("perfect")
    elif ratio >= 0.7:
        sfx("wrong")
    else:
        sfx("wrong")

    if ratio == 1:
        st.balloons()
        st.success("🎉 완벽해요! 전부 정답입니다.")
    elif ratio >= 0.7:
        st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
    else:
        st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")

    sb_authed_local = get_authed_sb()
    if sb_authed_local is None:
        if show_post_ui:
            st.warning("DB 저장/조회용 토큰이 없습니다. 다시 로그인해 주세요.")
    else:
        if not st.session_state.saved_this_attempt:
            try:
                run_db(lambda: save_attempt_to_db(
                    sb_authed=sb_authed_local,
                    user_id=user_id,
                    user_email=user_email,
                    pos=current_pos_group,   # ✅ 그룹 저장
                    quiz_type=current_type,
                    quiz_len=quiz_len,
                    score=score,
                    wrong_list=wrong_list,
                ))
                st.session_state.saved_this_attempt = True
            except Exception as e:
                if show_post_ui:
                    st.warning("DB 저장에 실패했습니다. (테이블/컬럼/권한/RLS 정책 확인 필요)")
                    st.write(str(e))

        if not st.session_state.stats_saved_this_attempt:
            try:
                sync_answers_from_widgets()
                items = build_word_results_bulk_payload(
                    quiz=st.session_state.quiz,
                    answers=st.session_state.answers,
                    quiz_type=current_type,
                    pos=current_pos_group,  # ✅ 그룹 기준
                )
                if items:
                    run_db(lambda: sb_authed_local.rpc("record_word_results_bulk", {"p_items": items}).execute())
                st.session_state.stats_saved_this_attempt = True
            except Exception as e:
                if show_post_ui and is_admin():
                    st.error("❌ 단어 통계(bulk) 저장 실패 (RPC/정책 확인)")
                    st.exception(e)

        try:
            save_progress_to_db(sb_authed_local, user_id)
        except Exception:
            pass

    # ============================================================
    # ✅ 콤보 계산 (⚠️ 반드시 제출 후에만)
    # ============================================================
    correct_flags = []
    for idx, q in enumerate(st.session_state.quiz):
        picked = st.session_state.answers[idx]
        correct = q["correct_text"]
        correct_flags.append(picked == correct)

    max_combo = compute_max_combo(correct_flags)
    render_combo_celebration(max_combo)
    render_combo_small_badge()

    # ============================================================
    # ✅ 제출 후 화면 내부 "오답노트" 블록
    # ============================================================
    if st.session_state.wrong_list:
        st.subheader("❌ 오답 노트")

    def _s(v):
        return "" if v is None else str(v)

    def _esc(x: str) -> str:
        x = _s(x)
        return (x.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&#39;"))

    STYLE = """
<style>
.wrong-card{
  border: 1px solid rgba(120,120,120,0.25);
  border-radius: 16px;
  padding: 14px 14px;
  margin-bottom: 10px;
  background: rgba(255,255,255,0.02);
}
.wrong-top{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  margin-bottom: 8px;
}
.wrong-left{ min-width:0; }
.wrong-title{
  font-weight: 900;
  font-size: 15px;
  margin-bottom: 4px;
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.wrong-sub{
  opacity: 0.8;
  font-size: 12px;
}
.tag{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(120,120,120,0.25);
  background: rgba(255,255,255,0.03);
  white-space: nowrap;
}
.ans-row{
  display:grid;
  grid-template-columns: 72px 1fr;
  gap:10px;
  margin-top:6px;
  font-size: 13px;
}
.ans-k{ opacity: 0.7; font-weight: 700; }
</style>
"""

    cards = []
    for w in st.session_state.wrong_list:
        no = _s(w.get("No"))
        qtext = _s(w.get("문제"))
        picked = _s(w.get("내 답"))
        correct = _s(w.get("정답"))
        word = _s(w.get("단어"))
        reading = _s(w.get("읽기"))
        meaning = _s(w.get("뜻"))
        mode = quiz_label_map.get(w.get("유형"), _s(w.get("유형")))
        pos_label = POS_LABEL_MAP.get(w.get("품사"), _s(w.get("품사")))

        card_html = f"""
<div class="jp">
  <div class="wrong-card">
    <div class="wrong-top">
      <div class="wrong-left">
        <div class="wrong-title">Q{_esc(no)}. {_esc(word)}</div>
        <div class="wrong-sub">{_esc(qtext)} · 품사: {_esc(pos_label)} · 유형: {_esc(mode)}</div>
      </div>
      <div class="tag">오답</div>
    </div>

    <div class="ans-row"><div class="ans-k">내 답</div><div>{_esc(picked)}</div></div>
    <div class="ans-row"><div class="ans-k">정답</div><div><b>{_esc(correct)}</b></div></div>
    <div class="ans-row"><div class="ans-k">발음</div><div>{_esc(reading)}</div></div>
    <div class="ans-row"><div class="ans-k">뜻</div><div>{_esc(meaning)}</div></div>
  </div>
</div>
"""
        cards.append(card_html)

    def _render_cards(card_list: list[str], max_height: int = 650):
        if not card_list:
            return
        html_block = "".join(card_list)
        h = 190 * len(card_list) + 10
        h = max(190, min(h, max_height))

        components.html(
            textwrap.dedent(f"""
{STYLE}
{html_block}
"""),
            height=h,
        )

    MAX_PREVIEW = 3
    preview_cards = cards[:MAX_PREVIEW]
    rest_cards = cards[MAX_PREVIEW:]

    _render_cards(preview_cards, max_height=650)

    if rest_cards:
        with st.expander(f"오답 더 보기 (+{len(rest_cards)}개)", expanded=False):
            _render_cards(rest_cards, max_height=900)
            

# ============================================================
# ✅ 제출 후 하단 액션 버튼 (오답 유무와 무관하게 항상 표시)
# ============================================================
if st.session_state.get("submitted", False):
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cA, cB = st.columns(2)
    with cA:
        locked = free_limit_reached()

        if locked:
            st.caption("🔒 오늘 무료 한도(30문항)를 모두 사용했어요.")

        if st.button(
            "✅ 다음 10문항 시작하기",
            type="primary",
            use_container_width=True,
            key="btn_next_10",
            disabled=locked
        ):
            if locked:
                st.stop()

            clear_question_widget_keys()

            st.session_state["_counted_today"] = False
            
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state.free_limit_applied_this_attempt = False
            mark_quiz_as_seen(new_quiz, st.session_state.quiz_type, st.session_state.pos_group)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    with cB:
        # 오답이 있을 때만 활성화(없으면 disabled)
        has_wrongs = bool(st.session_state.get("wrong_list"))
        pro_only_disabled = (not is_pro()) or (not has_wrongs)
        if st.button(
            "❌ 틀린 문제만 다시 풀기",
            use_container_width=True,
            disabled=pro_only_disabled,
            key="btn_retry_wrongs_bottom_global"
        ):
            clear_question_widget_keys()
            retry_quiz = build_quiz_from_wrongs(
                st.session_state.wrong_list,
                st.session_state.quiz_type,
                st.session_state.pos_group
            )
            start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

    show_naver_talk = (SHOW_NAVER_TALK == "N") or is_admin()
    if show_naver_talk:
        render_naver_talk()



