# hotena kanji quiz module (cleaned)
# - Hub(home.py) provides: cfg, cookies, sb, sb_authed, user, login_email, is_admin flags
# - This file focuses only on: CSV pool -> quiz build -> quiz UI -> wrong note

from __future__ import annotations

from pathlib import Path
import random
import time
import unicodedata
import traceback
from collections import Counter

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


# ============================================================
# Page config (home.py is the owner; standalone-safe)
# ============================================================
if not st.session_state.get("_page_config_set"):
    try:
        st.set_page_config(page_title="Hotena", layout="centered")
    except Exception:
        pass


# ============================================================
# Top spacing + radio compact (keep: UX 핵심)
# ============================================================
st.markdown(
    """<style>
section.main > div.block-container,
div[data-testid="stAppViewContainer"] > div.block-container {
  padding-top: 0rem !important;
  margin-top: 0rem !important;
}

div.block-container > div:first-child {
  margin-top: 0rem !important;
  padding-top: 0rem !important;
}

header[data-testid="stHeader"]{
  height: 0px !important;
  min-height: 0px !important;
}

@media (max-width: 768px){
  section.main > div.block-container,
  div[data-testid="stAppViewContainer"] > div.block-container {
    padding-top: 0rem !important;
    margin-top: 0rem !important;
  }
}
</style>""",
    unsafe_allow_html=True,
)

st.markdown(
    """<style>
/* HN RADIO COMPACT (v4) */
div[data-testid="stRadio"] div[role="radiogroup"]{ gap: 0px !important; }

div[data-testid="stRadio"] div[data-baseweb="radio"]{
  margin: 0 0 0.28rem 0 !important;
  padding: 0 !important;
}

div[data-testid="stRadio"] div[data-baseweb="radio"] > div{ padding: 0 !important; }

div[data-testid="stRadio"] label,
div[data-testid="stRadio"] span{ line-height: 1.32 !important; }
</style>""",
    unsafe_allow_html=True,
)

st.session_state["_page_config_set"] = True


# ============================================================
# Typography (keep)
# ============================================================
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Kosugi+Maru&family=Noto+Sans+JP:wght@400;500;700;800&display=swap" rel="stylesheet">

<style>
:root{ --jp-rounded: "Noto Sans JP","Kosugi Maru","Hiragino Sans","Yu Gothic","Meiryo",sans-serif; }
.jp, .jp *{ font-family: var(--jp-rounded) !important; line-height:1.7; letter-spacing:.2px; }

div[data-testid="stRadio"] * ,
div[data-baseweb="radio"] * ,
label[data-baseweb="radio"] * { font-family: var(--jp-rounded) !important; }

/* 헤더 여백 */
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4{
  margin-top: 10px !important;
  margin-bottom: 8px !important;
}

/* 버튼 기본 */
div.stButton > button {
  padding: 6px 10px !important;
  font-size: 13px !important;
  line-height: 1.1 !important;
  white-space: nowrap !important;
}

/* 상단 타이틀 */
.headbar{ display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin: 10px 0 16px 0; }
.headtitle{ font-size:34px; font-weight:900; line-height:1.15; white-space: nowrap; }
@media (max-width: 480px){ .headtitle{ font-size:24px; } }

/* 레벨/유형 버튼 스타일 */
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
.qtype_hint{ font-size: 15px; opacity: .70; margin-top: 2px; margin-bottom: 10px; line-height: 1.2; }
.tight-divider hr{ margin: 6px 0 10px 0 !important; }

div[data-testid="stMarkdownContainer"] h3{ margin-bottom: 4px !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# Helpers
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "words_kanji.csv"
KST_TZ = "Asia/Seoul"
N = 10

quiz_label_map = {"reading": "발음", "meaning": "뜻", "kr2jp": "한→일"}
QUIZ_TYPES_USER = ["reading", "meaning", "kr2jp"]
LEVEL_OPTIONS = ["N5", "N4", "N3", "N2", "N1"]


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin") or st.session_state.get("is_admin_cached"))


def get_authed_sb():
    return st.session_state.get("supabase_authed") or st.session_state.get("sb_authed")


def to_kst_naive(x):
    ts = pd.to_datetime(x, utc=True, errors="coerce")
    if isinstance(ts, pd.Series):
        return ts.dt.tz_convert(KST_TZ).dt.tz_localize(None)
    if pd.isna(ts):
        return ts
    return ts.tz_convert(KST_TZ).tz_localize(None)


def clear_question_widget_keys():
    keys_to_del = [k for k in list(st.session_state.keys()) if isinstance(k, str) and k.startswith("q_")]
    for k in keys_to_del:
        st.session_state.pop(k, None)


def start_quiz_state(quiz_list: list, qtype: str, clear_wrongs: bool = True):
    st.session_state.quiz_version = int(st.session_state.get("quiz_version", 0)) + 1
    st.session_state.quiz_type = qtype
    st.session_state.quiz = quiz_list if isinstance(quiz_list, list) else []
    st.session_state.answers = [None] * len(st.session_state.quiz)
    st.session_state.submitted = False
    if clear_wrongs:
        st.session_state.wrong_list = []


def mastery_key(qtype: str | None = None, level: str | None = None) -> str:
    qt = qtype or st.session_state.get("quiz_type", "reading")
    lv = (level or st.session_state.get("level", "N5")).upper()
    return f"{lv}__{qt}"


def ensure_mastered_words_shape():
    if "mastered_words" not in st.session_state or not isinstance(st.session_state.mastered_words, dict):
        st.session_state.mastered_words = {}
    for qt in QUIZ_TYPES_USER:
        st.session_state.mastered_words.setdefault(mastery_key(qt), set())


def ensure_excluded_wrong_words_shape():
    if "excluded_wrong_words" not in st.session_state or not isinstance(st.session_state.excluded_wrong_words, dict):
        st.session_state.excluded_wrong_words = {}
    for qt in QUIZ_TYPES_USER:
        st.session_state.excluded_wrong_words.setdefault(mastery_key(qt), set())


def ensure_mastery_banner_shape():
    if "mastery_banner_shown" not in st.session_state or not isinstance(st.session_state.mastery_banner_shown, dict):
        st.session_state.mastery_banner_shown = {}
    if "mastery_done" not in st.session_state or not isinstance(st.session_state.mastery_done, dict):
        st.session_state.mastery_done = {}
    for qt in QUIZ_TYPES_USER:
        k = mastery_key(qt)
        st.session_state.mastery_banner_shown.setdefault(k, False)
        st.session_state.mastery_done.setdefault(k, False)


# ============================================================
# Pool loader
# ============================================================
READ_KW = dict(
    dtype=str,
    keep_default_na=False,
    na_values=["nan", "NaN", "NULL", "null", "None", "none"],
)


@st.cache_data(show_spinner=False)
def load_pool(csv_path_str: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path_str, **READ_KW)

    required_cols = {"level", "jp_word", "reading", "meaning", "pos"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV 필수 컬럼 누락: {sorted(list(missing))}")

    df["pos"] = df["pos"].astype(str).str.strip().str.lower()

    def _nfkc(s):
        return unicodedata.normalize("NFKC", str(s or ""))

    lv = df["level"].apply(_nfkc).astype(str).str.upper().str.strip()
    lv = lv.str.replace(" ", "", regex=False)
    extracted = lv.str.extract(r"(N[1-5])", expand=False)
    digit_map = {"1": "N1", "2": "N2", "3": "N3", "4": "N4", "5": "N5"}
    only_digit = lv.where(extracted.isna(), "")
    only_digit = only_digit.str.extract(r"^([1-5])$", expand=False)
    digit_fixed = only_digit.map(digit_map)
    final_lv = extracted.fillna(digit_fixed).fillna(lv)
    final_lv = final_lv.where(final_lv.isin(["N1", "N2", "N3", "N4", "N5"]), "")
    df["level"] = final_lv

    df["jp_word"] = df["jp_word"].astype(str).str.strip()
    df["reading"] = df["reading"].astype(str).str.strip()
    df["meaning"] = df["meaning"].astype(str).str.strip()

    df = df[(df["jp_word"] != "") & (df["reading"] != "") & (df["meaning"] != "")].copy()
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
        with st.expander("🔎 디버그: 레벨별 단어 수", expanded=False):
            st.write(pool["level"].value_counts(dropna=False))
            st.write("CSV_PATH =", str(CSV_PATH))


# ============================================================
# Quiz logic
# ============================================================

def _nfkc_str(x) -> str:
    return unicodedata.normalize("NFKC", str(x or "")).strip()


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


def _last_char(x) -> str:
    s = _to_hira(_nfkc_str(x))
    return s[-1] if s else ""


def _vowel_group(kana_or_word: str) -> str:
    ch = _last_char(kana_or_word)
    if not ch:
        return "other"
    if ch == "ん":
        return "n"
    if ch in "ぁぃぅぇぉゃゅょっーゎ":
        return "other"

    A = set("あかさたなはまやらわがざだばぱぁゃゎ")
    I = set("いきしちにひみりぎじぢびぴぃ")
    U = set("うくすつぬふむゆるぐずづぶぷぅゅ")
    E = set("えけせてねへめれげぜでべぺぇ")
    O = set("おこそとのほもよろをごぞどぼぽぉょを")

    if ch in A:
        return "a"
    if ch in I:
        return "i"
    if ch in U:
        return "u"
    if ch in E:
        return "e"
    if ch in O:
        return "o"
    return "other"


def _uniq(xs):
    out, seen = [], set()
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _pick_reading_wrongs(
    candidates: list[str],
    correct: str,
    pos: str,
    jp_word: str = "",
    k: int = 3,
    strict_pos: set[str] | None = None,
) -> list[str]:
    def _suffix(x: str, n: int) -> str:
        s = _to_hira(_nfkc_str(x))
        return s[-n:] if len(s) >= n else s

    if strict_pos is None:
        strict_pos = {"v", "verb", "adj", "adj_i", "adj_na", "i_adj", "adj-i"}

    correct_nf = _nfkc_str(correct)
    cands = _uniq([_nfkc_str(c) for c in candidates if _nfkc_str(c) and _nfkc_str(c) != correct_nf])
    if len(cands) < k:
        return []

    s1 = _suffix(correct_nf, 1)
    s2 = _suffix(correct_nf, 2)

    jp_h = _to_hira(_nfkc_str(jp_word))
    rd_h = _to_hira(correct_nf)
    force_i_adj = (jp_h.endswith("い") and rd_h.endswith("い"))

    if (pos in strict_pos) or force_i_adj:
        same2 = _uniq([c for c in cands if _suffix(c, 2) == s2])
        if len(same2) >= k:
            return random.sample(same2, k)

        same1 = _uniq([c for c in cands if _suffix(c, 1) == s1])
        if len(same1) >= k:
            wrongs = same2[:]
            rest = [c for c in same1 if c not in wrongs]
            need = k - len(wrongs)
            if need > 0:
                if len(rest) >= need:
                    wrongs += random.sample(rest, need)
                else:
                    pool_all = [c for c in cands if c not in wrongs]
                    wrongs += random.sample(pool_all, min(need, len(pool_all)))
            return wrongs[:k]

        g = _vowel_group(correct_nf)
        vg = _uniq([c for c in cands if _vowel_group(c) == g])
        if len(vg) >= k:
            return random.sample(vg, k)

        return random.sample(cands, k)

    base = cands[:]
    random.shuffle(base)
    wrongs, seen_last = [], set()

    for c in base:
        lc = _last_char(c)
        if lc and lc not in seen_last:
            wrongs.append(c)
            seen_last.add(lc)
            if len(wrongs) == k:
                return wrongs

    rest = [c for c in base if c not in wrongs]
    if len(rest) >= (k - len(wrongs)):
        wrongs += random.sample(rest, k - len(wrongs))
        return wrongs

    return wrongs


def make_question(row: pd.Series, qtype: str, pool: pd.DataFrame) -> dict:
    jp = str(row.get("jp_word", "")).strip()
    rd = str(row.get("reading", "")).strip()
    mn = str(row.get("meaning", "")).strip()
    lvl = str(row.get("level", "")).strip().upper()
    pos = str(row.get("pos", "")).strip().lower()

    pool_pos = pool[pool["pos"].astype(str).str.strip().str.lower() == pos].copy()

    if qtype == "reading":
        prompt = f"{jp}의 발음은?"
        correct = rd
        candidates = pool_pos.loc[pool_pos["reading"] != correct, "reading"].dropna().drop_duplicates().tolist()
        wrongs = _pick_reading_wrongs(candidates, correct, pos=pos, jp_word=jp, k=3)
        if len(wrongs) < 3:
            st.error(f"오답 후보 부족(발음): pos={pos}, 후보={len(candidates)}개")
            st.stop()

    elif qtype == "meaning":
        prompt = f"{jp}의 뜻은?"
        correct = mn
        candidates = pool_pos.loc[pool_pos["meaning"] != correct, "meaning"].dropna().drop_duplicates().tolist()
        if len(candidates) < 3:
            st.error(f"오답 후보 부족(뜻): pos={pos}, 후보={len(candidates)}개")
            st.stop()
        wrongs = random.sample(candidates, 3)

    elif qtype == "kr2jp":
        prompt = f"'{mn}'의 일본어(한자)는?"
        correct = jp
        candidates = pool_pos.loc[pool_pos["jp_word"] != correct, "jp_word"].dropna().astype(str).str.strip().tolist()
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
        "level": lvl,
        "pos": pos,
        "qtype": qtype,
    }


def build_quiz(qtype: str, level: str) -> list[dict]:
    ensure_pool_ready()
    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()

    pool = st.session_state["_pool"]
    level = str(level).strip().upper()
    base_level = pool[pool["level"].astype(str).str.upper() == level].copy()

    if len(base_level) < N:
        st.warning(f"{level} 단어가 부족합니다. (현재 {len(base_level)}개 / 필요 {N}개)")
        return []

    k = mastery_key(qtype=qtype)
    mastered = st.session_state.get("mastered_words", {}).get(k, set())
    excluded = st.session_state.get("excluded_wrong_words", {}).get(k, set())

    blocked = set()
    if mastered:
        blocked |= set(mastered)
    if excluded:
        blocked |= set(excluded)

    def _filter_blocked(df: pd.DataFrame) -> pd.DataFrame:
        if not blocked:
            return df
        keys = df["jp_word"].astype(str).str.strip()
        return df[~keys.isin(blocked)].copy()

    base = _filter_blocked(base_level)

    if len(base) < N:
        st.session_state.setdefault("mastery_done", {})
        st.session_state.mastery_done[k] = True
        return []

    sampled = base.sample(n=N, replace=False).reset_index(drop=True)
    return [make_question(sampled.iloc[i], qtype, pool) for i in range(N)]


def build_quiz_from_wrongs(wrong_list: list, qtype: str) -> list:
    ensure_pool_ready()
    pool = st.session_state["_pool"]

    wrong_words = []
    for w in (wrong_list or []):
        key = str(w.get("단어", "")).strip()
        if key:
            wrong_words.append(key)
    wrong_words = list(dict.fromkeys(wrong_words))

    if not wrong_words:
        st.warning("현재 오답 노트가 비어 있어요. 🙂")
        return []

    retry_df = pool[pool["jp_word"].isin(wrong_words)].copy()
    if len(retry_df) == 0:
        st.error("오답 단어를 풀에서 찾지 못했습니다. (jp_word 매칭 확인)")
        st.stop()

    retry_df = retry_df.sample(frac=1).reset_index(drop=True)
    return [make_question(retry_df.iloc[i], qtype, pool) for i in range(len(retry_df))]


# ============================================================
# UI
# ============================================================

def render_kanji_quiz(HUB_MODE: bool = True):
    if HUB_MODE:
        st.session_state["HUB_MODE"] = True

    # 세션 기본값
    st.session_state.setdefault("quiz_version", 0)
    st.session_state.setdefault("submitted", False)
    st.session_state.setdefault("wrong_list", [])
    st.session_state.setdefault("quiz_type", "reading")
    st.session_state.setdefault("level", "N5")

    if st.session_state.level not in LEVEL_OPTIONS:
        st.session_state.level = "N5"
    if st.session_state.quiz_type not in QUIZ_TYPES_USER:
        st.session_state.quiz_type = "reading"

    ensure_mastered_words_shape()
    ensure_excluded_wrong_words_shape()
    ensure_mastery_banner_shape()

    # title
    st.markdown(
        """
<div class="jp headbar">
  <div class="headtitle">✨ 한자 퀴즈</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="qtypewrap">', unsafe_allow_html=True)

    def on_pick_level(lv: str):
        lv = str(lv).strip().upper()
        if lv == st.session_state.level:
            return
        st.session_state.level = lv
        clear_question_widget_keys()
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
        st.session_state["_scroll_top_once"] = True

    def on_pick_qtype(qt: str):
        qt = str(qt).strip()
        if qt == st.session_state.quiz_type:
            return
        st.session_state.quiz_type = qt
        clear_question_widget_keys()
        new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
        start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
        st.session_state["_scroll_top_once"] = True

    st.markdown('<div class="qtype_hint jp">✨레벨을 선택하세요</div>', unsafe_allow_html=True)
    level_cols = st.columns(len(LEVEL_OPTIONS), gap="small")
    for i, lv in enumerate(LEVEL_OPTIONS):
        is_selected = (lv == st.session_state.level)
        with level_cols[i]:
            st.button(
                lv,
                use_container_width=True,
                type="primary" if is_selected else "secondary",
                key=f"btn_level_{lv}",
                on_click=on_pick_level,
                args=(lv,),
            )

    st.markdown('<div class="qtype_hint jp">✨유형을 선택하세요</div>', unsafe_allow_html=True)
    type_cols = st.columns(len(QUIZ_TYPES_USER), gap="small")
    for i, qt in enumerate(QUIZ_TYPES_USER):
        is_selected = (qt == st.session_state.quiz_type)
        with type_cols[i]:
            st.button(
                quiz_label_map.get(qt, qt),
                use_container_width=True,
                type="primary" if is_selected else "secondary",
                key=f"btn_qtype_{qt}",
                on_click=on_pick_qtype,
                args=(qt,),
            )

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="tight-divider">', unsafe_allow_html=True)
    st.divider()
    st.markdown('</div>', unsafe_allow_html=True)

    cbtn1, cbtn2 = st.columns(2)

    with cbtn1:
        if st.button("🔄 새 문제(랜덤 10문항)", use_container_width=True, key="btn_new_random_10"):
            k_now = mastery_key()
            if st.session_state.get("mastery_done", {}).get(k_now, False):
                st.rerun()
            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.rerun()

    with cbtn2:
        if st.button("맞힌 단어 제외 초기화", use_container_width=True, key="btn_reset_mastered_current_type"):
            k_now = mastery_key()
            st.session_state.mastered_words[k_now] = set()
            st.session_state.mastery_banner_shown[k_now] = False
            st.session_state.mastery_done[k_now] = False
            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.success(f"초기화 완료 (유형: {quiz_label_map[st.session_state.quiz_type]})")
            st.rerun()

    k_now = mastery_key()
    if st.session_state.get("mastery_done", {}).get(k_now, False):
        st.success("🏆 이 유형을 완전히 정복했어요!")
        st.caption("👉 다른 유형을 선택하거나, '맞힌 단어 제외 초기화'로 다시 시작할 수 있어요.")
        st.stop()

    # quiz ensure
    if "quiz" not in st.session_state or not isinstance(st.session_state.quiz, list):
        st.session_state.quiz = []

    if len(st.session_state.quiz) == 0:
        clear_question_widget_keys()
        st.session_state.quiz = build_quiz(st.session_state.quiz_type, st.session_state.level) or []
        st.session_state.submitted = False

    if len(st.session_state.quiz) == 0:
        st.info("이 레벨에 출제할 단어가 없어요. 다른 레벨을 선택하거나, CSV의 level 값을 확인해 주세요.")
        st.stop()

    quiz_len = len(st.session_state.quiz)
    if "answers" not in st.session_state or not isinstance(st.session_state.answers, list) or len(st.session_state.answers) != quiz_len:
        st.session_state.answers = [None] * quiz_len

    # problems
    circled_nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"

    for idx, q in enumerate(st.session_state.quiz):
        badge = circled_nums[idx] if idx < len(circled_nums) else f"({idx+1})"

        st.markdown(
            f"""
<div class="jp" style="display:flex; align-items:baseline; gap:5px; margin: 10px 0 8px 0;">
  <div style="flex:0 0 auto; font-size:20px; line-height:1; font-weight:900; transform: translateY(1px);">{badge}</div>
  <div style="flex:1 1 auto; font-size:18px; font-weight:500; line-height:1.35;">{q['prompt']}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        widget_key = f"q_{st.session_state.quiz_version}_{idx}"
        prev = st.session_state.answers[idx]
        default_index = q["choices"].index(prev) if (prev is not None and prev in q["choices"]) else None

        choice = st.radio(
            label="보기",
            options=q["choices"],
            index=default_index,
            key=widget_key,
            label_visibility="collapsed",
        )
        st.session_state.answers[idx] = choice

    all_answered = (quiz_len > 0) and all(a is not None for a in st.session_state.answers)

    if st.button("제출하고 채점하기", disabled=not all_answered, type="primary", use_container_width=True, key="btn_submit"):
        st.session_state.submitted = True

    if not all_answered:
        st.info("모든 문제에 답을 선택하면 제출 버튼이 활성화됩니다.")

    # post-submit
    if st.session_state.submitted:
        score = 0
        wrong_list = []
        current_type = st.session_state.quiz_type

        for idx, q in enumerate(st.session_state.quiz):
            picked = st.session_state.answers[idx]
            correct = q["correct_text"]
            word_key = str(q.get("jp_word", "")).strip()

            if picked == correct:
                score += 1
                if word_key:
                    st.session_state.mastered_words.setdefault(k_now, set()).add(word_key)
            else:
                wrong_list.append(
                    {
                        "No": idx + 1,
                        "문제": str(q.get("prompt", "")),
                        "내 답": "" if picked is None else str(picked),
                        "정답": str(correct),
                        "단어": str(q.get("jp_word", "")).strip(),
                        "읽기": str(q.get("reading", "")).strip(),
                        "뜻": str(q.get("meaning", "")).strip(),
                        "유형": current_type,
                    }
                )

        st.session_state.wrong_list = wrong_list

        st.success(f"점수: {score} / {quiz_len}")
        ratio = (score / quiz_len) if quiz_len else 0

        if ratio == 1:
            st.balloons()
            st.success("🎉 완벽해요! 전부 정답입니다. 정말 잘했어요!")
            st.caption("※ 정복 판정은 ‘더 이상 출제할 단어가 없을 때’ 자동으로 표시됩니다.")
        elif ratio >= 0.7:
            st.info("👍 잘하고 있어요! 조금만 더 다듬으면 완벽해질 거예요.")
        else:
            st.warning("💪 괜찮아요! 틀린 문제는 성장의 재료예요. 다시 한 번 도전해봐요.")

        # 오답 노트
        if st.session_state.wrong_list:
            st.subheader("❌ 오답 노트")

            st.markdown(
                """
<style>
.wrong-card{ border: 1px solid rgba(120,120,120,0.25); border-radius: 16px; padding: 14px 14px; margin-bottom: 10px; background: rgba(255,255,255,0.02); }
.wrong-top{ display:flex; align-items:flex-start; justify-content:space-between; gap:12px; margin-bottom: 8px; }
.wrong-title{ font-weight: 900; font-size: 15px; margin-bottom: 4px; }
.wrong-sub{ opacity: 0.8; font-size: 12px; }
.tag{ display:inline-flex; align-items:center; gap:6px; padding: 5px 9px; border-radius: 999px; font-size: 12px; font-weight: 700; border: 1px solid rgba(120,120,120,0.25); background: rgba(255,255,255,0.03); white-space: nowrap; }
.ans-row{ display:grid; grid-template-columns: 72px 1fr; gap:10px; margin-top:6px; font-size: 13px; }
.ans-k{ opacity: 0.7; font-weight: 700; }
</style>
""",
                unsafe_allow_html=True,
            )

            def _s(v):
                return "" if v is None else str(v)

            for w in st.session_state.wrong_list:
                no = _s(w.get("No"))
                qtext = _s(w.get("문제"))
                picked = _s(w.get("내 답"))
                correct = _s(w.get("정답"))
                word = _s(w.get("단어"))
                reading = _s(w.get("읽기"))
                meaning = _s(w.get("뜻"))
                mode = quiz_label_map.get(w.get("유형"), w.get("유형", ""))

                st.markdown(
                    f"""
<div class="jp">
  <div class="wrong-card">
    <div class="wrong-top">
      <div>
        <div class="wrong-title">Q{no}. {word}</div>
        <div class="wrong-sub">{qtext} · 유형: {mode}</div>
      </div>
      <div class="tag">오답</div>
    </div>
    <div class="ans-row"><div class="ans-k">내 답</div><div>{picked}</div></div>
    <div class="ans-row"><div class="ans-k">정답</div><div><b>{correct}</b></div></div>
    <div class="ans-row"><div class="ans-k">발음</div><div>{reading}</div></div>
    <div class="ans-row"><div class="ans-k">뜻</div><div>{meaning}</div></div>
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )

            if st.button("❌ 틀린 문제만 다시 풀기", type="primary", use_container_width=True, key="btn_retry_wrongs_bottom"):
                clear_question_widget_keys()
                retry_quiz = build_quiz_from_wrongs(st.session_state.wrong_list, st.session_state.quiz_type)
                start_quiz_state(retry_quiz, st.session_state.quiz_type, clear_wrongs=True)
                st.rerun()

        if st.button("다음 10문항 시작하기", type="primary", use_container_width=True, key="btn_next_10"):
            clear_question_widget_keys()
            new_quiz = build_quiz(st.session_state.quiz_type, st.session_state.level)
            start_quiz_state(new_quiz, st.session_state.quiz_type, clear_wrongs=True)
            st.rerun()


# ============================================================
# Entry points
# ============================================================

def render():
    """Home hub에서 import 후 호출되는 진입점."""
    try:
        render_kanji_quiz(HUB_MODE=True)
    except Exception:
        st.error("한자 퀴즈에서 예외가 발생했습니다. 아래 Traceback을 확인해 주세요.")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    # Standalone run (no hub). It will work without DB features.
    render_kanji_quiz(HUB_MODE=False)
