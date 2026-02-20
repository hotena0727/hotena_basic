# mypage.py
from __future__ import annotations

import streamlit as st
from datetime import datetime, timedelta, timezone

def _get_email_from_user(user):
    if not user:
        return None
    # dict style
    if isinstance(user, dict):
        return user.get("email") or user.get("user", {}).get("email")
    # object style
    for attr in ("email",):
        if hasattr(user, attr):
            v = getattr(user, attr, None)
            if v:
                return v
    # nested
    if hasattr(user, "user") and getattr(user, "user") is not None:
        u = getattr(user, "user")
        if isinstance(u, dict):
            return u.get("email")
        if hasattr(u, "email"):
            return getattr(u, "email", None)
    return None

def render_mypage(sb=None, user=None, user_plan: str | None = None):
    st.markdown("## 👤 마이페이지")
    email = _get_email_from_user(user) or st.session_state.get("user_email")
    plan = user_plan or st.session_state.get("user_plan") or "free"

    # Header card
    st.markdown(
        f"""
<div style="border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:14px;
            background: rgba(0,0,0,0.02); box-shadow:0 8px 24px rgba(0,0,0,0.04);">
  <div style="font-weight:800; font-size:1.05rem;">{email or "로그인 정보 확인 중"}</div>
  <div style="opacity:0.72; margin-top:4px;">플랜: <b>{plan.upper()}</b> · 최근 기록을 기반으로 학습 현황을 보여드립니다.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # If no sb/user, still show gentle message, not developer-like
    if not sb or not email:
        st.info("로그인 정보를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.")
        return

    # Pull recent attempts (keep it lightweight)
    try:
        rows = (
            sb.table("quiz_attempts")
              .select("created_at,level,pos_mode,quiz_len,score,wrong_count")
              .eq("user_email", email)
              .order("created_at", desc=True)
              .limit(200)
              .execute()
              .data
        )
    except Exception:
        rows = []

    # Aggregate
    total_attempts = len(rows)
    total_correct = sum(int(r.get("score") or 0) for r in rows)
    total_q = sum(int(r.get("quiz_len") or 0) for r in rows)
    total_wrong = sum(int(r.get("wrong_count") or 0) for r in rows)
    acc = int(round((total_correct / total_q) * 100)) if total_q else 0

    # Cards row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("누적 세트", f"{total_attempts}회")
    c2.metric("누적 문항", f"{total_q}문")
    c3.metric("정답률", f"{acc}%")
    c4.metric("오답", f"{total_wrong}개")

    st.markdown("---")

    # Recent activity cards
    st.markdown("### 🗂️ 최근 학습 기록")
    if not rows:
        st.write("아직 기록이 없습니다. 훈련을 한 번만 해도 여기에 쌓입니다.")
        return

    # show last 12 as cards
    for r in rows[:12]:
        dt = r.get("created_at")
        when = ""
        try:
            when = dt.replace("T"," ").split(".")[0] if isinstance(dt,str) else str(dt)
        except Exception:
            when = str(dt)

        level = str(r.get("level") or "")
        mode = str(r.get("pos_mode") or "")
        qlen = int(r.get("quiz_len") or 0)
        score = int(r.get("score") or 0)
        wrong = int(r.get("wrong_count") or 0)
        acc1 = int(round((score/qlen)*100)) if qlen else 0

        st.markdown(
            f"""
<div style="border:1px solid rgba(0,0,0,0.08); border-radius:14px; padding:12px 14px;
            background:#fff; box-shadow:0 6px 18px rgba(0,0,0,0.04); margin-bottom:10px;">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
    <div style="font-weight:800;">{level} · {mode}</div>
    <div style="opacity:0.72; font-size:0.9rem;">{when}</div>
  </div>
  <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap;">
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">점수 {score}/{qlen}</div>
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">정답률 {acc1}%</div>
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">오답 {wrong}개</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("### ✅ 다음 추천")
    st.write("오늘은 오답이 나온 세트를 한 번만 더 복습하면 효과가 큽니다.")
