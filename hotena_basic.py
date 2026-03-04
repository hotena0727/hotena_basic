from __future__ import annotations
# ============================================================
# OK 왕초보 탈출 하테나일본어 (단어 앱) - 전체 복붙용 단일 파일
# - 품사 선택 + 유형 선택(발음/뜻/한→일)
# - 로그인/회원가입(Supabase Auth) + 쿠키 세션 복원
# - 홈/퀴즈/마이페이지/관리자 라우팅
# - 오답노트 + 오답만 다시풀기
# - 맞힌 단어 제외(정복) + 초기화
# - 사운드 토글 + 테스트 재생 + 제출 후 1회 SFX
#
# OK CSV (data/.csv) 필수 컬럼(최종):
#   level, pos, jp_word, reading, meaning, example_jp, example_kr
#   - 문제는 jp_word(한자 포함 단어)에서 뽑음
#ㅜㅁ
# OK 이번 수정 반영:
#   1) 발음(読み) 문제에서 "보기 모양"으로 찍기 방지:
#      - verb: 가능한 한 '끝 2글자(히라가나 기준)' 동일 → 부족하면 '끝 1글자' 동일
#      - verb: する 동사는 보기 4개 모두 '～する'로 통일
#      - adj_i: 보기 전부 끝이 'い'로 통일(동일 pos 풀에서)
#      - adj_na: pos가 동일하므로 기본적으로 모양 찍기 난이도 상승(동사처럼 suffix 적용은 X)
#   2) 제출 후 SFX: perfect / (0.7 이상) correct / (그 외) wrong
#   3) OK B안 반영:
#      - 상단 품사 버튼: noun/verb/adj_i/adj_na/other(기타)
#      - 기타 선택 시: 부사/조사/접속사/감탄사 체크박스(expander) + "적용(새 문제)" 버튼
#      - 기타에서는 유형을 "뜻, 한→일" 2개만 노출 (발음 숨김)
#   4) OK 필수패턴: "퀴즈"가 아니라 "카드"로(품사 그룹별) expander 제공
# ============================================================


from pathlib import Path
import random
import pandas as pd
import streamlit as st


import core
# ============================================================
# OK wrong_notes debug helper
# ============================================================
_WN_DEBUG = bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))
def _wn_warn(msg: str):
    if _WN_DEBUG:
        try:
            st.warning(msg)
        except Exception:
            pass
# OK HUB에서 호출되면 상단 중복 UI를 숨기기 위한 플래그
HUB_MODE = st.session_state.get('HUB_MODE', False)
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

# ============================================================
# OK Page Config + Paths
# ============================================================
st.session_state.pop("plan_cached", None)

if not st.session_state.get('_page_config_set'):
    st.set_page_config(
    page_title="단어",
    page_icon="icon-192.png",   # 또는 "🟦"
    layout="centered",
)

# ✅ PWA/A2HS 공통 주입 (루트: /manifest.json, /sw.js, /apple-touch-icon.png, /icon-192.png, /icon-512.png)
core.inject_pwa_once(app_name="Hotena", theme_color="#0F6B3F")

# HN_RADIO_COMPACT_V4
try:
    _hn_css = "/* ===========================\n   HN RADIO COMPACT (v4)\n   \ubaa9\ud45c: \"\uc120\ud0dd \ud6c4\"\uc758 \ucd18\ucd18\ud55c \ub290\ub08c\uc744 \uae30\ubcf8\uac12\uc73c\ub85c \uace0\uc815\n   - Streamlit \uae30\ubcf8 \ud3f0\ud2b8/\uc0c9\uc0c1 \uc720\uc9c0\n   - \uc120\ud0dd \uc804/\ud6c4 \uac04\uaca9 \ub3d9\uc77c\n   =========================== */\ndiv[data-testid=\"stRadio\"] div[role=\"radiogroup\"]{\n  gap: 0px !important;\n}\n\n/* \uac01 \ubcf4\uae30(\ub77c\ub514\uc624 1\uac1c)\uc758 \uae30\ubcf8 \uac04\uaca9\uc744 '\ucd18\ucd18\ud558\uac8c' */\ndiv[data-testid=\"stRadio\"] div[data-baseweb=\"radio\"]{\n  margin: 0 0 0.28rem 0 !important;   /* \u2705 \uae30\ubcf8 \uac04\uaca9\uc744 \uc120\ud0dd \ud6c4 \ub290\ub08c\uc73c\ub85c */\n  padding: 0 !important;\n}\n\n/* \ub0b4\ubd80 \ub798\ud37c \uc5ec\ubc31 \uc81c\uac70(\ube0c\ub77c\uc6b0\uc800/\uc120\ud0dd\uc0c1\ud0dc\uc5d0 \ub530\ub978 \ud754\ub4e4\ub9bc \ubc29\uc9c0) */\ndiv[data-testid=\"stRadio\"] div[data-baseweb=\"radio\"] > div{\n  padding: 0 !important;\n}\n\n/* \uae00\uc904 \ub192\uc774\ub3c4 \uc0b4\uc9dd \ucef4\ud329\ud2b8\ud558\uac8c(\uc120\ud0dd \uc804/\ud6c4 \ub3d9\uc77c) */\ndiv[data-testid=\"stRadio\"] label,\ndiv[data-testid=\"stRadio\"] span{\n  font-weight: inherit !important;\n  line-height: 1.32 !important;\n}"
    _hn_html = (
        "<script>(function(){try{"
        "var doc=(window.parent&&window.parent.document)?window.parent.document:document;"
        "var ID='hn_radio_compact_v4';"
        "var style=doc.getElementById(ID);"
        "if(!style){style=doc.createElement('style');style.id=ID;doc.head.appendChild(style);}"
        "style.textContent=" + JSON.stringify(_hn_css) + ";"
        "}catch(e){}})();</script>"
    )
    components.html(_hn_html, height=0)
except Exception:
    # fallback (iframe 내부)
    st.markdown("""<style>
/* ===========================
   HN RADIO COMPACT (v4)
   목표: "선택 후"의 촘촘한 느낌을 기본값으로 고정
   - Streamlit 기본 폰트/색상 유지
   - 선택 전/후 간격 동일
   =========================== */
div[data-testid="stRadio"] div[role="radiogroup"]{
  gap: 0px !important;
}

/* 각 보기(라디오 1개)의 기본 간격을 '촘촘하게' */
div[data-testid="stRadio"] div[data-baseweb="radio"]{
  margin: 0 0 0.28rem 0 !important;   /* ✅ 기본 간격을 선택 후 느낌으로 */
  padding: 0 !important;
}

/* 내부 래퍼 여백 제거(브라우저/선택상태에 따른 흔들림 방지) */
div[data-testid="stRadio"] div[data-baseweb="radio"] > div{
  padding: 0 !important;
}

/* 글줄 높이도 살짝 컴팩트하게(선택 전/후 동일) */
div[data-testid="stRadio"] label,
div[data-testid="stRadio"] span{
  font-weight: inherit !important;
  line-height: 1.32 !important;
}
    </style>""", unsafe_allow_html=True)

st.session_state['_page_config_set'] = True
# ============================================================
# OK [HOTFIX] Disable onboarding ("60초 이용안내") block entirely
# - In case any legacy UI is still rendered, forcibly hide/remove it.
# ============================================================
try:
    components.html(
        """
<script>
(function(){
  const kill = () => {
    const needles = ["60초 이용안내", "처음 오셨나요"];
    // expander renders as <details><summary>...</summary>...
    document.querySelectorAll("details").forEach(d => {
      const s = d.querySelector("summary");
      const t = (s ? s.innerText : d.innerText) || "";
      if (needles.some(n => t.includes(n))) { d.remove(); }
    });
    // also remove any plain text blocks
    document.querySelectorAll("*").forEach(el => {
      if (el && el.childNodes && el.childNodes.length===1 && el.childNodes[0].nodeType===3) {
        const t = el.innerText || "";
        if (needles.some(n => t.includes(n))) { el.remove(); }
      }
    });
  };
  window.setTimeout(kill, 50);
  window.setTimeout(kill, 500);
})();
</script>
""",
        height=0,
    )
except Exception:
    pass





BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "beginner.csv"   # OK 왕초보 단어 CSV
PATTERN_CSV_PATH = BASE_DIR / "data" / "patterns_beginner.csv"
APP_URL = "https://hotena-basic-925102605904.asia-northeast3.run.app/"      # OK 이메일 인증 redirect용 (스트림릿 앱 주소로 교체)

# ============================================================
# OK App Settings
# ============================================================
SHOW_POST_SUBMIT_UI = "N"  # 제출 후 '내 최근 기록' 등을 퀴즈 페이지에 바로 보여줄지
SHOW_NAVER_TALK = "Y"
NAVER_TALK_URL = "https://talk.naver.com/W45141"

KST_TZ = "Asia/Seoul"
N = 10  # 한 번에 10문항

# ============================================================
# OK POS / QUIZ TYPES  (OK B안: pos_group + other 세부 선택)
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

# OK 요청 반영: 기타(adv/particle/conj/interj)에서는 발음(reading) 숨김 → 그룹 단위로 other만 제한
POS_ONLY_2TYPES = {"other"}

# ============================================================
# OK 필수패턴(카드) - 최소 샘플(원하면 나중에 확장)
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
# OK Session Defaults  (OK pos → pos_group / 기타 체크 세트)
# ============================================================
if "quiz_type" not in st.session_state:
    st.session_state.quiz_type = "meaning"  # 왕초보는 뜻부터 추천
if "pos_group" not in st.session_state:
    st.session_state.pos_group = "noun"

if "other_pos_selected" not in st.session_state:
    # OK 처음엔 기타 전체 체크
    st.session_state.other_pos_selected = set(["adv", "particle", "conj", "interj"])

if st.session_state.quiz_type not in QUIZ_TYPES_USER:
    st.session_state.quiz_type = "meaning"
if st.session_state.pos_group not in POS_GROUP_OPTIONS:
    st.session_state.pos_group = "noun"

# OK (안전) 제한 그룹인데 reading이 잡혀 있으면 meaning으로 강제
if str(st.session_state.get("pos_group", "noun")).lower().strip() in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
    st.session_state.quiz_type = "meaning"

# ============================================================
# OK CSS (폰트/버튼/카드/간격)
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
# OK Scroll Top Anchor + Helpers
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
if not st.session_state.get("HUB_MODE", False):
    if not st.session_state.get("_fab_top_injected", False):
        render_floating_scroll_top()
        st.session_state["_fab_top_injected"] = True
if st.session_state.get("_scroll_top_once"):
    st.session_state["_scroll_top_once"] = False
    st.session_state["_scroll_top_nonce"] = st.session_state.get("_scroll_top_nonce", 0) + 1
    scroll_to_top(nonce=st.session_state["_scroll_top_nonce"])

# ============================================================
# OK Cookies + Supabase (Cloud Run env + Streamlit secrets 겸용)
# ============================================================
import os
import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
from supabase import create_client

def get_cfg(key: str) -> str:
    # 0) Hub(home.py)에서 주입된 설정 우선
    try:
        cfg = st.session_state.get("cfg", {}) or {}
        if key in cfg and cfg[key]:
            return str(cfg[key])
    except Exception:
        pass
    # 1) Cloud Run: 환경변수 우선
    v = os.getenv(key)
    if v:
        return v
    # 2) Streamlit Cloud: secrets
    try:
        return st.secrets[key]
    except Exception:
        return 

COOKIE_PASSWORD = get_cfg("COOKIE_PASSWORD")
SUPABASE_URL = get_cfg("SUPABASE_URL")
SUPABASE_ANON_KEY = get_cfg("SUPABASE_ANON_KEY")

# OK 필수값 체크
missing = [k for k, v in {
    "COOKIE_PASSWORD": COOKIE_PASSWORD,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
}.items() if not v]

if missing:
    st.error(f"설정값이 없습니다: {', '.join(missing)} (Cloud Run env 또는 Streamlit secrets 확인)")
    st.stop()

# OK cookies/supabase는 Hub(home.py)에서 1회 생성 후 공유합니다.
cookies = st.session_state.get("cookies")
sb = st.session_state.get("sb")

if cookies is None:
    cookies = EncryptedCookieManager(
        prefix="hotena_beginner_",
        password=COOKIE_PASSWORD,
    )
    if not cookies.ready():
        st.info("잠깐만요! 곧 시작할게요🙂")
        st.stop()
    st.session_state["cookies"] = cookies

if sb is None:
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    st.session_state["sb"] = sb

# ============================================================
# OK Utils: 위젯 잔상(q_...) 제거
# ============================================================
def clear_question_widget_keys():
    keys_to_del = [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith("q_")]
    for k in keys_to_del:
        st.session_state.pop(k, None)

        
# ============================================================
# OK FREE 관련 공통 유틸 (현재 제한 OFF 모드)
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
# OK COMBO 시스템 (연속 정답)
# - 제출 시 10문항 기준으로 "최대 연속 정답" 계산
# - 5 콤보: 🔥 / 10 콤보: 🎉 Perfect Streak
# ============================================================

def ensure_combo_state():
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
# OK POS filters (OK B안 핵심)
# ============================================================
def get_pos_filters() -> list[str]:
    g = str(st.session_state.get("pos_group", "noun")).strip().lower()
    if g == "other":
        sel = st.session_state.get("other_pos_selected", set())
        sel = [x for x in OTHER_POS_OPTIONS if x in sel]
        return sel if sel else list(OTHER_POS_OPTIONS)
    return [g]

# ============================================================
# OK Key helpers (정복/제외/배너)
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

    # OK 여기: fetch 함수가 없으면 False로
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
# OK Answers 동기화 + Progress save helper
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
    
    # OK 추가: 새 회차 시작 시 콤보 알림 단계 초기화
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
# OK Auth helpers (JWT refresh, sb authed)
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
# OK DB functions (기존 테이블 구조 그대로 활용)
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
        "level": str(pos),          # OK level 컬럼에 pos_group 저장
        "pos_mode": str(quiz_type), # OK pos_mode 컬럼에 유형 저장
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
    # OK 단일 기준: profiles.plan == "pro"
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
                "pos": str(pos),            # OK pos_group 저장(통계에서는 그룹 기준)
                "quiz_type": str(quiz_type),
                "is_correct": bool(is_correct),
            }
        )
    return items

# ============================================================
# OK Progress (DB 저장/복원)  (OK pos_group + 기타 체크 저장)
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

    # OK 구버전(progress에 pos가 있던 경우)도 최대한 흡수
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

    # OK 제한 그룹이면 reading 복원되더라도 meaning으로 강제
    if str(st.session_state.get("pos_group", "noun")).lower().strip() in POS_ONLY_2TYPES and st.session_state.quiz_type == "reading":
        st.session_state.quiz_type = "meaning"

    if isinstance(st.session_state.quiz, list):
        qlen = len(st.session_state.quiz)
        if not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != qlen:
            st.session_state.answers = [None] * qlen

# ============================================================
# OK Admin
# ============================================================
def get_available_quiz_types() -> list[str]:
    return QUIZ_TYPES_ADMIN if is_admin() else QUIZ_TYPES_USER

# OK (신규) pos_group에 따라 가능한 유형 필터
def get_available_quiz_types_for_pos(pos_group: str) -> list[str]:
    pos_group = str(pos_group).strip().lower()
    base = get_available_quiz_types()
    if pos_group in POS_ONLY_2TYPES:
        return [t for t in base if t in ("meaning", "kr2jp")]
    return base

# ============================================================
# ✅ SFX (효과음) — 중앙 통제: core.py
# - 토글: st.session_state.sfx_enabled (기본 ON)
# - 재생: core.play_sfx("correct"|"wrong"|"reward"|"click")
# - 제출 후 1회: core.play_sfx_once(key, name)
# ============================================================

def render_sound_toggle():
    # Hub mode: sound toggle is rendered in home.py (plan pill)
    if st.session_state.get("HUB_MODE", False):
        return

    # 기존 호환: sound_enabled 유지(다른 코드가 참조할 수 있음)
    if "sound_enabled" not in st.session_state:
        st.session_state.sound_enabled = core.is_sfx_enabled(True)

    c1, c2, c3 = st.columns([1.4, 4.6, 4.0], vertical_alignment="center")
    with c1:
        v = st.toggle("🔊", value=bool(st.session_state.sound_enabled), label_visibility="collapsed")
        st.session_state.sound_enabled = bool(v)
        core.set_sfx_enabled(bool(v))
    with c2:
        st.caption("소리 " + ("ON" if core.is_sfx_enabled(True) else "OFF"))
    with c3:
        if core.is_sfx_enabled(True):
            if st.button("🔈 테스트", use_container_width=True, key="btn_sound_test"):
                core.play_sfx("click")

def sfx(event: str):
    """Backward-compat wrapper (perfect/correct/wrong)."""
    mp = {"perfect": "reward", "correct": "correct", "wrong": "wrong"}
    core.play_sfx(mp.get(str(event).strip().lower(), "click"))

# ============================================================
# OK TTS (브라우저 Web Speech API) - 일본어 발음 버튼용
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

    // OK 일본어 보이스만 추림
    const ja = vs.filter(v => String(v.lang || "").toLowerCase().startsWith("ja"));
    if (!ja.length) return null;

    // OK "여성"로 추정되는 이름/키워드 우선 (환경별로 다름)
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

      // OK “여성 느낌” 쪽으로 살짝 보정 (너무 올리면 부자연스러울 수 있어요)
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
# OK Login UI
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
      ✨ 단어
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

# ============================================================
# OK 네이버톡 배너 (제출 후만)
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
# OK Top Card (마이페이지/관리자/로그아웃)
# ============================================================

def nav_to(page: str, scroll_top: bool = True):
    st.session_state.page = page
    if scroll_top:
        st.session_state["_scroll_top_once"] = True

def nav_logout():
    clear_auth_everywhere()

def render_topcard():
    # HUB에서는 상단 메뉴를 home.py가 책임집니다.
    if st.session_state.get("HUB_MODE"):
        return

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
# OK CSV Load Pool  (OK CSV 최종 스펙 반영)
# ============================================================
READ_KW = dict(
    dtype=str,
    keep_default_na=False,
    na_values=["nan", "NaN", "NULL", "null", "None", "none"],
)

@st.cache_data(show_spinner=False)
def load_pool(csv_path_str: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path_str, **READ_KW)

    # OK CSV 최종 필수 컬럼
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
# OK Quiz Logic
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

    # OK 같은 실제 pos 풀
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
    # OK 안전장치: 제한 그룹에서는 reading 강제 금지
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

    # OK 발음(reading) 문제: jp_word에 한자가 없는(히라가나만 등) 단어는 제외
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
        blocked |= set(seen)          # OK 한 번이라도 출제된 건 전부 제외
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
# OK Quiz builders for review (TOP10 / wrong retry)
# OK 반드시 Admin/My pages(마이페이지) 보다 위에 있어야 합니다.
# ============================================================

def build_quiz_from_word_keys(word_keys: list[str], qtype: str, pos_group: str) -> list[dict]:
    # OK 안전장치
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
    # OK 안전장치
    pos_group = str(pos_group).strip().lower()
    qtype = str(qtype).strip()
    if pos_group in POS_ONLY_2TYPES and qtype == "reading":
        qtype = "meaning"

    ensure_pool_ready()
    pool = st.session_state["_pool"]

    # OK wrong_list에서 jp_word 키 뽑기
    wrong_words = []
    for w in (wrong_list or []):
        key = str(w.get("단어", "")).strip()
        if key:
            wrong_words.append(key)
    wrong_words = list(dict.fromkeys(wrong_words))

    if not wrong_words:
        st.warning("현재 오답 노트가 비어 있어요. 🙂")
        return []

    # OK 현재 화면의 pos 필터(기타면 체크된 세부 품사들)
    pos_filters = get_pos_filters()

    # OK pool에서 오답 단어 + 현재 pos필터로 매칭
    retry_df = pool[
        (pool["pos"].astype(str).str.strip().str.lower().isin(pos_filters))
        & (pool["jp_word"].astype(str).str.strip().isin(wrong_words))
    ].copy()

    if retry_df.empty:
        st.error("오답 단어를 현재 풀(품사/기타 선택)에서 찾지 못했습니다. (jp_word 매칭/필터 확인)")
        return []

    # OK reading이면 ‘한자 포함 jp_word’만
    if qtype == "reading":
        retry_df = retry_df[retry_df["jp_word"].apply(_has_kanji)].copy()
        if retry_df.empty:
            st.warning("오답 중 ‘한자 포함 단어’가 없어 발음 문제로는 복습할 수 없어요. (뜻/한→일로 복습 추천)")
            return []

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)

    # OK 오답 전체를 문제로 만들되, 최대 N개까지만 (원하면 삭제 가능)
    if len(retry_df) > N:
        retry_df = retry_df.head(N).copy()

    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]

# ============================================================
# OK Admin/My pages
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

                st.success("전체 학습 기록이 완전 초기화되었습니다.")
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

    # OK TOP10 시험보기 버튼
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
# OK Home
# ============================================================
def reset_quiz_state_only():
    clear_question_widget_keys()
    for k in ["quiz", "answers", "submitted", "wrong_list",
              "saved_this_attempt", "stats_saved_this_attempt",
              "session_stats_applied_this_attempt"]:
        st.session_state.pop(k, None)

def go_quiz_from_home():
    reset_quiz_state_only()

    # OK 콤보 알림 단계 리셋(오늘 최고 기록은 유지)
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
def render_home():
    u = st.session_state.get("user")
    email = (getattr(u, "email", None) if u else None) or st.session_state.get("login_email", "")

    # OK (1) 타이틀/환영
    st.markdown(
        f"""
<div class="jp headbar">
  <div class="headtitle">✨ 단어</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # OK (2) 오늘의 학습 리포트: 홈에서만 / 타이틀 다음, 오늘의 말 위
    try:
        sb_authed = get_authed_sb()
        user_id = getattr(u, "id", None) if u else None
        if sb_authed and user_id:
            render_today_report_db_only(sb_authed, user_id)
    except Exception:
        # 리포트 실패해도 홈 화면은 멈추지 않게
        pass

    # OK (3) 오늘의 말
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
# OK 오늘의 학습 리포트 (DB only / quiz_attempts 기반)
#   - 로그인 유저만 표시
#   - 오늘 푼 문항 / 정답률 / 오늘 오답 / 연속 학습(streak)
#   - 가장 많이 틀린 모드(pos_mode)
# ============================================================

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import Counter
import html
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
    # OK 오늘 집계
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

    # OK 연속 학습(streak)
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

        # OK 표시용 (PRO 아니면 blur 처리)
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
# OK App Start: refresh → login → routing
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

# HUB에서 실행될 때는 홈/내부 라우팅 대신 바로 퀴즈 화면으로 진입
if st.session_state.get("HUB_MODE"):
    st.session_state.page = "quiz"

user = st.session_state.get("user")
user_id = getattr(user, "id", None) if user else None
user_email = getattr(user, "email", None) if user else None
user_email = user_email or st.session_state.get("login_email")

sb_authed = get_authed_sb()

# OK PRO 캐시가 다른 유저에게 넘어가는 것 방지 (먼저!)
cached_uid = st.session_state.get("plan_cached_user_id")
if cached_uid != user_id:
    st.session_state.pop("plan_cached", None)
    st.session_state["plan_cached_user_id"] = user_id

# OK 로그인 유저 + authed 클라 둘 다 있을 때만 리포트 표시
# if sb_authed and user_id:
#    render_today_report_db_only(sb_authed, user_id)

# OK pos_group 기반 available_types 적용
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

# OK 현재 선택된 유형이 pos_group에서 허용되지 않으면 meaning으로 강제
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

if sb_authed is not None and not st.session_state.get("progress_restored"):
    try:
        restore_progress_from_db(sb_authed, user_id)
    except Exception:
        pass
    st.session_state.progress_restored = True

# OK 복원 후에도 pos_group/available_types 재동기화
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
  <div class="headtitle">✨ 단어</div>
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
# OK Routing
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
# OK PAYWALL CHECK (render_topcard() 보다 위에서 1번만!)
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

# OK 잠금 판단
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

# OK 오늘 푼 문항 수(total) 정의: 목표 UI/DEBUG에서 공통 사용
total = 0
try:
    sb_authed_local = get_authed_sb()
    if sb_authed_local is not None and user_id:
        total = get_daily_solved_from_db(sb_authed_local, user_id)  # 오늘 푼 문항 수
except Exception:
    total = 0

# ============================================================
# OK Quiz Page
# ============================================================
def render_plan_banner():
    # HUB에서는 공통 배지를 home.py에서 렌더링하므로 중복 표시하지 않음
    if st.session_state.get("HUB_MODE", False):
        return

    plan = get_user_plan()
    if plan == "pro":
        st.success("✨ PRO 이용 중입니다.")
        return

    st.info("🔒 일부 기능은 PRO에서 열립니다. (예: 오답만 다시풀기, 발음 버튼, 패턴카드 확장 등)")
    if st.button("💎 PRO 신청/문의", use_container_width=True, key="btn_go_pro"):
        st.session_state["_scroll_top_once"] = True
        st.markdown(f"<meta http-equiv='refresh' content='0;url={NAVER_TALK_URL}'>", unsafe_allow_html=True)

# OK 호출은 정의 아래에서
render_topcard()
render_plan_banner()
render_sound_toggle()

if not st.session_state.get("HUB_MODE", False):
    streak = st.session_state.get("streak_count")
    did_today = st.session_state.get("did_attend_today")
    if streak is not None:
        if did_today:
            st.success(f"오늘 출석 완료!  (연속 {streak}일)")
        else:
            st.caption(f"연속 출석 {streak}일")
        if streak >= 30:
            st.info("🔥 30일 연속 달성!")
        elif streak >= 7:
            st.info("🏅 7일 연속 달성!")

    if not HUB_MODE:
            # --- (A) 기존 "오늘의 목표(루틴)" 섹션 ---
            if "today_goal_text" not in st.session_state:
                st.session_state.today_goal_text = "오늘은 10문항 1회 완주"
            if "today_goal_done" not in st.session_state:
                st.session_state.today_goal_done = False
        
            # ============================================================
            # OK [PATCH] 🎯 오늘 목표 자동 연동 + 진행률 도표(프로그레스 바)
            # - 목표 1회=10문항, 2회=20문항...
            # - today_total(= total) 기준으로 자동 OK달성/⏳진행중
            # - OK “오늘 목표” 박스 안에 진행률 도표 + % 표시
            # - OK 세그먼트 카드/목표 카드 톤(테두리/라운드/그림자) 통일
            # ============================================================
        
            st.markdown("""
            <style>
            /* OK goal 세그먼트 전용 앵커 */
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
        
            # OK 앵커는 segmented_control "바로 직전"에 둬야 함
            st.markdown('<div id="goal_seg_anchor"></div>', unsafe_allow_html=True)
        
        
            # OK 1) 목표(세션) 설정값
            if "goal_sessions" not in st.session_state:
                st.session_state.goal_sessions = 1  # 기본 1회(=10문항)
        
            target_questions = st.slider(
                "오늘 목표",
                min_value=10, max_value=60, step=10,
                value=st.session_state.get("target_questions", 10),
            )
            st.session_state["target_questions"] = target_questions
        
        
            # OK 2) 오늘 푼 문항수(기존 total 변수 재사용)
            today_total = int(total)  # ← 기존 코드에서 total이 "오늘 푼 문항"이면 그대로 OK
        
            goal_done = today_total >= target_questions
            goal_percent = int(min(100, (today_total / max(1, target_questions)) * 100))
            remain = max(0, target_questions - today_total)
        
            goal_msg = "오늘 목표 달성! 내일도 루틴 이어가요 🔥" if goal_done else f"남은 문항: {remain}"
        
        
            # OK 3) 자동 목표 UI (진행률 도표 포함)
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
                  {"달성" if goal_done else "⏳ 진행중"}
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
            components.html(card_html, height=0)
        
        
            st.divider()

# ============================================================
# OK 이하: 기존 세션 상태 초기화/shape ensure (그대로 유지)
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
# OK 상단 UI: 품사 버튼 → (기타 expander + 적용 버튼) → 유형 버튼 → 캡션 → divider
# ============================================================
def on_pick_pos_group(ps: str):
    ps = str(ps).strip().lower()
    if ps == st.session_state.pos_group:
        return
    st.session_state.pos_group = ps

    # OK 제한 그룹이면 reading 선택 상태를 자동 해제
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

# OK 현재 pos_group 기준으로 유형 리스트 재계산(표시 직전에!)
try:
    if sb_authed is not None:
        available_types = get_available_quiz_types_for_pos(st.session_state.get("pos_group", "noun"))
    else:
        g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
        available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER
except Exception:
    g_now = str(st.session_state.get("pos_group", "noun")).lower().strip()
    available_types = ["meaning", "kr2jp"] if g_now in POS_ONLY_2TYPES else QUIZ_TYPES_USER

# OK 선택된 유형이 현재 pos_group에서 허용되지 않으면 meaning으로 강제
if st.session_state.get("quiz_type") not in available_types:
    st.session_state.quiz_type = "meaning"

st.markdown('<div class="qtypewrap">', unsafe_allow_html=True)

st.markdown('<div class="qtype_hint jp">✨품사를 선택하세요</div>', unsafe_allow_html=True)

# OK 품사 그룹 버튼(5개)
pos_cols = st.columns(5, gap="small")
for i, ps in enumerate(POS_GROUP_OPTIONS):
    with pos_cols[i]:
        is_sel = (ps == st.session_state.pos_group)
        st.button(
            ("" if is_sel else "") + POS_LABEL_MAP.get(ps, ps),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_posg_{ps}",
            on_click=on_pick_pos_group,
            args=(ps,),
        )

# OK B안: 기타 선택 시에만 세부 선택 expander + 적용 버튼
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
            # OK 기타는 reading 불가
            if st.session_state.quiz_type == "reading":
                st.session_state.quiz_type = "meaning"

            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.pos_group)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.session_state["_scroll_top_once"] = True
            st.rerun()

st.markdown('<div class="qtype_hint jp">✨유형을 선택하세요</div>', unsafe_allow_html=True)

# OK 유형 버튼
type_cols = st.columns(len(available_types), gap="small")
for i, qt in enumerate(available_types):
    with type_cols[i]:
        is_sel = (qt == st.session_state.quiz_type)
        st.button(
            ("" if is_sel else "") + quiz_label_map.get(qt, qt),
            use_container_width=True,
            type=("primary" if is_sel else "secondary"),
            key=f"btn_qtype_{qt}",
            on_click=on_pick_qtype,
            args=(qt,),
        )

st.markdown("</div>", unsafe_allow_html=True)

# OK 필수패턴(카드)
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
# OK FREE 사용량 기록 (현재는 제한 OFF라 no-op)
# ============================================================
def add_free_used(n: int):
    """FREE 제한을 다시 켤 때를 대비해 남겨둠. 현재는 아무 것도 하지 않음."""
    return

# ============================================================
# OK 버튼: 새 문제(랜덤10) / 맞힌 단어 제외 초기화  (복붙 버전)
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
    
        # OK 새 퀴즈 시작 = 제출 카운트 플래그 리셋
        st.session_state["_counted_today"] = False

        # OK 콤보 알림 단계 리셋(오늘 최고 콤보 기록은 유지)
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
# OK 퀴즈 생성(없으면 1회 자동 생성)
# ============================================================

k_now = mastery_key()  # OK 먼저!

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
        st.success("이 설정에서 새로 출제할 문제가 더 이상 없습니다.")
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
# OK 오늘 목표(Progress) - 세션 기반 (DB 없이)
#   - 상단(1곳)만 사용
#   - 하단은 SHOW_BOTTOM_GOAL=False면 절대 렌더링 안 됨
# ============================================================

SHOW_BOTTOM_GOAL = False  # OK 하단을 완전히 숨기려면 False 유지

def get_today_done_count() -> int:
    return int(st.session_state.get("today_done", 0))

def add_done_count(n: int):
    st.session_state["today_done"] = get_today_done_count() + int(n)

def reset_today_done():
    st.session_state["today_done"] = 0

def get_today_goal_default() -> int:
    return 10

# OK 누적용 상태(필요하면 유지)
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
# OK 하단 렌더링(숨김)
#   - 아래 조건부 블록만 남기고, "직접 호출"은 절대 하지 마세요.
# ============================================================

if SHOW_BOTTOM_GOAL:
    render_today_goal_progress()


# ============================================================
# OK 문제 표시 (동그란 배지: ① ② ③ ... + 같은 줄)
# ============================================================
circled_nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"

with st.form(key=f"quiz_form_word_{st.session_state.quiz_version}"):
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

            # OK PRO만 버튼 렌더링 (무료는 루프 안에서 아무것도 안 찍음)
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
        )
        st.session_state.answers[idx] = choice

    sync_answers_from_widgets()

    submitted_clicked = st.form_submit_button(
        "제출하고 채점하기",
        type="primary",
        use_container_width=True,
        key="btn_submit_form",
    )

# ============================================================
# OK 제출/채점 (FORM)
# - 보기 선택만으로는 rerun이 일어나지 않도록 st.form으로 감쌌습니다.
# - 제출 버튼을 눌렀을 때만 채점/DB 저장을 진행합니다.
# ============================================================
quiz_len = len(st.session_state.quiz)

if submitted_clicked:
    selected_now = []
    for idx, q in enumerate(st.session_state.quiz):
        widget_key = f"q_{st.session_state.quiz_version}_{idx}"
        selected_now.append(st.session_state.get(widget_key, None))

    all_answered = (quiz_len > 0) and all(a is not None for a in selected_now)

    if not all_answered:
        st.warning("아직 선택하지 않은 문제가 있어요. 모든 문제에 답을 선택해 주세요 🙂")
        st.session_state.submitted = False
    else:
        st.session_state.submitted = True
        st.session_state.session_stats_applied_this_attempt = False

        # OK 제출 시점에만 answers에 확정 반영
        st.session_state.answers = selected_now

        # OK 중복 카운트 방지
        if not st.session_state.get("_counted_today", False):
            add_done_count(int(st.session_state.get("quiz_len", 10)))
            st.session_state["_counted_today"] = True

# ============================================================
# OK 제출 후 화면
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
                "품사": current_pos_group,   # OK 그룹 저장
                "유형": current_type,
            })

    st.session_state.wrong_list = wrong_list

    # ============================================================
    # OK 오답 상세 저장 (wrong_notes) — 3회 이상 반복오답/Top10 복습용
    # - 홈/마이페이지에서 '단어/정답/내답' 카드 복원을 위해 필요
    rows = []
    sb_authed = get_authed_sb()
    u_id = getattr(st.session_state.get("user"), "id", None)

    if (not u_id) and st.session_state.get("access_token"):
        try:
            u = sb.auth.get_user(st.session_state.get("access_token"))
            u_id = getattr(getattr(u, "user", None), "id", None) or getattr(u, "id", None)
        except Exception:
            u_id = None

    # OK wrong_notes는 "가능하면 저장" (실패해도 채점/진행은 계속)
    try:
        if sb_authed is None:
            _wn_warn("오답 저장 실패: authed client 없음(access_token).")
        elif not u_id:
            _wn_warn("오답 저장 실패: user_id(uid) 없음. 로그인 세션을 확인하세요.")
        else:
            for w in (st.session_state.get("wrong_list") or []):
                rows.append({
                    "user_id": str(u_id),
                    "quiz_type": "word",
                    "question": str(w.get("단어") or w.get("question") or ""),
                    "correct_answer": str(w.get("정답") or w.get("correct") or ""),
                    "user_answer": str(w.get("내 답") or w.get("user") or ""),
                    "level": str(st.session_state.get("level", "") or ""),
                })
            if rows:
                sb_authed.table("wrong_notes").insert(rows).execute()
    except Exception as e:
        _wn_warn(f"오답 저장 실패: {e}")

    # ============================================================
    # OK 결과/효과/UI (OK 항상 실행)
    # ============================================================
    st.success(f"점수: {score} / {quiz_len}")

    # OK FREE 제한 카운트 누적 (제출 1회 = quiz_len 소비)
    #    같은 제출 화면에서 rerun이 여러 번 나도 중복 누적되지 않도록 1회만 적용
    if "free_limit_applied_this_attempt" not in st.session_state:
        st.session_state.free_limit_applied_this_attempt = False

    if not st.session_state.free_limit_applied_this_attempt:
        add_free_used(quiz_len)  # 보통 10
        st.session_state.free_limit_applied_this_attempt = True

    
    ratio = score / quiz_len if quiz_len else 0.0

    # OK 점수 기반 SFX (제출 직후 1회) — core.py에서 중앙 통제
    _sfx_key = f"word_submit__{int(st.session_state.get('quiz_version', 0) or 0)}"
    if ratio == 1:
        core.play_sfx_once(_sfx_key, "reward")
        st.balloons()
        st.success("🎉 완벽해요! 전부 정답입니다.")
    elif ratio >= 0.7:
        core.play_sfx_once(_sfx_key, "correct")
        st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
    else:
        core.play_sfx_once(_sfx_key, "wrong")
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
                    pos=current_pos_group,   # OK 그룹 저장
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
                    pos=current_pos_group,  # OK 그룹 기준
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
    # OK 콤보 계산 (⚠️ 반드시 제출 후에만)
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
    # OK 제출 후 화면 내부 "오답노트" 블록
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
# OK 제출 후 하단 액션 버튼 (오답 유무와 무관하게 항상 표시)
# ============================================================
if st.session_state.get("submitted", False):
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cA, cB = st.columns(2)
    with cA:
        locked = free_limit_reached()

        if locked:
            st.caption("🔒 오늘 무료 한도(30문항)를 모두 사용했어요.")

        if st.button(
            "다음 10문항 시작하기",
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

    show_naver_talk = (SHOW_NAVER_TALK == "Y") or is_admin()
    if show_naver_talk:
        render_naver_talk()
