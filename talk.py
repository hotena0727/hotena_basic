# talk.py (v27) - 1문제 집중형 + 말하기 완료 체크(B)
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, date
import random
import hashlib

import pandas as pd
import streamlit as st
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
# ✅ Filters (tag/level)
# ============================================================
all_tags = [t for t in DF["tag"].astype(str).unique().tolist() if t]
tag_options = [t for t in ["daily", "business", "call", "interview", "travel", "shopping", "food", "emergency"] if t in all_tags]
if not tag_options:
    tag_options = all_tags

c1, c2, c3 = st.columns([1.4, 1, 1])
with c1:
    tag = st.selectbox(
        "상황 선택",
        options=tag_options,
        format_func=lambda x: TAG_LABELS.get(x, x),
        key=f"{NS}_tag",
    )

with c2:
    levels_in_data = [lv for lv in ["n5", "n4", "n3"] if lv in DF["level"].unique().tolist()]
    if not levels_in_data:
        levels_in_data = ["n5", "n4", "n3"]
    level = st.selectbox(
        "레벨",
        options=levels_in_data,
        format_func=lambda x: LEVEL_LABELS.get(x, x.upper()),
        key=f"{NS}_level",
    )

with c3:
    if st.button("새 세트(10문제)", use_container_width=True, key=f"{NS}_new_set"):
        reset_set()
        st.rerun()

pool_df = DF[(DF["tag"] == tag) & (DF["level"] == level)].copy().reset_index(drop=True)
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
# ============================================================
progress = (idx + 1) / max(1, len(qids))
st.progress(progress)
st.caption(f"진행: {idx+1}/{len(qids)}")

# ============================================================
# ✅ Current question
# ============================================================
qid = qids[idx]
row = pool_df[pool_df["qid"].astype(str) == str(qid)].iloc[0].to_dict()

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


# ------------------------------
# ✅ Soft Set Complete Card (A안)
# ------------------------------
if idx >= len(qids):
    results = st.session_state.get(f"{NS}_results", {}) or {}
    total = len(qids)
    correct_n = sum(1 for q in qids if results.get(str(q), {}).get("correct") is True)
    wrong_qids = [str(q) for q in qids if results.get(str(q), {}).get("correct") is False]
    acc = int(round((correct_n / total) * 100)) if total else 0

    st.markdown(
        f"""
<div style="border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:14px 14px 12px;
            background: rgba(0,0,0,0.02); box-shadow:0 8px 24px rgba(0,0,0,0.04);">
  <div style="font-size:1.2rem; font-weight:800; margin-bottom:6px;">🎉 1세트 완료</div>
  <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
    <div style="padding:6px 10px; border-radius:999px; background:#fff; border:1px solid rgba(0,0,0,0.08); font-weight:700;">
      점수 {correct_n}/{total}
    </div>
    <div style="padding:6px 10px; border-radius:999px; background:#fff; border:1px solid rgba(0,0,0,0.08); font-weight:700;">
      정답률 {acc}%
    </div>
    <div style="padding:6px 10px; border-radius:999px; background:#fff; border:1px solid rgba(0,0,0,0.08);">
      오답 {len(wrong_qids)}개
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if acc == 100:
        st.success("완벽합니다. 다음 세트도 이 페이스로 가시죠 🔥")
    elif acc >= 80:
        st.info("좋습니다. 오답만 한 번 더 잡고 넘어가면 더 탄탄해져요.")
    else:
        st.warning("괜찮습니다. 오답만 한 번 돌리면 금방 올라갑니다.")

    if wrong_qids:
        with st.expander("오답 빠른 확인", expanded=False):
            for n, q in enumerate(wrong_qids, 1):
                row = pool_df[pool_df["qid"].astype(str) == str(q)]
                st.markdown(f"**{n}. QID {q}**")
                if len(row) > 0:
                    r0 = row.iloc[0]
                    partner = str(r0.get("partner_jp","")).strip()
                    ans = str(r0.get("answer_jp","")).strip()
                    if partner:
                        st.write(f"상대: {partner}")
                    if ans:
                        st.write(f"정답: {ans}")

    c1, c2, c3 = st.columns([0.42, 0.33, 0.25])
    with c1:
        if st.button("➡️ 다음 세트", use_container_width=True, type="primary"):
            start_new_set()
            st.rerun()
    with c2:
        if st.button("🔁 오답만", disabled=(len(wrong_qids)==0), use_container_width=True):
            start_wrong_set(wrong_qids) if "start_wrong_set" in globals() else start_new_set()
            st.rerun()
    with c3:
        if st.button("🏠 홈", use_container_width=True):
            try:
                st.query_params["p"] = "home"
            except Exception:
                pass
            st.rerun()

    st.stop()
