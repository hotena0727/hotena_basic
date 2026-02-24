# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations
# BUILD_STAMP_TALK: talk-newset-in-progress-v1 2026-02-22 KST (+09:00)

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib

import pandas as pd
import streamlit as st



# ============================================================
# ✅ wrong_notes debug helper
# ============================================================
_WN_DEBUG = bool(st.session_state.get("is_admin", False)) or bool(st.session_state.get("is_admin_cached", False))
def _wn_warn(msg: str):
    if _WN_DEBUG:
        try:
            st.warning(msg)
        except Exception:
            pass
# ============================================================
# ✅ HUB 진입 시: 선택/제출 상태 초기화 (회화)
# ============================================================
if st.session_state.get("_entered_talk"):
    for k in list(st.session_state.keys()):
        if k.startswith("talk_") or k in ("submitted", "is_graded", "answers"):
            st.session_state.pop(k, None)
    st.session_state["_entered_talk"] = False


import streamlit.components.v1 as components
from supabase import create_client

# ============================================================
# ✅ Settings
# ============================================================
NS = "talk"
SET_LEN = 10

# ============================================================
# ✅ Hub login required
# ============================================================
u = st.session_state.get("user")
if not u:
    st.warning("홈에서 로그인 후 이용해 주세요.")
    st.stop()

USER_ID = getattr(u, "id", None)
USER_EMAIL = getattr(u, "email", "") or ""

USER_PLAN = (st.session_state.get("user_plan") or "free").lower()
IS_PRO = USER_PLAN == "pro"

st.title("회화 훈련 · 상황판단")
st.caption("1문제씩: 상황 → 상대 발화(🔊/PRO) → 보기 선택 → 제출 → 정답/설명 → (선택)말하기 완료 체크")

# ============================================================
# ✅ Supabase client (hub reuse)
# ============================================================

def get_cfg(key: str) -> str:
    cfg = st.session_state.get("cfg") or {}
    v = cfg.get(key)
    if v:
        return v
    try:
        return st.secrets[key]
    except Exception:
        return ""


def get_sb():
    sb = st.session_state.get("sb")
    if sb is not None:
        return sb


def get_authed_sb():
    # 홈허브 로그인 세션의 access_token을 사용해 PostgREST 권한 요청을 보냅니다.
    token = st.session_state.get("access_token")
    if not token:
        return None

    cached = st.session_state.get("_sb_authed_talk")
    cached_token = st.session_state.get("_sb_authed_talk_token")
    if cached is not None and cached_token == token:
        return cached

    sb2 = get_sb()
    try:
        # supabase-py: postgrest.auth(token)
        sb2.postgrest.auth(token)
    except Exception:
        # 일부 버전은 내부 client 설정이 다를 수 있음
        pass

    st.session_state["_sb_authed_talk"] = sb2
    st.session_state["_sb_authed_talk_token"] = token
    return sb2
    url = get_cfg("SUPABASE_URL")
    key = get_cfg("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error("Supabase 설정이 없습니다. (SUPABASE_URL / SUPABASE_ANON_KEY)")
        st.stop()
    sb = create_client(url, key)
    st.session_state["sb"] = sb
    return sb


sb = get_sb()

# ============================================================
# ✅ CSV load
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "talk_situations.csv"

if not CSV_PATH.exists():
    st.error(f"CSV 파일이 없습니다: {CSV_PATH}")
    st.stop()


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = ["qid", "level", "tag", "situation_kr", "partner_jp", "answer_jp"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"CSV 필수 컬럼 누락: {c}")

    # 문자열 정리
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
            df[c] = df[c].replace({"nan": "", "NaN": "", "None": ""})

    # level/tag 소문자
    df["level"] = df["level"].astype(str).str.lower().str.strip()
    df["tag"] = df["tag"].astype(str).str.lower().str.strip()

    return df.fillna("")


DF = load_csv(CSV_PATH)

# ============================================================
# ✅ Labels
# ============================================================
TAG_LABELS = {
    "business": "비즈니스",
    "daily": "일상",
    "call": "전화/온라인",
    "interview": "면접",
    "travel": "여행",
    "shopping": "쇼핑",
    "food": "음식/카페",
    "emergency": "긴급/트러블",
}
LEVEL_LABELS = {"n5": "N5", "n4": "N4", "n3": "N3"}

# ============================================================
# ✅ Progress I/O (profiles.progress)
# ============================================================

def load_progress() -> dict:
    if isinstance(st.session_state.get("progress_all"), dict):
        return st.session_state["progress_all"]
    try:
        resp = sb.table("profiles").select("progress").eq("id", USER_ID).single().execute()
        prog = (getattr(resp, "data", None) or {}).get("progress") or {}
        if not isinstance(prog, dict):
            prog = {}
        st.session_state["progress_all"] = prog
        return prog
    except Exception:
        prog = {}
        st.session_state["progress_all"] = prog
        return prog


def save_progress(progress_all: dict):
    st.session_state["progress_all"] = progress_all
    try:
        sb.table("profiles").update({"progress": progress_all}).eq("id", USER_ID).execute()
    except Exception:
        pass


def log_attempt(level: str, score: int, quiz_len: int, wrong_count: int, wrong_list: list[dict], tag: str):
    try:
        sb.table("quiz_attempts").insert(
            {
                "user_id": USER_ID,
                "user_email": USER_EMAIL,
                "level": "talk",  # 홈 마이페이지에서 훈련 구분
                "pos_mode": f"talk:{tag}:{level}",
                "quiz_len": int(quiz_len),
                "score": int(score),
                "wrong_count": int(wrong_count),
                "wrong_list": wrong_list,
            }
        ).execute()
    except Exception:
        pass


def award_xp(amount: int, reason: str):
    fn = st.session_state.get("hub_award_xp")
    if callable(fn):
        fn(int(amount), reason)


# ============================================================
# ✅ New set / reset on hub navigation
# ============================================================

def reset_set():
    for k in list(st.session_state.keys()):
        if k.startswith(f"{NS}_"):
            # 홈에서 공유하는 건 제외
            if k.startswith("talk_"):
                st.session_state.pop(k, None)
    # 안전하게 핵심만 제거
    for k in [
        f"{NS}_set_qids",
        f"{NS}_idx",
        f"{NS}_answers",
        f"{NS}_submitted",
        f"{NS}_selected",
        f"{NS}_opts",
        f"{NS}_spoken",
    ]:
        st.session_state.pop(k, None)


try:
    nav = st.session_state.get("_hub_nav_token")
    last = st.session_state.get(f"_{NS}_last_nav_token")
    if nav and nav != last:
        st.session_state[f"_{NS}_last_nav_token"] = nav
        reset_set()
except Exception:
    pass

# ============================================================
# ✅ Filters (상황(tag) → 레벨(level))  ※ 실전회화만 노출
# ============================================================

# --- normalize (비교 실패/공백 문제 방지) ---
for _c in ["mode", "tag", "level"]:
    if _c in DF.columns:
        DF[_c] = DF[_c].astype(str).fillna("").str.strip()

if "mode" in DF.columns:
    DF["mode"] = DF["mode"].str.lower()
if "tag" in DF.columns:
    DF["tag"] = DF["tag"].str.lower().str.replace(r"[\s\-]+", "_", regex=True)
if "level" in DF.columns:
    # n3/N3/3 혼재 방지: n3 형태로 통일
    DF["level"] = DF["level"].str.lower().str.replace(" ", "")

# --- 실전회화만 사용 (business 데이터는 CSV에 남겨두되 UI에서 제외) ---
DF_BASE = DF.copy()
if "mode" in DF_BASE.columns:
    DF_BASE = DF_BASE[DF_BASE["mode"] == "real"].copy()

# --- 상황(tag) 옵션: DF_BASE 기준 ---
all_tags = [t for t in DF_BASE["tag"].astype(str).unique().tolist() if t]
# business 같은 중복/혼란 태그는 숨김
all_tags = [t for t in all_tags if t not in {"business"}]

# 보기 순서(추천) - 데이터가 없으면 그냥 전체
preferred_order = ["daily", "travel", "food", "shopping", "call", "emergency", "interview"]
tag_options = [t for t in preferred_order if t in all_tags]
TAG_LABEL = {
    "aisatsu": "인사말",
}
def _tag_label(t: str) -> str:
    return TAG_LABEL.get(str(t), str(t))
if not tag_options:
    tag_options = sorted(all_tags)

# tag 변경 시 level이 유효하지 않으면 초기화
_prev_tag = st.session_state.get(f"_{NS}_prev_tag")
if _prev_tag != st.session_state.get(f"{NS}_tag"):
    st.session_state[f"_{NS}_prev_tag"] = st.session_state.get(f"{NS}_tag")
    # 레벨이 이전 선택값으로 남아 충돌하는 걸 방지
    if f"{NS}_level" in st.session_state:
        del st.session_state[f"{NS}_level"]

c1, c2 = st.columns([1.4, 1], vertical_alignment="bottom")
with c1:
    tag = st.selectbox(
        "상황 선택",
        options=tag_options,
        format_func=lambda x: TAG_LABELS.get(x, x, format_func=_tag_label),
        key=f"{NS}_tag",
    )

# --- 레벨 옵션: 선택된 tag에 실제로 존재하는 level만 ---
_df_tag = DF_BASE[DF_BASE["tag"] == tag].copy() if "tag" in DF_BASE.columns else DF_BASE.copy()
levels_in_data = sorted([lv for lv in _df_tag["level"].unique().tolist() if str(lv).strip()])
preferred_lv = [lv for lv in ["n5", "n4", "n3", "n2", "n1"] if lv in levels_in_data]
levels_in_data = preferred_lv or levels_in_data or ["n4", "n3"]

with c2:
    level = st.selectbox(
        "레벨",
        options=levels_in_data,
        format_func=lambda x: LEVEL_LABELS.get(x, str(x).upper()),
        key=f"{NS}_level",
    )

pool_df = DF_BASE[(DF_BASE["tag"] == tag) & (DF_BASE["level"] == level)].copy().reset_index(drop=True)
if pool_df.empty:
    st.warning("해당 조건의 회화 문제가 없습니다. (CSV의 tag/level 확인)")
    st.stop()

# ============================================================
# ✅ TTS (PRO only) - 브라우저 SpeechSynthesis
# ============================================================


def tts_button(text: str, label: str, key: str):
    """브라우저 SpeechSynthesis 기반 TTS 버튼.
    - Streamlit iframe 안에서 직접 버튼을 렌더링(부모 DOM 주입 X) → 가장 안정적
    - PRO: 클릭 시 재생
    - FREE: 잠금된 버튼(비활성) 표시
    """
    safe = (text or "").replace("\\", "\\\\").replace("`", "").replace("\n", " ")
    disabled = "true" if (not IS_PRO) else "false"
    btn_text = (f"🔒 {label}" if (not IS_PRO) else label)
    # key마다 고유한 mount id
    components.html(
        f"""
<div style='width:100%'>
  <button id='tts_{key}' {'disabled' if not IS_PRO else ''} 
    style='width:100%;padding:8px 10px;border-radius:12px;border:1px solid rgba(49,51,63,.18);
           background:{'#f6f7f9' if not IS_PRO else 'white'};cursor:{'not-allowed' if not IS_PRO else 'pointer'};
           font-weight:800;opacity:{'0.7' if not IS_PRO else '1.0'};'>
    {btn_text}
  </button>
</div>
<script>
(function() {{
  const btn = document.getElementById('tts_{key}');
  if (!btn) return;
  if ({disabled}) return;
  // 동일 rerun에서 이벤트 중복 등록 방지
  if (btn.dataset.bound === '1') return;
  btn.dataset.bound = '1';
  btn.addEventListener('click', () => {{
    try {{
      const u = new SpeechSynthesisUtterance({safe!r});
      u.lang = 'ja-JP';
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(u);
    }} catch(e) {{}}
  }});
}})();
</script>
""",
        height=60,
    )

# ======================================
# ======================================
# ✅ Build choices (문제 로딩 시 1회 셔플 후 고정)
# ============================================================

def build_choices(row: dict, pool_answers: list[str]) -> list[str]:
    correct = str(row.get("answer_jp", "")).strip()
    picks: list[str] = []

    for c in ["d1_jp", "d2_jp", "d3_jp"]:
        if c in row:
            v = str(row.get(c, "")).strip()
            if v and v != correct and v not in picks:
                picks.append(v)

    if len(picks) < 3:
        cand = [a for a in pool_answers if a and a != correct and a not in picks]
        random.shuffle(cand)
        picks += cand[: (3 - len(picks))]

    picks = picks[:3]
    choices = picks + [correct]
    random.shuffle(choices)
    return choices


pool_answers = pool_df["answer_jp"].astype(str).tolist()

# ============================================================
# ✅ Initialize set (10 qids) + pointer
# ============================================================
if f"{NS}_set_qids" not in st.session_state:
    n = min(SET_LEN, len(pool_df))
    sample = pool_df.sample(n=n, replace=False).reset_index(drop=True)
    qids = sample["qid"].astype(str).tolist()
    st.session_state[f"{NS}_set_qids"] = qids
    st.session_state[f"{NS}_idx"] = 0
    st.session_state[f"{NS}_answers"] = {qid: {"selected": None, "ok": None, "spoken": False} for qid in qids}
    st.session_state[f"{NS}_submitted"] = False

qids: list[str] = st.session_state[f"{NS}_set_qids"]
idx: int = int(st.session_state.get(f"{NS}_idx") or 0)
idx = max(0, min(idx, len(qids) - 1))
answers = st.session_state.get(f"{NS}_answers") or {}

# ============================================================
# ✅ Progress header (1/10)
#   - '새 세트' 버튼을 진행 영역 오른쪽으로 이동(필터와 분리)
# ============================================================
progress = (idx + 1) / max(1, len(qids))

p1, p2 = st.columns([1.6, 0.6], vertical_alignment="center")
with p1:
    st.progress(progress)
    st.caption(f"진행: {idx+1}/{len(qids)}")

with p2:
    if st.button("🔄 새 세트", use_container_width=True, type="secondary", key=f"{NS}_new_set"):
        reset_set()
        st.rerun()

# ============================================================
# ✅ Current question
# ============================================================
qid = qids[idx]
_cur = pool_df[pool_df["qid"].astype(str) == str(qid)]
# ✅ 필터/상황/레벨 변경 등으로 qid가 풀에서 사라질 수 있음 → 안전 처리
if _cur.empty:
    # 가장 첫 문제로 강제 리셋
    st.session_state[f"{NS}_idx"] = 0
    qid = qids[0]
    _cur = pool_df[pool_df["qid"].astype(str) == str(qid)]
row = _cur.iloc[0].to_dict()

# options fixed per qid
opt_key = f"{NS}_opts_{qid}"
if opt_key not in st.session_state:
    st.session_state[opt_key] = build_choices(row, pool_answers)
choices: list[str] = st.session_state[opt_key]

# selected
sel_key = f"{NS}_selected_{qid}"
if sel_key not in st.session_state:
    st.session_state[sel_key] = None
selected = st.session_state.get(sel_key)

submitted_key = f"{NS}_submitted_{qid}"
if submitted_key not in st.session_state:
    st.session_state[submitted_key] = False
submitted = bool(st.session_state.get(submitted_key))

# ============================================================
# ✅ Render card
# ============================================================
with st.container(border=True):
    st.markdown(f"**상황**: {row.get('situation_kr','')}")
    st.markdown(f"**상대**: {row.get('partner_jp','')}")

    # 상대 발음(제출 전/후 모두)
    tts_button(row.get("partner_jp", ""), "🔊 상대 듣기", key=f"{qid}_partner")

    st.markdown("---")
    st.markdown("**내가 할 말(보기)**")

    # 보기 버튼(선택 없음 상태 유지)
    # 버튼은 클릭 시 selected 저장, 보기 순서는 고정(choices 리스트)
    btn_cols = st.columns(1)
    for j, opt in enumerate(choices):
        # 보기 버튼 key는 qid+index로 고정
        bkey = f"{NS}_optbtn_{qid}_{j}"
        label = opt
        pressed = st.button(label, use_container_width=True, key=bkey, disabled=submitted)
        if pressed:
            st.session_state[sel_key] = opt
            selected = opt

    # 선택 표시(제출 전)
    if not submitted:
        if selected:
            st.info(f"선택: **{selected}**")
        else:
            st.warning("보기를 하나 선택해 주세요.")

# ============================================================
# ✅ Submit / Next controls
# ============================================================
cc1, cc2, cc3 = st.columns([1, 1, 1])

with cc1:
    if st.button("이전", use_container_width=True, disabled=(idx == 0), key=f"{NS}_prev"):
        st.session_state[f"{NS}_idx"] = idx - 1
        st.rerun()

with cc2:
    can_submit = (not submitted) and bool(selected)
    if st.button("정답 제출", use_container_width=True, disabled=not can_submit, key=f"{NS}_submit"):
        st.session_state[submitted_key] = True
        submitted = True

with cc3:
    if st.button("다음", use_container_width=True, disabled=(idx >= len(qids) - 1), key=f"{NS}_next"):
        st.session_state[f"{NS}_idx"] = idx + 1
        st.rerun()

# ============================================================
# ✅ After submit
# ============================================================
if submitted:
    correct = str(row.get("answer_jp", "")).strip()
    ok = (selected == correct)
        # ============================================================
    # ✅ 오답 상세 저장 (wrong_notes) — 회화도 '단어/정답/내답' 기록
    # ============================================================
    if not ok:
        try:
            sb2 = st.session_state.get("sb_authed") or sb  # hub에서 공유되면 sb_authed 우선
            if sb2 and USER_ID:
                q_text = (str(row.get("q_jp", "")) or str(row.get("situation_kr",""))).strip()
                sb2 = get_authed_sb() or sb2

                if not sb2:

                    _wn_warn("오답 저장 실패: authed client 없음(access_token).")

                else:

                    try:

                        sb2.table("wrong_notes").insert({

                            "user_id": USER_ID,

                            "quiz_type": "talk",

                            "question": q_text if q_text else str(row.get("id", "")),

                            "correct_answer": str(correct),

                            "user_answer": str(selected),

                            "level": "talk",

                        }).execute()

                    except Exception as e:

                        _wn_warn(f"오답 저장 실패: {e}")
        except Exception:
            pass

# 저장(answers)
    answers.setdefault(qid, {})
    answers[qid]["selected"] = selected
    answers[qid]["ok"] = ok
    st.session_state[f"{NS}_answers"] = answers

    st.markdown("---")
    st.subheader("결과")

    if ok:
        st.success("정답 ✅")
    else:
        st.error("오답 ❌")

    # 상대/정답 스크립트 + 발음
    with st.container(border=True):
        st.markdown("**상대 스크립트**")
        st.write(row.get("partner_jp", ""))
        tts_button(row.get("partner_jp", ""), "🔊 상대 듣기", key=f"{qid}_partner_after")

        st.markdown("**정답 스크립트**")
        st.write(correct)
        tts_button(correct, "🔊 정답 듣기", key=f"{qid}_answer")
        # ✅ 말하기 녹음(선택) — 채점/인식 없이 '내 발화'만 남길 수 있게
        try:
            if hasattr(st, "audio_input"):
                audio = st.audio_input("내 말 녹음(선택)", key=f"{NS}_rec_{qid}")
                if audio is not None:
                    st.audio(audio)
            else:
                st.caption("현재 Streamlit 버전에서는 즉시 녹음이 지원되지 않아, 파일 업로드로 대체됩니다.")
                up = st.file_uploader("내 음성 파일 업로드(선택)", type=["wav","mp3","m4a"], key=f"{NS}_rec_up_{qid}")
                if up is not None:
                    st.audio(up)
        except Exception:
            pass


        # 납득 가능한 안내
        hint = str(row.get("hint_kr", "")).strip()
        if hint:
            st.info(hint)
        else:
            st.info("포인트: 상황에서 ‘요청/사과/확인/거절’ 중 무엇인지 먼저 잡고, 그에 맞는 톤(정중/캐주얼)을 고르면 실수가 줄어듭니다.")

    # 말하기 완료 체크 (B안)
    st.markdown("#### 🎤 말하기(체크형)")
    st.caption("정답을 보고 2~3번 따라 말한 뒤, 아래 체크를 눌러 주세요. (녹음/인식 없이 가볍게!)")

    spoken_key = f"{NS}_spoken_{qid}"
    if spoken_key not in st.session_state:
        st.session_state[spoken_key] = False

    already = bool(st.session_state.get(spoken_key))
    speak_done = st.checkbox("말하기 완료", value=already, key=f"{NS}_spoken_cb_{qid}")

    if speak_done and not already:
        st.session_state[spoken_key] = True
        # XP 지급(1문제 말하기 완료)
        award_xp(1, "회화 말하기 완료")
        st.success("+1 XP (말하기 완료)")

# ============================================================
# ✅ Set completion (10문제 모두 제출되면 자동 집계)
# ============================================================

def is_done_one(qid_: str) -> bool:
    return bool(st.session_state.get(f"{NS}_submitted_{qid_}"))


def finalize_set_if_ready():
    if not all(is_done_one(q) for q in qids):
        return

    # 중복 집계 방지
    done_key = f"{NS}_set_done"
    if st.session_state.get(done_key):
        return

    score = 0
    wrong_list: list[dict] = []
    for q in qids:
        r = pool_df[pool_df["qid"].astype(str) == str(q)].iloc[0].to_dict()
        correct = str(r.get("answer_jp", "")).strip()
        sel = st.session_state.get(f"{NS}_selected_{q}")
        ok = (sel == correct)
        score += 1 if ok else 0
        if not ok:
            wrong_list.append({"qid": q, "selected": sel, "correct": correct})

    wrong_count = len(wrong_list)

    # progress 저장(누적)
    prog = load_progress()
    talk_prog = prog.get("talk") or {}
    talk_prog["attempts"] = int(talk_prog.get("attempts") or 0) + len(qids)
    talk_prog["correct"] = int(talk_prog.get("correct") or 0) + score
    talk_prog["wrongs"] = int(talk_prog.get("wrongs") or 0) + wrong_count
    talk_prog["last_set"] = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "tag": tag,
        "level": level,
        "score": score,
        "quiz_len": len(qids),
        "wrong_count": wrong_count,
        "qids": qids,
    }
    prog["talk"] = talk_prog
    save_progress(prog)

    # DB 로그(선택)
    log_attempt(level=level, score=score, quiz_len=len(qids), wrong_count=wrong_count, wrong_list=wrong_list, tag=tag)

    # 홈 공통 streak/오늘세트 + XP(10)
    rec = st.session_state.get("hub_record_completion")
    if callable(rec):
        rec("talk", score, len(qids))

    st.session_state[done_key] = True

    st.balloons()
    st.success(f"🎉 10문제 완주! 점수: {score}/{len(qids)}  ·  오답: {wrong_count}")


finalize_set_if_ready()
