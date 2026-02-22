from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# ✅ MyPage (Redesign v3 • Hatena Blue • No Msg Dup • app+pos)
# - C안 적용: 기록 "최근 카드" 3개만 (중복감 최소화)
# - 정석(방법2) 대응: quiz_attempts에 app + pos 분리 저장을 전제로 표시
#   - app: word/kanji/talk
#   - pos: noun/verb/adj/... (선택)
# - 호환: 예전 데이터에서 app에 noun/verb...가 들어간 경우 자동 보정
# - 상단: 메시지(관리자 메세지) 중복 뱃지/영역 제거 → 메시지 탭에서만 확인
# ============================================================

HATENA_BLUE = "#1E6BFF"

# ---------------------------
# Supabase helpers
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
# UI / CSS
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
  --ha-bg: #ffffff;
  --ha-chip: #f1f5f9;
  --ha-soft: rgba(30,107,255,0.08);
}}

.ha-wrap {{
  max-width: 980px;
  margin: 0 auto;
  padding: 6px 8px 26px 8px;
}}

.ha-top {{
  border: 1px solid var(--ha-line);
  border-radius: 18px;
  background: var(--ha-bg);
  padding: 14px 14px;
  margin: 8px 0 10px 0;
}}

.ha-topbar {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
}}

.ha-brand {{
  display:flex;
  align-items:flex-start;
  gap: 10px;
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

.ha-progress-row {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-top: 10px;
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

.ha-row {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  flex-wrap: wrap;
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
  background: var(--ha-bg);
  margin: 10px 0;
}}

.ha-card {{
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 10px 10px;
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
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--ha-blue);
  display:inline-block;
  margin-right: 6px;
  opacity: 0.85;
}}

/* mini calendar */
.ha-week {{
  margin-top: 10px;
  border: 1px solid var(--ha-line);
  border-radius: 16px;
  padding: 10px 10px;
  background: #fff;
}}
.ha-week-head {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap: 10px;
  margin-bottom: 8px;
}}
.ha-week-title {{
  font-size: 13px;
  font-weight: 900;
  color: var(--ha-text);
}}
.ha-week-grid {{
  display:grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 8px;
}}
.ha-day {{
  border: 1px solid var(--ha-line);
  border-radius: 14px;
  padding: 8px 6px;
  text-align:center;
  background: #fff;
}}
.ha-day-top {{
  font-size: 11px;
  color: var(--ha-sub);
  font-weight: 900;
}}
.ha-day-num {{
  margin-top: 4px;
  font-size: 16px;
  font-weight: 900;
  color: var(--ha-text);
}}
.ha-day-sub {{
  margin-top: 2px;
  font-size: 11px;
  color: var(--ha-sub);
  font-weight: 800;
}}

@media (max-width: 720px) {{
  .ha-kpi {{ grid-template-columns: 1fr; }}
  .ha-week-grid {{ gap: 6px; }}
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


def _load_wrongs(limit: int = 400) -> List[Dict[str, Any]]:
    cols = "id, user_id, app, level, jp_word, reading, meaning, correct_answer, user_answer, created_at"
    rows = _safe_select("wrong_notes", cols=cols, limit=limit, order="created_at", desc=True)
    for r in rows:
        if "jp_word" not in r and "word" in r:
            r["jp_word"] = r.get("word")
        if "correct_answer" not in r and "correct" in r:
            r["correct_answer"] = r.get("correct")
        if "user_answer" not in r and "answer" in r:
            r["user_answer"] = r.get("answer")
    return rows


def _load_messages(limit: int = 300) -> List[Dict[str, Any]]:
    cols = "id, user_id, title, body, created_at, read_at"
    return _safe_select("user_messages", cols=cols, limit=limit, order="created_at", desc=True)


def _load_attempts(limit: int = 500) -> Tuple[List[Dict[str, Any]], str]:
    """
    ✅ 방법2 대응: pos 컬럼이 있으면 같이 가져옴
    """
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
# Formatting + normalization
# ---------------------------
_POS_LIKE = {
    "noun", "n", "명사",
    "verb", "v", "동사",
    "adj", "adjective", "형용사",
    "adv", "adverb", "부사",
    "particle", "조사",
    "conj", "conjunction", "접속사",
}


def _normalize_attempt(a: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ 호환 처리:
    - 예전 데이터에서 app='noun' 같은 값이면 app='word'로 보고 pos에 옮김
    - pos가 있으면 그대로 사용
    """
    app_raw = (a.get("app") or "").strip()
    pos_raw = (a.get("pos") or "").strip()

    app_l = app_raw.lower()
    pos_l = pos_raw.lower()

    # app에 pos가 들어간 경우
    if app_l in _POS_LIKE and not pos_raw:
        a = dict(a)
        a["pos"] = app_raw
        a["app"] = "word"
        return a

    # pos가 비었고, app이 단어앱인데 level/기록에서 'noun' 등 힌트가 다른 컬럼에 있을 수는 없음 → 여기까지만
    return a


def _fmt_dt(s: Any) -> str:
    if not s:
        return "-"
    try:
        if isinstance(s, str):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif isinstance(s, datetime):
            dt = s
        else:
            return str(s)
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


def _pos_label(pos: Optional[str]) -> Optional[str]:
    p = (pos or "").strip()
    if not p:
        return None
    pl = p.lower()
    # 영어 → 한글
    if pl in ("noun", "n"):
        return "명사"
    if pl in ("verb", "v"):
        return "동사"
    if pl in ("adj", "adjective"):
        return "형용사"
    if pl in ("adv", "adverb"):
        return "부사"
    if pl in ("particle",):
        return "조사"
    if pl in ("conj", "conjunction"):
        return "접속사"
    # 이미 한글이면 그대로
    return p


def _num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except Exception:
        return "0"


def _calc_score(a: Dict[str, Any]) -> Optional[float]:
    score = a.get("score")
    if score is not None:
        try:
            return float(score)
        except Exception:
            return None
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions")
    correct = a.get("correct") or a.get("correct_cnt") or a.get("correct_answers")
    try:
        if total and correct is not None:
            return round((float(correct) / float(total)) * 100, 1)
    except Exception:
        pass
    return None


def _calc_total_wrong(a: Dict[str, Any]) -> Tuple[Any, Any]:
    total = a.get("total") or a.get("quiz_len") or a.get("total_questions") or "-"
    wrong = a.get("wrong") or a.get("wrong_cnt") or a.get("wrong_answers") or "-"
    return total, wrong


def _to_dt_kst(any_dt: Any) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(str(any_dt).replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=9)))
    except Exception:
        return None


# ---------------------------
# Navigation
# ---------------------------
def _go_home() -> None:
    for key in ("hub_page", "page", "current_page"):
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

    for k in [
        "access_token", "refresh_token", "user_id", "uid", "email",
        "sb_authed", "sb", "is_admin", "plan", "user_plan"
    ]:
        if k in st.session_state:
            st.session_state[k] = None

    for key in ("hub_page", "page", "current_page"):
        if key in st.session_state:
            st.session_state[key] = "home"
    st.rerun()


# ---------------------------
# Mini widget
# ---------------------------
def _week_counts(attempts: List[Dict[str, Any]]) -> Tuple[List[datetime], List[int]]:
    now = datetime.now(timezone(timedelta(hours=9)))
    days = [(now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0) for i in range(6, -1, -1)]
    counts = [0] * 7
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if not dt:
            continue
        d0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for i, day in enumerate(days):
            if d0 == day:
                counts[i] += 1
                break
    return days, counts


def _render_week_widget(attempts: List[Dict[str, Any]]) -> None:
    days, counts = _week_counts(attempts)
    mx = max(counts) if counts else 0
    dow_kr = ["월", "화", "수", "목", "금", "토", "일"]

    blocks = []
    for day, c in zip(days, counts):
        wd = dow_kr[day.weekday()]
        if mx <= 0:
            bg = "rgba(30,107,255,0.06)"
            bd = "rgba(229,231,235,1)"
        else:
            alpha = 0.08 + (0.20 * (c / mx)) if c > 0 else 0.06
            bg = f"rgba(30,107,255,{alpha:.3f})"
            bd = "rgba(30,107,255,0.22)" if c > 0 else "rgba(229,231,235,1)"
        blocks.append(
            f"""
<div class="ha-day" style="background:{bg}; border-color:{bd};">
  <div class="ha-day-top">{wd}</div>
  <div class="ha-day-num">{day.day}</div>
  <div class="ha-day-sub">{c}회</div>
</div>
"""
        )

    total = sum(counts)
    streak = 0
    for c in reversed(counts):
        if c > 0:
            streak += 1
        else:
            break

    st.markdown(
        f"""
<div class="ha-week">
  <div class="ha-week-head">
    <div class="ha-week-title">최근 7일 학습</div>
    <div class="ha-inline">
      <span class="ha-chip">총 <b>{total}</b>회</span>
      <span class="ha-chip">연속 <b>{streak}</b>일</span>
    </div>
  </div>
  <div class="ha-week-grid">
    {''.join(blocks)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_filter_chips(title: str, key: str) -> List[str]:
    options = ["단어", "한자", "회화", "기타"]
    selected = st.multiselect(title, options=options, default=st.session_state.get(key, []), key=key)
    if selected:
        chips = " ".join([f'<span class="ha-badge">{s}</span>' for s in selected])
        st.markdown(f'<div class="ha-inline" style="margin-top:6px;">{chips}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ha-inline" style="margin-top:6px;"><span class="ha-chip">전체</span></div>', unsafe_allow_html=True)
    return selected


# ---------------------------
# Top summary (NO messages duplication)
# ---------------------------
def _render_top_summary(wrongs: List[Dict[str, Any]], attempts: List[Dict[str, Any]]) -> None:
    wrong_total = len(wrongs)

    scores = []
    for a in attempts:
        sc = _calc_score(a)
        if sc is not None:
            scores.append(sc)
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    now = datetime.now(timezone(timedelta(hours=9)))
    week_ago = now - timedelta(days=7)
    recent_cnt = 0
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if dt and dt >= week_ago:
            recent_cnt += 1

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_cnt = 0
    for a in attempts:
        dt = _to_dt_kst(a.get("created_at"))
        if dt and dt >= month_start:
            month_cnt += 1

    goal = st.session_state.get("goal_sets") or st.session_state.get("hub_goal_sets") or 20
    try:
        goal = max(1, int(goal))
    except Exception:
        goal = 20
    pct = min(100, round((month_cnt / goal) * 100, 0)) if goal else 0

    st.markdown('<div class="ha-top">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="ha-topbar">
  <div class="ha-brand">
    <div class="ha-logo">は</div>
    <div>
      <div class="ha-title">하테나일본어 · 마이페이지</div>
      <div class="ha-sub">핵심은 위에, 자세한 내용은 탭에서 확인하세요.</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    colA, colB = st.columns([7, 3], vertical_alignment="center")
    with colB:
        b1, b2 = st.columns(2, gap="small")
        with b1:
            if st.button("🏠 홈", use_container_width=True, key="myp_v3_home"):
                _go_home()
        with b2:
            if st.button("로그아웃", use_container_width=True, key="myp_v3_logout"):
                _logout()

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

    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
<div class="ha-row">
  <div class="ha-inline">
    <span class="ha-chip"><b>이번 달</b> {month_cnt}/{goal}회</span>
    <span class="ha-chip"><b>{int(pct)}%</b> 진행</span>
  </div>
</div>
<div class="ha-progress-row">
  <div class="ha-progress"><div style="width:{pct}%;"></div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    _render_week_widget(attempts)

    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1], gap="small")
    with c1:
        if st.button("📚 오답 복습", use_container_width=True, key="myp_v3_cta_wrongs"):
            st.session_state["myp_tab"] = "wrongs"
            st.rerun()
    with c2:
        if st.button("📈 기록 보기", use_container_width=True, key="myp_v3_cta_records"):
            st.session_state["myp_tab"] = "records"
            st.rerun()
    with c3:
        if st.button("📩 메시지 확인", use_container_width=True, key="myp_v3_cta_msgs"):
            st.session_state["myp_tab"] = "msgs"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Tabs
# ---------------------------
def _render_tab_wrongs(wrongs: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📚 오답</div><div class="ha-sub">앱 필터(칩) + 검색 + 반복오답 토글 + 접힘 목록.</div>', unsafe_allow_html=True)

    if not wrongs:
        st.info("아직 저장된 오답이 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    counts: Dict[str, int] = {}
    for w in wrongs:
        k = (w.get("jp_word") or "").strip()
        if k:
            counts[k] = counts.get(k, 0) + 1

    app_selected = _render_filter_chips("앱 필터", "myp_wrongs_app")
    q = st.text_input("검색 (단어/뜻/발음)", value=st.session_state.get("myp_wrongs_q", ""), key="myp_wrongs_q")
    only_repeat = st.toggle("🔥 반복 오답만 보기 (3회+)", value=st.session_state.get("myp_wrongs_repeat", False), key="myp_wrongs_repeat")
    per_page = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100], value=20, key="myp_wrongs_per")

    def match(w: Dict[str, Any]) -> bool:
        jp = (w.get("jp_word") or "").lower()
        rd = (w.get("reading") or "").lower()
        mn = (w.get("meaning") or "").lower()
        if q.strip():
            qq = q.strip().lower()
            if qq not in jp and qq not in rd and qq not in mn:
                return False
        if only_repeat and counts.get((w.get("jp_word") or "").strip(), 0) < 3:
            return False
        if app_selected and _app_label(w.get("app")) not in app_selected:
            return False
        return True

    filtered = [w for w in wrongs if match(w)]
    repeat_cnt = sum(1 for w in filtered if counts.get((w.get("jp_word") or "").strip(), 0) >= 3)
    st.markdown(
        f'<div class="ha-meta"><span class="ha-chip">총 <b>{_num(len(filtered))}</b>개</span>'
        f'<span class="ha-chip">반복 오답 <b>{_num(repeat_cnt)}</b>개</span></div>',
        unsafe_allow_html=True,
    )

    max_page = max(1, (len(filtered) + per_page - 1) // per_page)
    page = st.number_input("페이지", min_value=1, max_value=max_page, value=min(st.session_state.get("myp_wrongs_page", 1), max_page), step=1, key="myp_wrongs_page")
    start = (page - 1) * per_page
    chunk = filtered[start:start + per_page]

    for w in chunk:
        jp = w.get("jp_word") or "-"
        app = _app_label(w.get("app"))
        level = w.get("level") or "-"
        dt = _fmt_dt(w.get("created_at"))
        rep = counts.get((w.get("jp_word") or "").strip(), 0)
        header = f"{jp}  ·  {app}  ·  Lv {level}" + (f"  ·  🔥 {rep}회" if rep >= 3 else "")
        with st.expander(header, expanded=False):
            c1, c2 = st.columns([2, 2])
            with c1:
                st.markdown(f"**정답**: {w.get('correct_answer') or '-'}")
                st.markdown(f"**내답**: {w.get('user_answer') or '-'}")
            with c2:
                st.markdown(f"**발음**: {w.get('reading') or '-'}")
                st.markdown(f"**뜻**: {w.get('meaning') or '-'}")
            st.caption(f"저장: {dt}")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_tab_records(attempts: List[Dict[str, Any]], attempts_status: str) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📈 기록</div><div class="ha-sub">최근 카드는 3개만. 나머지는 빠른 목록에서 한번에 훑습니다.</div>', unsafe_allow_html=True)

    if attempts_status != "ok" or not attempts:
        st.warning("학습 기록을 불러올 수 없습니다. (RLS 또는 테이블/컬럼 확인)")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    attempts = [_normalize_attempt(a) for a in attempts]

    app_selected = _render_filter_chips("앱 필터", "myp_rec_app")
    level_q = st.text_input("레벨 검색 (예: N4, 4 등)", value=st.session_state.get("myp_rec_lvlq", ""), key="myp_rec_lvlq")

    def match(a: Dict[str, Any]) -> bool:
        if app_selected and _app_label(a.get("app")) not in app_selected:
            return False
        if level_q.strip():
            lv = str(a.get("level") or "").lower()
            if level_q.strip().lower() not in lv:
                return False
        return True

    filtered = [a for a in attempts if match(a)]

    scores = [s for s in (_calc_score(a) for a in filtered[:200]) if s is not None]
    best = max(scores) if scores else None
    avg = round(sum(scores) / len(scores), 1) if scores else None

    now = datetime.now(timezone(timedelta(hours=9)))
    week_ago = now - timedelta(days=7)
    recent7 = [a for a in filtered if (dt := _to_dt_kst(a.get("created_at"))) and dt >= week_ago]

    st.markdown(
        f"""
<div class="ha-meta">
  <span class="ha-chip">총 <b>{_num(len(filtered))}</b>회</span>
  <span class="ha-chip">최근 7일 <b>{_num(len(recent7))}</b>회</span>
  <span class="ha-chip">평균 <b>{(str(avg)+'%') if avg is not None else '-'}</b></span>
  <span class="ha-chip">최고 <b>{(str(best)+'%') if best is not None else '-'}</b></span>
</div>
""",
        unsafe_allow_html=True,
    )

    _render_week_widget(filtered)
    st.divider()

    # ✅ C안: 최근 3개만
    st.markdown("**최근 학습(3개)**")
    top = filtered[:3]
    for a in top:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = a.get("level") or "-"
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        # app + pos 표시
        title = f"{app}" + (f" · {pos}" if pos else "") + f" · Lv {level}"

        st.markdown(
            f"""
<div class="ha-card">
  <div class="ha-card-title">{title}</div>
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

    st.divider()

    st.markdown("**빠른 목록**")
    show_n = st.select_slider("표시 개수", options=[10, 20, 30, 50, 100, 200], value=30, key="myp_rec_n")
    # ✅ 중복감 최소화: 최근3개는 제외하고 목록 시작
    rest = filtered[3:]
    for a in rest[:show_n]:
        app = _app_label(a.get("app"))
        pos = _pos_label(a.get("pos"))
        level = a.get("level") or "-"
        dt = _fmt_dt(a.get("created_at"))
        score = _calc_score(a)
        total, wrong = _calc_total_wrong(a)

        left_badges = f'<span class="ha-badge">{app}</span>'
        if pos:
            left_badges += f' <span class="ha-badge">{pos}</span>'

        st.markdown(
            f"""
<div class="ha-card" style="padding:10px 10px;">
  <div class="ha-row">
    <div class="ha-inline">
      {left_badges}
      <span class="ha-chip">Lv <b>{level}</b></span>
      <span class="ha-chip">{dt}</span>
    </div>
    <div class="ha-inline">
      <span class="ha-chip">점수 <b>{(str(score)+'%') if score is not None else '-'}</b></span>
      <span class="ha-chip">문항 <b>{total}</b></span>
      <span class="ha-chip">오답 <b>{wrong}</b></span>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_tab_messages(msgs: List[Dict[str, Any]]) -> None:
    st.markdown('<div class="ha-section">', unsafe_allow_html=True)
    st.markdown('<div class="ha-title">📩 메시지</div><div class="ha-sub">읽지 않은 메시지를 먼저 보여주고, 기본은 접힘(아코디언)입니다.</div>', unsafe_allow_html=True)

    if not msgs:
        st.info("받은 메시지가 없습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    sb = _sb()

    unread = [m for m in msgs if not m.get("read_at")]
    read = [m for m in msgs if m.get("read_at")]
    ordered = unread + read

    q = st.text_input("검색 (제목/내용)", value=st.session_state.get("myp_msg_q", ""), key="myp_msg_q")
    only_unread = st.toggle("읽지 않음만", value=st.session_state.get("myp_msg_unread", False), key="myp_msg_unread")
    per = st.select_slider("표시 개수", options=[5, 10, 20, 30, 50], value=10, key="myp_msg_per")

    def match(m: Dict[str, Any]) -> bool:
        if only_unread and m.get("read_at"):
            return False
        if q.strip():
            qq = q.strip().lower()
            t = (m.get("title") or "").lower()
            b = (m.get("body") or "").lower()
            if qq not in t and qq not in b:
                return False
        return True

    filtered = [m for m in ordered if match(m)]
    st.markdown(
        f'<div class="ha-meta"><span class="ha-chip">총 <b>{_num(len(filtered))}</b>개</span>'
        f'<span class="ha-chip">읽지 않음 <b>{_num(sum(1 for m in filtered if not m.get("read_at")))}</b>개</span></div>',
        unsafe_allow_html=True,
    )

    for m in filtered[:per]:
        title = m.get("title") or "메시지"
        body = m.get("body") or ""
        dt = _fmt_dt(m.get("created_at"))
        is_unread = not m.get("read_at")
        dot = '<span class="ha-dot"></span>' if is_unread else ""
        chip = "읽지 않음" if is_unread else "읽음"
        header = f"{title}  ·  {dt}" + ("  ·  🔵" if is_unread else "")

        with st.expander(header, expanded=False):
            st.markdown(
                f"""
<div class="ha-card">
  <div class="ha-card-title">{dot}{title}</div>
  <div class="ha-meta">
    <span class="ha-chip">{dt}</span>
    <span class="ha-chip">{chip}</span>
  </div>
  <div style="margin-top:8px; color: var(--ha-text); font-size: 14px; line-height: 1.55;">
    {body.replace('<', '&lt;').replace('>', '&gt;').replace('\\n','<br>')}
  </div>
</div>
""",
                unsafe_allow_html=True,
            )

            if is_unread and sb:
                if st.button("읽음 처리", key=f"msg_read_{m.get('id')}"):
                    try:
                        sb.table("user_messages").update({"read_at": datetime.utcnow().isoformat()}).eq("id", m["id"]).execute()
                        st.success("읽음 처리 완료")
                        st.rerun()
                    except Exception:
                        st.warning("읽음 처리에 실패했습니다. (RLS 확인)")

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------
# Public entrypoint
# ---------------------------
def render() -> None:
    _inject_css()
    _wrap_start()

    wrongs = _load_wrongs(limit=400)
    msgs = _load_messages(limit=300)
    attempts, attempts_status = _load_attempts(limit=500)
    attempts_ok = attempts if attempts_status == "ok" else []

    # ✅ 상단에서는 메시지 영역/뱃지 제거 (중복 방지)
    _render_top_summary(wrongs, attempts_ok)

    # default tab selection (CTA)
    tab_key = st.session_state.get("myp_tab", "")
    labels = ["📚 오답", "📈 기록", "📩 메시지"]

    tab1, tab2, tab3 = st.tabs(labels)

    with tab1:
        _render_tab_wrongs(wrongs)
    with tab2:
        _render_tab_records(attempts_ok, "ok" if attempts_ok else attempts_status)
    with tab3:
        _render_tab_messages(msgs)

    _wrap_end()
