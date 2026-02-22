from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# ✅ MyPage (Redesign v5)
# - Fix #1: "Lv noun / 기타" 레거시 정규화 강화 + '기타' 최소화
# - Fix #2: 상단 CTA(오답복습/기록보기/메시지확인) 제거 → 하단 뷰 스위처만 유지
# - Fix #3: 오답 데이터 미로딩 대응:
#     - wrong_notes가 비면 wrong_note / wrongs 테이블도 순차 시도(레거시 호환)
# - Feature #4: 오답으로 시험보기(간단 퀴즈) 추가
# - Fix #5: 메시지 탭을 "리스트(좌) + 미리보기(우)" 형태로 예쁘게(Expander 제거)
#
# ⚠️ 참고:
#  - "프로 이용중입니다 / 관리자 메세지" 상단 배너는 mypage가 아니라 home.py(허브 상단)에서 출력됩니다.
# ============================================================

KST = timezone(timedelta(hours=9))
HATENA_BLUE = "#1E6BFF"

# ---------------------------
# Supabase helper
# ---------------------------
def _sb() -> Any:
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    token = st.session_state.get("access_token")
    try:
        if sb and token and hasattr(sb, "postgrest") and hasattr(sb.postgrest, "auth"):
            sb.postgrest.auth(token)
    except Exception:
        pass
    return sb

# ---------------------------
# CSS (chips only; no inline HTML cards)
# ---------------------------
def _inject_css() -> None:
    st.markdown(
        f"""
<style>
:root {{
  --ha-blue: {HATENA_BLUE};
  --ha-text: #0f172a;
  --ha-sub: #64748b;
  --ha-line: #e5e7eb;
  --ha-chip: #f1f5f9;
  --ha-soft: rgba(30,107,255,0.08);
}}

.ha-wrap {{
  max-width: 980px;
  margin: 0 auto;
  padding: 8px 8px 26px 8px;
}}

.ha-top {{
  border: 1px solid var(--ha-line);
  border-radius: 18px;
  background: #fff;
  padding: 14px 14px;
  margin: 6px 0 10px 0;
}}

.ha-brand {{
  display:flex;
  gap: 10px;
  align-items:flex-start;
}}
.ha-logo {{
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(30,107,255,0.25);
  background: var(--ha-soft);
  display:flex;
  align-items:center;
  justify-content:center;
  color: var(--ha-blue);
  font-weight: 900;
}}
.ha-title {{
  font-size: 18px;
  font-weight: 900;
  color: var(--ha-text);
  letter-spacing: -0.3px;
  line-height: 1.15;
}}
.ha-sub {{
  margin-top: 3px;
  font-size: 12px;
  color: var(--ha-sub);
}}

.ha-kpi {{
  margin-top: 12px;
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}}
.ha-kpi-item {{
  border: 1px solid var(--ha-line);
  border-radius: 16px;
  padding: 12px 12px;
  background: #fff;
}}
.ha-kpi-num {{
  font-size: 26px;
  font-weight: 900;
  color: var(--ha-text);
  line-height: 1.0;
}}
.ha-kpi-lbl {{
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  font-weight: 800;
}}

.ha-chip {{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 4px 9px;
  border-radius: 999px;
  background: var(--ha-chip);
  border: 1px solid var(--ha-line);
  font-size: 12px;
  font-weight: 800;
  color: var(--ha-sub);
  white-space: nowrap;
}}
.ha-chip b {{ color: var(--ha-text); }}

.ha-badge {{
  border: 1px solid rgba(30,107,255,0.25);
  background: rgba(30,107,255,0.08);
  color: var(--ha-blue);
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}}

.ha-inline {{
  display:flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items:center;
}}

.ha-section {{
  border: 1px solid var(--ha-line);
  border-radius: 18px;
  padding: 12px 12px;
  background: #fff;
  margin: 10px 0;
}}

@media (max-width: 720px) {{
  .ha-kpi {{ grid-template-columns: 1fr; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )

def _wrap_start() -> None:
    st.markdown('<div class="ha-wrap">', unsafe_allow_html=True)

def _wrap_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Query helpers
# ---------------------------
def _safe_select(table: str, cols: str = "*", limit: int = 200, order: Optional[str] = None, desc: bool = True) -> List[Dict[str, Any]]:
    sb = _sb()
    if not sb:
        return []
    try:
        q = sb.table(table).select(cols)
        if order:
            q = q.order(order, desc=desc)
        if limit:
            q = q.limit(limit)
        res = q.execute()
        data = getattr(res, "data", None)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _load_wrongs(limit: int = 400) -> Tuple[List[Dict[str, Any]], str]:
    # 레거시 호환: wrong_notes → wrong_note → wrongs
    cols = "id, user_id, app, level, jp_word, reading, meaning, correct_answer, user_answer, created_at"
    for table in ("wrong_notes", "wrong_note", "wrongs"):
        rows = _safe_select(table, cols=cols, limit=limit, order="created_at", desc=True)
        if rows:
            for r in rows:
                if "jp_word" not in r and "word" in r:
                    r["jp_word"] = r.get("word")
                if "correct_answer" not in r and "correct" in r:
                    r["correct_answer"] = r.get("correct")
                if "user_answer" not in r and "answer" in r:
                    r["user_answer"] = r.get("answer")
            return rows, table
    return [], "wrong_notes"

def _load_messages(limit: int = 300) -> List[Dict[str, Any]]:
    cols = "id, user_id, title, body, created_at, read_at"
    return _safe_select("user_messages", cols=cols, limit=limit, order="created_at", desc=True)

def _load_attempts(limit: int = 500) -> Tuple[List[Dict[str, Any]], str]:
    sb = _sb()
    if not sb:
        return [], "no-sb"
    candidates = [
        "id, user_id, app, pos, level, total, correct, wrong, score, created_at",
        "id, user_id, app, pos, level, quiz_len, correct_cnt, wrong_cnt, score, created_at",
        "id, user_id, app, pos, level, total_questions, correct_answers, wrong_answers, score, created_at",
        "*",
    ]
    last_err = "unknown"
    for cols in candidates:
        try:
            res = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(limit).execute()
            data = getattr(res, "data", None)
            if isinstance(data, list):
                return data, "ok"
        except Exception as e:
            last_err = str(e)
    return [], last_err

# ---------------------------
# Normalization (app/pos/level 섞임 복구)
# ---------------------------
_POS_KEYS = {"noun","n","명사","verb","v","동사","adj","adjective","형용사","adv","adverb","부사","particle","조사","conj","conjunction","접속사"}
_APP_WORD = {"word","words","vocab"}
_APP_KANJI = {"kanji","hanja"}
_APP_TALK = {"talk","conversation","speech"}

def _looks_like_pos(x: Any) -> bool:
    return str(x or "").strip().lower() in _POS_KEYS

def _looks_like_app(x: Any) -> bool:
    s = str(x or "").strip().lower()
    return s in (_APP_WORD | _APP_KANJI | _APP_TALK)

def _normalize_attempt(a: Dict[str, Any]) -> Dict[str, Any]:
    a = dict(a)
    app = (a.get("app") or "").strip()
    pos = (a.get("pos") or "").strip()
    level = (a.get("level") or "").strip()

    # app에 pos가 들어간 경우
    if _looks_like_pos(app) and not pos:
        a["pos"] = app
        a["app"] = "word"
        app = "word"

    # level에 pos가 들어간 경우 (Lv noun 방지)
    if _looks_like_pos(level) and not pos:
        a["pos"] = level
        a["level"] = ""
        level = ""

    # app이 비었는데 pos만 있다 → 단어로 간주
    if not app and pos:
        a["app"] = "word"

    # app이 이상한 값인데 pos가 있으면 → 단어로 간주 (기타 최소화)
    if app and (not _looks_like_app(app)) and (pos or _looks_like_pos(app) or _looks_like_pos(level)):
        a["app"] = "word"

    return a

# ---------------------------
# Labels
# ---------------------------
def _app_label(app: Optional[str]) -> str:
    a = (app or "").strip().lower()
    if a in _APP_WORD:
        return "단어"
    if a in _APP_KANJI:
        return "한자"
    if a in _APP_TALK:
        return "회화"
    return "단어"

def _pos_label(pos: Optional[str]) -> Optional[str]:
    p = (pos or "").strip()
    if not p:
        return None
    pl = p.lower()
    if pl in ("noun","n"):
        return "명사"
    if pl in ("verb","v"):
        return "동사"
    if pl in ("adj","adjective"):
        return "형용사"
    if pl in ("adv","adverb"):
        return "부사"
    if pl == "particle":
        return "조사"
    if pl in ("conj","conjunction"):
        return "접속사"
    return p

def _fmt_dt(s: Any) -> str:
    if not s:
        return "-"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)

def _num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return "0"

def _calc_score(a: Dict[str, Any]) -> Optional[float]:
    if a.get("score") is not None:
        try:
            return float(a["score"])
        except Exception:
            return None
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions")
    correct = a.get("correct") or a.get("correct_cnt") or a.get("correct_answers")
    try:
        if total and correct is not None:
            return round((float(correct)/float(total))*100, 1)
    except Exception:
        pass
    return None

def _calc_total_wrong(a: Dict[str, Any]) -> Tuple[Any, Any]:
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions") or "-"
    wrong = a.get("wrong") or a.get("wrong_cnt") or a.get("wrong_answers") or "-"
    return total, wrong

def _to_dt_kst(any_dt: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(any_dt).replace("Z","+00:00")).astimezone(KST)
    except Exception:
        return None

# ---------------------------
# Navigation
# ---------------------------
def _go_home() -> None:
    for key in ("hub_page","page","current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"
    st.rerun()

def _logout() -> None:
    sb = _sb()
    try:
        if sb and hasattr(sb, "auth") and hasattr(sb.auth, "sign_out"):
            sb.auth.sign_out()
    except Exception:
        pass
    for k in ("access_token","refresh_token","user_id","uid","email","sb_authed","sb","is_admin","plan","user_plan"):
        if k in st.session_state:
            st.session_state[k] = None
    _go_home()

# ---------------------------
# View switcher (single source of truth)
# ---------------------------
def _view_switcher() -> str:
    label_map = {"wrongs":"📚 오답", "records":"📈 기록", "msgs":"📩 메시지"}
    inv = {v:k for k,v in label_map.items()}
    cur = st.session_state.get("myp_view") or "wrongs"
    cur_label = label_map.get(cur, "📚 오답")
    choice = st.radio(
        "보기",
        options=list(label_map.values()),
        index=list(label_map.values()).index(cur_label),
        horizontal=True,
        label_visibility="collapsed",
        key="myp_view_radio",
    )
    st.session_state["myp_view"] = inv.get(choice, "wrongs")
    return st.session_state["myp_view"]

# ---------------------------
# Top summary (no message area)
# ---------------------------
def _render_top(wrongs: List[Dict[str, Any]], attempts: List[Dict[str, Any]]) -> None:
    wrong_total = len(wrongs)

    scores = [s for s in (_calc_score(a) for a in attempts) if s is not None]
    avg_score = round(sum(scores)/len(scores), 1) if scores else None

    now = datetime.now(KST)
    week_ago = now - timedelta(days=7)
    recent_cnt = sum(1 for a in attempts if (dt := _to_dt_kst(a.get("created_at"))) and dt >= week_ago)

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cnt = sum(1 for a in attempts if (dt := _to_dt_kst(a.get("created_at"))) and dt >= month_start)

    goal = st.session_state.get("goal_sets") or st.session_state.get("hub_goal_sets") or 20
    try:
        goal = max(1, int(goal))
    except Exception:
        goal = 20
    pct = min(100, round((month_cnt / goal) * 100, 0))

    st.markdown('<div class="ha-top">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="ha-brand">
  <div class="ha-logo">は</div>
  <div>
    <div class="ha-title">하테나일본어 · 마이페이지</div>
    <div class="ha-sub">오답 / 기록 / 메시지를 한 곳에서 정리합니다.</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    colA, colB = st.columns([7,3], vertical_alignment="center")
    with colB:
        b1, b2 = st.columns(2, gap="small")
        with b1:
            if st.button("🏠 홈", use_container_width=True, key="myp_v5_home"):
                _go_home()
        with b2:
            if st.button("로그아웃", use_container_width=True, key="myp_v5_logout"):
                _logout()

    st.markdown(
        f"""
<div class="ha-kpi">
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{_num(wrong_total)}</div>
    <div class="ha-kpi-lbl">오답</div>
  </div>
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{(str(avg_score)+'%') if avg_score is not None else '-'}</div>
    <div class="ha-kpi-lbl">평균 정답률</div>
  </div>
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{_num(recent_cnt)}</div>
    <div class="ha-kpi-lbl">최근 7일 학습</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ha-inline" style="margin-top:10px;">', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip"><b>이번 달</b> {month_cnt}/{goal}회</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip"><b>{int(pct)}%</b> 진행</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.progress(int(pct))

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Wrong quiz (simple)
# ---------------------------
def _make_wrong_quiz(wrongs: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    # quiz item: jp_word -> choose meaning among 4
    import random
    pool = [w for w in wrongs if (w.get("jp_word") and w.get("meaning"))]
    random.shuffle(pool)
    pool = pool[: max(n, 12)]
    meanings = list({w.get("meaning") for w in pool if w.get("meaning")})
    quiz = []
    for w in pool[:n]:
        correct = w.get("meaning")
        opts = [correct]
        others = [m for m in meanings if m != correct]
        random.shuffle(others)
        opts += others[:3]
        opts = list(dict.fromkeys(opts))  # unique, keep order
        while len(opts) < 4 and others:
            opts.append(others.pop())
        random.shuffle(opts)
        quiz.append(
            {
                "jp_word": w.get("jp_word"),
                "reading": w.get("reading"),
                "correct": correct,
                "options": opts[:4],
            }
        )
    return quiz

def _render_wrongs(wrongs: List[Dict[str, Any]], wrongs_table_used: str) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📚 오답</div><div class="ha-sub">필터/검색 + 오답으로 시험보기.</div>', unsafe_allow_html=True)

    if not wrongs:
        # 데이터 미로딩/테이블 불일치 가능성이 큼 → 안내 강화
        st.warning("오답 데이터를 불러오지 못했습니다. (테이블이 비었거나 RLS/테이블명이 다를 수 있어요.)")
        st.caption(f"시도한 테이블: wrong_notes → wrong_note → wrongs (현재: {wrongs_table_used})")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # 오답 시험보기
    st.markdown('<div class="ha-inline">', unsafe_allow_html=True)
    n = st.select_slider("시험 문항 수", options=[5, 10, 15, 20], value=10, key="myp_wrong_quiz_n")
    if st.button("📝 오답으로 시험보기", use_container_width=False, key="myp_wrong_quiz_start"):
        st.session_state["myp_wrong_quiz"] = _make_wrong_quiz(wrongs, n=n)
        st.session_state["myp_wrong_quiz_ans"] = {}
        st.session_state["myp_wrong_quiz_done"] = False
    st.markdown("</div>", unsafe_allow_html=True)

    quiz = st.session_state.get("myp_wrong_quiz") or []
    if quiz:
        st.divider()
        st.subheader("오답 시험")
        ans: Dict[int, str] = st.session_state.get("myp_wrong_quiz_ans") or {}
        for i, q in enumerate(quiz, start=1):
            col1, col2 = st.columns([7,3], vertical_alignment="center")
            with col1:
                st.markdown(f"**{i}. {q['jp_word']}**" + (f"  _( {q.get('reading','-')} )_" if q.get("reading") else ""))
            with col2:
                ans[i] = st.radio(
                    "선택",
                    options=q["options"],
                    index=q["options"].index(ans[i]) if i in ans and ans[i] in q["options"] else 0,
                    key=f"mq_{i}",
                    label_visibility="collapsed",
                )
        st.session_state["myp_wrong_quiz_ans"] = ans

        c1, c2 = st.columns([1,1], gap="small")
        with c1:
            if st.button("채점하기", use_container_width=True, key="myp_wrong_quiz_grade"):
                st.session_state["myp_wrong_quiz_done"] = True
        with c2:
            if st.button("시험 초기화", use_container_width=True, key="myp_wrong_quiz_reset"):
                st.session_state["myp_wrong_quiz"] = []
                st.session_state["myp_wrong_quiz_ans"] = {}
                st.session_state["myp_wrong_quiz_done"] = False
                st.rerun()

        if st.session_state.get("myp_wrong_quiz_done"):
            correct_cnt = 0
            for i, q in enumerate(quiz, start=1):
                if ans.get(i) == q["correct"]:
                    correct_cnt += 1
            st.success(f"점수: {correct_cnt}/{len(quiz)}")
            with st.expander("오답만 보기", expanded=False):
                for i, q in enumerate(quiz, start=1):
                    if ans.get(i) != q["correct"]:
                        st.markdown(f"- **{i}. {q['jp_word']}** → 정답: **{q['correct']}** / 선택: {ans.get(i)}")

    st.divider()

    # 기본 오답 리스트 (간단)
    qtxt = st.text_input("검색 (단어/뜻/발음)", value=st.session_state.get("myp_wrongs_q", ""), key="myp_wrongs_q")
    per = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100], value=20, key="myp_wrongs_per")
    filtered = []
    qq = qtxt.strip().lower()
    for w in wrongs:
        jp = (w.get("jp_word") or "").lower()
        rd = (w.get("reading") or "").lower()
        mn = (w.get("meaning") or "").lower()
        if qq and (qq not in jp and qq not in rd and qq not in mn):
            continue
        filtered.append(w)

    st.caption(f"표시: {len(filtered)}개")
    for w in filtered[:per]:
        jp = w.get("jp_word") or "-"
        rd = w.get("reading") or "-"
        mn = w.get("meaning") or "-"
        dt = _fmt_dt(w.get("created_at"))
        st.markdown(f"**{jp}**  ·  {rd}  ·  {mn}")
        st.caption(f"저장: {dt}")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Records
# ---------------------------
def _render_records(attempts: List[Dict[str, Any]], status: str) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📈 기록</div><div class="ha-sub">최근 3개 + 목록. (HTML 카드 대신 Streamlit 컴포넌트로 안전 렌더)</div>', unsafe_allow_html=True)

    if status != "ok" or not attempts:
        st.warning("학습 기록을 불러올 수 없습니다. (RLS 또는 테이블/컬럼 확인)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    attempts = [_normalize_attempt(a) for a in attempts]

    apps = st.multiselect("앱 필터", options=["단어","한자","회화"], default=st.session_state.get("myp_rec_app", []), key="myp_rec_app")
    level_q = st.text_input("레벨 검색", value=st.session_state.get("myp_rec_lvlq",""), key="myp_rec_lvlq")

    def match(a: Dict[str, Any]) -> bool:
        if apps and _app_label(a.get("app")) not in apps:
            return False
        if level_q.strip():
            if level_q.strip().lower() not in str(a.get("level") or "").lower():
                return False
        return True

    filtered = [a for a in attempts if match(a)]

    scores = [s for s in (_calc_score(a) for a in filtered[:200]) if s is not None]
    best = max(scores) if scores else None
    avg = round(sum(scores)/len(scores), 1) if scores else None

    st.markdown('<div class="ha-inline" style="margin-top:6px;">', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip">총 <b>{_num(len(filtered))}</b>회</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip">평균 <b>{(str(avg)+"%") if avg is not None else "-"}</b></span>', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip">최고 <b>{(str(best)+"%") if best is not None else "-"}</b></span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.markdown("**최근 학습(3개)**")
    for a in filtered[:3]:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = str(a.get("level") or "").strip()
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        title = app + (f" · {pos}" if pos else "") + (f" · Lv {level}" if level else "")
        c1, c2 = st.columns([7,3])
        with c1:
            st.markdown(f"**{title}**")
            st.caption(dt)
        with c2:
            st.markdown(f"점수 **{(str(score)+'%') if score is not None else '-'}**")
            st.caption(f"문항 {total} · 오답 {wrong}")

    st.divider()
    st.markdown("**목록**")
    show_n = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100, 200], value=30, key="myp_rec_n")
    for a in filtered[3:3+show_n]:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = str(a.get("level") or "").strip()
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        left = app + (f" · {pos}" if pos else "") + (f" · Lv {level}" if level else "")
        st.markdown(f"**{left}**")
        st.caption(f"{dt} · 점수 {(str(score)+'%') if score is not None else '-'} · 문항 {total} · 오답 {wrong}")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Messages (list + preview)
# ---------------------------
def _render_msgs(msgs: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📩 메시지</div><div class="ha-sub">펼침(Expander) 대신: 왼쪽 목록 + 오른쪽 미리보기.</div>', unsafe_allow_html=True)

    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # filters
    q = st.text_input("검색 (제목/내용)", value=st.session_state.get("myp_msg_q",""), key="myp_msg_q")
    only_unread = st.toggle("읽지 않음만", value=st.session_state.get("myp_msg_unread", False), key="myp_msg_unread")

    def match(m: Dict[str, Any]) -> bool:
        if only_unread and m.get("read_at"):
            return False
        if q.strip():
            qq = q.strip().lower()
            if qq not in (m.get("title") or "").lower() and qq not in (m.get("body") or "").lower():
                return False
        return True

    unread = [m for m in msgs if not m.get("read_at")]
    read = [m for m in msgs if m.get("read_at")]
    ordered = unread + read
    filtered = [m for m in ordered if match(m)]

    st.markdown('<div class="ha-inline" style="margin-top:6px;">', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip">총 <b>{_num(len(filtered))}</b>개</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="ha-chip">읽지 않음 <b>{_num(sum(1 for m in filtered if not m.get("read_at")))}</b>개</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([4,6], gap="medium")

    # selected
    sel_id = st.session_state.get("myp_msg_sel")
    if sel_id is None and filtered:
        st.session_state["myp_msg_sel"] = filtered[0].get("id")
        sel_id = st.session_state["myp_msg_sel"]

    with left:
        st.markdown("**목록**")
        for m in filtered[:50]:
            mid = m.get("id")
            title = m.get("title") or "메시지"
            dt = _fmt_dt(m.get("created_at"))
            is_unread = not m.get("read_at")
            prefix = "🔵 " if is_unread else "⚪ "
            active = (mid == sel_id)
            label = f"{prefix}{title}"
            if st.button(label, use_container_width=True, key=f"msg_pick_{mid}"):
                st.session_state["myp_msg_sel"] = mid
                st.rerun()
            st.caption(dt)
            if active:
                st.markdown('<span class="ha-badge">선택됨</span>', unsafe_allow_html=True)

    with right:
        st.markdown("**내용**")
        current = next((m for m in filtered if m.get("id") == sel_id), None)
        if not current:
            st.info("메시지를 선택하세요.")
        else:
            title = current.get("title") or "메시지"
            body = current.get("body") or ""
            dt = _fmt_dt(current.get("created_at"))
            is_unread = not current.get("read_at")

            st.markdown(f"### {title}")
            st.caption(dt)
            if is_unread:
                st.markdown('<span class="ha-badge">읽지 않음</span>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(body)

            # mark as read
            if is_unread:
                sb = _sb()
                if sb and st.button("읽음 처리", key="msg_mark_read", use_container_width=False):
                    try:
                        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", sel_id).execute()
                        st.success("읽음 처리 완료")
                        st.rerun()
                    except Exception:
                        st.warning("읽음 처리 실패 (RLS 확인)")

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# Public entrypoint
# ---------------------------
def render() -> None:
    _inject_css()
    _wrap_start()

    wrongs, wrongs_table = _load_wrongs(limit=400)
    msgs = _load_messages(limit=300)
    attempts, status = _load_attempts(limit=500)
    attempts_ok = [_normalize_attempt(a) for a in attempts] if status == "ok" else []

    _render_top(wrongs, attempts_ok)

    view = _view_switcher()

    if view == "records":
        _render_records(attempts_ok, "ok" if attempts_ok else status)
    elif view == "msgs":
        _render_msgs(msgs)
    else:
        _render_wrongs(wrongs, wrongs_table)

    _wrap_end()
