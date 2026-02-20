# mypage.py
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import streamlit as st
from supabase import create_client

KST = timezone(timedelta(hours=9))

def _sb():
    url = st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else os.environ.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_ANON_KEY") if hasattr(st, "secrets") else os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def _fmt_dt(s: str) -> str:
    try:
        dt = datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(KST)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s[:16] if s else ""

def _cards_css():
    st.markdown(
        """
<style>
.h-card{
  border:1px solid rgba(0,0,0,0.08);
  background: rgba(255,255,255,0.86);
  border-radius: 18px;
  padding: 14px 14px 12px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.04);
}
.h-title{ font-weight:900; font-size:1.15rem; margin-bottom:8px; }
.h-sub{ opacity:.75; margin-top:-2px; margin-bottom:10px; }
.h-pillrow{ display:flex; gap:10px; flex-wrap:wrap; }
.h-pill{
  padding:6px 10px; border-radius:999px;
  border:1px solid rgba(0,0,0,0.08);
  background:#fff; font-weight:700;
}
</style>
        """,
        unsafe_allow_html=True,
    )

def _aggregate(rows: list[dict]) -> dict:
    out = {
        "total_sets": 0,
        "avg_score": 0.0,
        "by_kind": {"word": {"sets":0}, "kanji":{"sets":0}, "talk":{"sets":0}},
        "recent": [],
    }
    if not rows:
        return out
    out["total_sets"] = len(rows)
    total_score = 0.0
    for r in rows:
        kind = (r.get("kind") or r.get("pos_mode") or "").lower()
        if kind not in out["by_kind"]:
            # map common values
            if "kanji" in kind:
                kind="kanji"
            elif "talk" in kind or "speech" in kind:
                kind="talk"
            else:
                kind="word"
        out["by_kind"][kind]["sets"] += 1
        total_score += float(r.get("score") or 0)
    out["avg_score"] = round(total_score / len(rows), 2)
    out["recent"] = rows[:10]
    return out

st.set_page_config(page_title="My Page", layout="centered")

_cards_css()

user = st.session_state.get("user") or {}
user_obj = st.session_state.get("user")
def _get_email(u):
    if not u:
        return ''
    if isinstance(u, dict):
        return (u.get('email') or u.get('user_email') or (u.get('user_metadata') or {}).get('email') or '').strip()
    return (getattr(u, 'email', '') or getattr(getattr(u, 'user', None), 'email', '') or '').strip()

email = _get_email(user_obj) or (user.get('email') if isinstance(user, dict) else '') or (st.session_state.get('user_email') or '')

st.markdown("<div class='h-card'>"
            "<div class='h-title'>👤 마이페이지</div>"
            f"<div class='h-sub'>로그인: {email or '알 수 없음'}</div>"
            "</div>", unsafe_allow_html=True)

sb = st.session_state.get('sb_authed') or st.session_state.get('sb') or _sb()
if not sb or not email:
    st.info("로그인 정보를 확인할 수 없습니다. 홈으로 돌아가 다시 로그인해 주세요.")
    st.stop()

# 최근 기록 (DB 부담 최소: 최근 100개만)
try:
    q = sb.table("quiz_attempts").select("*").eq("user_email", email).order("created_at", desc=True).limit(100).execute()
    rows = q.data or []
except Exception:
    rows = []

agg = _aggregate(rows)

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# Summary cards
c1, c2 = st.columns(2)
with c1:
    st.markdown(
        "<div class='h-card'><div class='h-title'>📦 누적 세트</div>"
        f"<div class='h-pillrow'><div class='h-pill'>{agg['total_sets']} 세트</div>"
        f"<div class='h-pill'>평균 {agg['avg_score']} 점</div></div></div>",
        unsafe_allow_html=True
    )
with c2:
    st.markdown(
        "<div class='h-card'><div class='h-title'>🧭 훈련 분포</div>"
        "<div class='h-pillrow'>"
        f"<div class='h-pill'>단어 {agg['by_kind']['word']['sets']}</div>"
        f"<div class='h-pill'>한자 {agg['by_kind']['kanji']['sets']}</div>"
        f"<div class='h-pill'>회화 {agg['by_kind']['talk']['sets']}</div>"
        "</div></div>",
        unsafe_allow_html=True
    )

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# Recent activity (card + table-like)
st.markdown("<div class='h-card'><div class='h-title'>🕒 최근 기록</div>", unsafe_allow_html=True)
if not rows:
    st.write("아직 기록이 없습니다. 훈련을 1세트만 해도 여기에 쌓입니다.")
else:
    # show 10 rows
    for r in agg["recent"]:
        kind = (r.get("kind") or r.get("pos_mode") or "").lower() or "word"
        score = r.get("score")
        quiz_len = r.get("quiz_len") or r.get("q") or ""
        dt = _fmt_dt(r.get("created_at",""))
        st.markdown(
            f"<div style='display:flex;gap:10px;align-items:center;padding:8px 0;border-top:1px solid rgba(0,0,0,0.06);'>"
            f"<div style='width:64px;font-weight:900;'>{kind}</div>"
            f"<div style='flex:1;opacity:.75;'>{dt}</div>"
            f"<div style='font-weight:800;'>{score}/{quiz_len}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
with st.expander("원본 데이터(개발자용)"):
    st.json(rows[:5])
