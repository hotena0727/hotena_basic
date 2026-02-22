from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# ✅ MyPage (AdminStyle Clean • Hatena Blue • No Top Msg Dup)
# - 목적: "개발자 느낌" 제거 + 관리자 탭과 같은 UI 언어로 통일
# - 위계: 숫자(KPI) → 흐름(상태) → 행동(CTA) → 상세(카드)
# - 데이터: wrong_notes / quiz_attempts(있으면) / user_messages
# ============================================================


# ---------------------------
# Supabase helpers
# ---------------------------
def _sb() -> Any:
    """Return Supabase client with JWT bound for RLS (if available)."""
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    token = st.session_state.get("access_token")
    try:
        # postgrest-python supports auth(token)
        if sb and token and hasattr(sb, "postgrest") and hasattr(sb.postgrest, "auth"):
            sb.postgrest.auth(token)
    except Exception:
        pass
    return sb


def _uid() -> Optional[str]:
    uid = st.session_state.get("user_id") or st.session_state.get("uid")
    if uid:
        return str(uid)
    try:
        sb = _sb()
        if sb and hasattr(sb, "auth"):
            u = sb.auth.get_user()
            if u and getattr(u, "user", None) and getattr(u.user, "id", None):
                return str(u.user.id)
    except Exception:
        pass
    return None


# ---------------------------
# UI / CSS
# ---------------------------
HATENA_BLUE = "#1E6BFF"  # ✅ 현재 하테나 블루(필요 시 값만 교체)

def _inject_css() -> None:
    st.markdown(
        f"""
<style>
:root {{
  --ha-blue: {HATENA_BLUE};
  --ha-text: #0f172a;
  --ha-sub: #64748b;
  --ha-line: #e5e7eb;
  --ha-bg: #ffffff;
  --ha-chip: #f1f5f9;
}}

.ha-wrap {{
  max-width: 980px;
  margin: 0 auto;
  padding: 10px 8px 30px 8px;
}}

.ha-topbar {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding: 2px 0 14px 0;
}}

.ha-title {{
  font-size: 20px;
  font-weight: 800;
  color: var(--ha-text);
  letter-spacing: -0.3px;
}}
.ha-sub {{
  margin-top: 2px;
  font-size: 12px;
  color: var(--ha-sub);
}}

.ha-actions {{
  display:flex;
  gap:8px;
  align-items:center;
}}

.ha-btn {{
  border: 1px solid var(--ha-line);
  background: #fff;
  color: var(--ha-text);
  border-radius: 999px;
  padding: 7px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}}
.ha-btn-primary {{
  border: 1px solid rgba(30,107,255,0.35);
  background: rgba(30,107,255,0.10);
  color: var(--ha-blue);
}}

.ha-section {{
  border: 1px solid var(--ha-line);
  border-radius: 16px;
  padding: 14px 14px;
  background: var(--ha-bg);
  margin: 10px 0;
}}

.ha-kpi {{
  display:grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}}
.ha-kpi-item {{
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 12px 12px;
  background: #fff;
}}
.ha-kpi-num {{
  font-size: 30px;
  font-weight: 900;
  color: var(--ha-text);
  line-height: 1.0;
}}
.ha-kpi-lbl {{
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  font-weight: 700;
}}

.ha-progress-row {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-top: 8px;
}}
.ha-progress {{
  width: 100%;
  height: 10px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow:hidden;
  border: 1px solid var(--ha-line);
}}
.ha-progress > div {{
  height: 100%;
  background: var(--ha-blue);
  width: 0%;
}}

.ha-cta {{
  display:flex;
  justify-content:center;
  gap: 10px;
  margin-top: 10px;
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
  font-weight: 700;
  color: var(--ha-sub);
}}
.ha-chip b {{ color: var(--ha-text); }}

.ha-card {{
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 12px 12px;
  background: #fff;
  margin: 8px 0;
}}
.ha-card-title {{
  font-weight: 900;
  color: var(--ha-text);
  letter-spacing: -0.2px;
}}
.ha-meta {{
  margin-top: 6px;
  font-size: 12px;
  color: var(--ha-sub);
  display:flex;
  flex-wrap:wrap;
  gap: 8px;
}}
.ha-dot {{
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--ha-blue);
  display:inline-block;
  margin-right: 6px;
  opacity: 0.8;
}}

@media (max-width: 720px) {{
  .ha-kpi {{ grid-template-columns: 1fr; }}
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _center_wrap_start() -> None:
    st.markdown('<div class="ha-wrap">', unsafe_allow_html=True)


def _center_wrap_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Data loaders (RLS-safe)
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


def _load_wrongs(limit: int = 200) -> List[Dict[str, Any]]:
    # wrong_notes: user_id RLS로 본인 것만
    cols = "id, user_id, app, level, jp_word, reading, meaning, correct_answer, user_answer, created_at"
    rows = _safe_select("wrong_notes", cols=cols, limit=limit, order="created_at", desc=True)
    # 유연 처리: 컬럼명이 다를 수 있으니 키 보정
    for r in rows:
        if "jp_word" not in r and "word" in r:
            r["jp_word"] = r.get("word")
        if "correct_answer" not in r and "correct" in r:
            r["correct_answer"] = r.get("correct")
        if "user_answer" not in r and "answer" in r:
            r["user_answer"] = r.get("answer")
    return rows


def _load_messages(limit: int = 200) -> List[Dict[str, Any]]:
    cols = "id, user_id, title, body, created_at, read_at"
    rows = _safe_select("user_messages", cols=cols, limit=limit, order="created_at", desc=True)
    return rows


def _load_attempts(limit: int = 300) -> Tuple[List[Dict[str, Any]], str]:
    """
    quiz_attempts 스키마가 환경마다 달라서,
    몇 가지 대표 컬럼 세트를 순서대로 시도합니다.
    """
    sb = _sb()
    if not sb:
        return [], "no-sb"

    candidates = [
        "id, user_id, app, level, total, correct, wrong, score, created_at",
        "id, user_id, app, level, quiz_len, correct_cnt, wrong_cnt, score, created_at",
        "id, user_id, app, level, total_questions, correct_answers, wrong_answers, score, created_at",
        "*",
    ]
    last_err = "unknown"
    for cols in candidates:
        try:
            q = sb.table("quiz_attempts").select(cols).order("created_at", desc=True).limit(limit)
            res = q.execute()
            data = getattr(res, "data", None)
            if isinstance(data, list):
                return data, "ok"
        except Exception as e:
            last_err = str(e)
            continue
    return [], last_err


# ---------------------------
# Formatting helpers
# ---------------------------
def _fmt_dt(s: Any) -> str:
    if not s:
        return "-"
    try:
        # s may be ISO string
        if isinstance(s, str):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif isinstance(s, datetime):
            dt = s
        else:
            return str(s)
        # show in Asia/Seoul friendly without importing pytz
        return dt.astimezone(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(s)


def _app_label(app: Optional[str]) -> str:
    a = (app or "").lower().strip()
    if a in ("word", "words", "vocab"):
        return "단어"
    if a in ("kanji", "hanja"):
        return "한자"
    if a in ("talk", "conversation", "speech"):
        return "회화"
    return (app or "기타")


def _num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return "0"


# ---------------------------
# Sections (Admin-style)
# ---------------------------
def _kpi_and_flow(wrongs: List[Dict[str, Any]], attempts: List[Dict[str, Any]], msgs: List[Dict[str, Any]]) -> None:
    # KPI 계산
    wrong_total = len(wrongs)
    unread = sum(1 for m in msgs if not m.get("read_at"))
    # 평균점수(가능한 경우)
    scores = []
    for a in attempts:
        sc = a.get("score")
        if sc is None:
            # score 없으면 correct/total로 계산 시도
            total = a.get("total") or a.get("quiz_len") or a.get("total_questions")
            correct = a.get("correct") or a.get("correct_cnt") or a.get("correct_answers")
            try:
                if total and correct is not None:
                    sc = round((float(correct) / float(total)) * 100, 1)
            except Exception:
                sc = None
        if sc is not None:
            try:
                scores.append(float(sc))
            except Exception:
                pass
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # 최근 7일 학습 횟수
    now = datetime.now(timezone(timedelta(hours=9)))
    week_ago = now - timedelta(days=7)
    recent_cnt = 0
    for a in attempts:
        ca = a.get("created_at")
        try:
            dt = datetime.fromisoformat(str(ca).replace("Z", "+00:00"))
            if dt.astimezone(timezone(timedelta(hours=9))) >= week_ago:
                recent_cnt += 1
        except Exception:
            continue

    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown(
        '<div class="ha-title">마이페이지</div>'
        '<div class="ha-sub">오답 · 학습 기록 · 받은 메시지를 한 곳에서 정리합니다.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="ha-kpi">
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{_num(wrong_total)}</div>
    <div class="ha-kpi-lbl">오답</div>
  </div>
  <div class="ha-kpi-item">
    <div class="ha-kpi-num">{(str(avg_score) + '%') if avg_score is not None else '-'}</div>
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

    # 흐름(이번 달 진행) — “정의”를 단순화: 이번 달 학습횟수 / 목표(기본 20)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cnt = 0
    for a in attempts:
        ca = a.get("created_at")
        try:
            dt = datetime.fromisoformat(str(ca).replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=9)))
            if dt >= month_start:
                month_cnt += 1
        except Exception:
            continue
    # 목표는 홈허브의 goal_sets(또는 20)을 따름. 없으면 20.
    goal = st.session_state.get("goal_sets") or st.session_state.get("hub_goal_sets") or 20
    try:
        goal = max(1, int(goal))
    except Exception:
        goal = 20
    pct = min(100, round((month_cnt / goal) * 100, 0)) if goal else 0

    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ha-sub"><b>이번 달 학습 흐름</b> · {month_cnt}/{goal}회</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="ha-progress-row">
  <div class="ha-progress"><div style="width:{pct}%;"></div></div>
  <div class="ha-chip"><b>{int(pct)}%</b> 진행</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # 행동(CTA)
    st.markdown('<div class="ha-cta">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1], gap="small")
    with c1:
        if st.button("🧪 TOP10 재시험", use_container_width=True):
            # 기존 mypage 구조에서 시험 화면이 있다면 그 라우트로 넘김
            st.session_state["mypage_view"] = "top10"
            st.rerun()
    with c2:
        if st.button("📚 오답 복습하기", use_container_width=True):
            st.session_state["mypage_view"] = "wrongs_focus"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # 메시지 안내는 중복 제거: KPI에 읽지않음만 뱃지로 조용히
    if unread:
        st.caption(f"읽지 않은 메시지 {unread}개가 있습니다.")
    st.markdown("</div>", unsafe_allow_html=True)


def _section_wrongs(wrongs: List[Dict[str, Any]], focus: bool = False) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📚 오답카드</div><div class="ha-sub">틀린 문제는 자동으로 쌓이고, 반복 오답은 우선 복습을 추천합니다.</div>', unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답 상세가 없습니다. (앞으로 틀린 문제는 자동으로 오답카드에 쌓입니다.)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # 반복 오답 카운트(같은 jp_word 기준) — 간단 버전
    counts: Dict[str, int] = {}
    for w in wrongs:
        k = (w.get("jp_word") or "").strip()
        if not k:
            continue
        counts[k] = counts.get(k, 0) + 1

    # 추천(3회 이상)
    repeat = [w for w in wrongs if counts.get((w.get("jp_word") or "").strip(), 0) >= 3]
    if repeat:
        st.markdown('<div class="ha-sub"><b>🔥 반복 오답</b> (3회 이상)</div>', unsafe_allow_html=True)
        for w in repeat[:5]:
            _wrong_card(w, counts)
        st.divider()

    st.markdown('<div class="ha-sub"><b>최근 오답</b></div>', unsafe_allow_html=True)
    show_n = 20 if (focus or st.session_state.get("mypage_view") == "wrongs_focus") else 10
    for w in wrongs[:show_n]:
        _wrong_card(w, counts)

    st.markdown("</div>", unsafe_allow_html=True)


def _wrong_card(w: Dict[str, Any], counts: Dict[str, int]) -> None:
    jp = w.get("jp_word") or "-"
    ca = _fmt_dt(w.get("created_at"))
    app = _app_label(w.get("app"))
    level = w.get("level") or "-"
    correct = w.get("correct_answer") or "-"
    ua = w.get("user_answer") or "-"
    c = counts.get((w.get("jp_word") or "").strip(), 0)

    badges = [f"{app}", f"Lv {level}" if level != "-" else None, ca]
    badges = [b for b in badges if b]

    badge_str = " · ".join(badges)
    rep = f" · {c}회" if c >= 3 else ""

    st.markdown(
        f"""
<div class="ha-card">
  <div class="ha-card-title">{jp}</div>
  <div class="ha-meta">
    <span class="ha-chip">{badge_str}{rep}</span>
  </div>
  <div class="ha-meta">
    <span>정답 <b>{correct}</b></span>
    <span>내답 <b>{ua}</b></span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _section_records(attempts: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📈 학습 기록</div><div class="ha-sub">최근 학습을 카드 형태로 정리합니다.</div>', unsafe_allow_html=True)

    if not attempts:
        st.warning("학습 기록을 불러올 수 없습니다. (RLS 또는 테이블 확인)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    for a in attempts[:15]:
        app = _app_label(a.get("app"))
        level = a.get("level") or "-"
        dt = _fmt_dt(a.get("created_at"))

        # score 우선, 없으면 correct/total로 계산
        score = a.get("score")
        if score is None:
            total = a.get("total") or a.get("quiz_len") or a.get("total_questions")
            correct = a.get("correct") or a.get("correct_cnt") or a.get("correct_answers")
            try:
                if total and correct is not None:
                    score = round((float(correct) / float(total)) * 100, 1)
            except Exception:
                score = None

        # 세부 숫자
        total = a.get("total") or a.get("quiz_len") or a.get("total_questions") or "-"
        wrong = a.get("wrong") or a.get("wrong_cnt") or a.get("wrong_answers") or "-"

        st.markdown(
            f"""
<div class="ha-card">
  <div class="ha-card-title">{app} · Lv {level}</div>
  <div class="ha-meta">
    <span class="ha-chip">{dt}</span>
    <span class="ha-chip">점수 <b>{(str(score)+'%') if score is not None else '-'}</b></span>
    <span class="ha-chip">문항 <b>{total}</b></span>
    <span class="ha-chip">오답 <b>{wrong}</b></span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _section_messages(msgs: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📩 받은 메시지</div><div class="ha-sub">관리자가 보낸 안내/공지 메시지입니다.</div>', unsafe_allow_html=True)

    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # 필터: 읽지않음 우선
    unread = [m for m in msgs if not m.get("read_at")]
    read = [m for m in msgs if m.get("read_at")]
    ordered = unread + read

    sb = _sb()

    for m in ordered[:30]:
        title = m.get("title") or "메시지"
        body = m.get("body") or ""
        dt = _fmt_dt(m.get("created_at"))
        is_unread = not m.get("read_at")
        dot = '<span class="ha-dot"></span>' if is_unread else ""
        chip = "읽지 않음" if is_unread else "읽음"

        st.markdown(
            f"""
<div class="ha-card">
  <div class="ha-card-title">{dot}{title}</div>
  <div class="ha-meta">
    <span class="ha-chip">{dt}</span>
    <span class="ha-chip">{chip}</span>
  </div>
  <div style="margin-top:8px; color: var(--ha-text); font-size: 14px; line-height: 1.55;">
    {body.replace('<', '&lt;').replace('>', '&gt;').replace('\n','<br>')}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        # 읽음 처리 버튼(읽지 않은 메시지에만)
        if is_unread and sb:
            col1, col2, col3 = st.columns([1, 1, 8])
            with col1:
                if st.button("읽음", key=f"msg_read_{m.get('id')}"):
                    try:
                        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", m["id"]).execute()
                        st.rerun()
                    except Exception:
                        st.warning("읽음 처리에 실패했습니다. (RLS 확인)")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Navigation actions (Home / Logout)
# ---------------------------
def _go_home() -> None:
    # home.py에서 hub_page로 라우팅하는 구조를 최대한 존중
    for key in ("hub_page", "page", "current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"
    st.session_state["mypage_view"] = "default"
    st.rerun()


def _logout() -> None:
    # 세션 토큰 제거 + 가능하면 supabase sign_out
    sb = _sb()
    try:
        if sb and hasattr(sb, "auth") and hasattr(sb.auth, "sign_out"):
            sb.auth.sign_out()
    except Exception:
        pass

    for k in [
        "access_token", "refresh_token", "user_id", "uid", "email",
        "sb_authed", "sb", "is_admin", "plan", "user_plan"
    ]:
        if k in st.session_state:
            st.session_state[k] = None
    # 홈으로
    for key in ("hub_page", "page", "current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"
    st.rerun()


# ---------------------------
# Public entrypoint
# ---------------------------
def render() -> None:
    _inject_css()
    _center_wrap_start()

    # Topbar (centered)
    left, mid, right = st.columns([2, 5, 2], vertical_alignment="center")
    with mid:
        st.markdown(
            '<div style="text-align:center;">'
            '<div class="ha-title">하테나일본어 · 마이페이지</div>'
            '<div class="ha-sub">오답 · 기록 · 메시지를 정돈된 형태로 확인하세요.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with right:
        # 작은 버튼 2개
        c1, c2 = st.columns(2, gap="small")
        with c1:
            if st.button("🏠 홈", key="myp_home_btn"):
                _go_home()
        with c2:
            if st.button("로그아웃", key="myp_logout_btn"):
                _logout()

    # Data
    wrongs = _load_wrongs(limit=300)
    msgs = _load_messages(limit=200)
    attempts, attempts_status = _load_attempts(limit=300)

    # KPI + Flow
    _kpi_and_flow(wrongs, attempts if attempts_status == "ok" else [], msgs)

    # Sections (Info-dense but clean)
    # View routing for CTA
    view = st.session_state.get("mypage_view", "default")
    if view == "top10":
        st.markdown('<div class="ha-section">', unsafe_allow_html=True)
        st.markdown('<div class="ha-title">🧪 TOP10 재시험</div><div class="ha-sub">현재 버전에서는 홈허브/기존 시험 화면으로 연결을 권장합니다.</div>', unsafe_allow_html=True)
        st.info("TOP10 재시험은 기존 시험 화면(단어/한자/회화)로 연결되도록 홈에서 진행하는 방식이 가장 안정적입니다.")
        if st.button("🏠 홈으로 돌아가기", use_container_width=True):
            _go_home()
        st.markdown("</div>", unsafe_allow_html=True)

    # 오답 섹션
    _section_wrongs(wrongs, focus=(view == "wrongs_focus"))

    # 기록 섹션
    if attempts_status == "ok":
        _section_records(attempts)
    else:
        _section_records([])

    # 메시지 섹션
    _section_messages(msgs)

    _center_wrap_end()
