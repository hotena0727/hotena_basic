from __future__ import annotations

import streamlit as st
# ============================================================
# ✅ Hide Streamlit default header/footer (applies per page)
# ============================================================
st.markdown(
    """
<style>
/* Hide Streamlit chrome */
header, footer {visibility: hidden;}
[data-testid="stHeader"], [data-testid="stFooter"] {display: none;}
/* In some builds, Streamlit shows a bottom badge/container */
[data-testid="stBottomBlockContainer"] {display: none;}
/* Fallback for older/newer badge classnames */
[class^="viewerBadge_"], [class*="viewerBadge_"] {display: none;}
</style>
""",
    unsafe_allow_html=True,
)

def _get_email(user):
    if not user:
        return None
    if isinstance(user, dict):
        return user.get("email") or (user.get("user") or {}).get("email")
    if hasattr(user, "email") and getattr(user, "email"):
        return getattr(user, "email")
    if hasattr(user, "user") and getattr(user, "user") is not None:
        u=getattr(user, "user")
        if isinstance(u, dict):
            return u.get("email")
        if hasattr(u, "email"):
            return getattr(u, "email", None)
    return None

def render():
    st.markdown("## 👤 마이페이지")
    user = st.session_state.get("user")
    sb = st.session_state.get("sb_authed") or st.session_state.get("sb")
    plan = (st.session_state.get("user_plan") or "free").upper()
    email = _get_email(user) or st.session_state.get("user_email")

    st.markdown(
        f"""
<div style="border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:14px;
            background:#fff; box-shadow:0 8px 24px rgba(0,0,0,0.04);">
  <div style="font-weight:800; font-size:1.05rem;">{email or "로그인 정보 확인 중"}</div>
  <div style="opacity:0.72; margin-top:4px;">플랜: <b>{plan}</b> · 최근 학습 기록을 카드로 보여드립니다.</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not sb or not email:
        st.info("로그인 정보를 불러오는 중입니다. 홈에서 다시 들어오면 자동으로 연결됩니다.")
        return

    try:
        rows = (sb.table("quiz_attempts")
                  .select("created_at,level,pos_mode,quiz_len,score,wrong_count")
                  .eq("user_email", email)
                  .order("created_at", desc=True)
                  .limit(100)
                  .execute()
                  .data)
    except Exception:
        rows = []

    total_attempts=len(rows)
    total_q=sum(int(r.get("quiz_len") or 0) for r in rows)
    total_score=sum(int(r.get("score") or 0) for r in rows)
    total_wrong=sum(int(r.get("wrong_count") or 0) for r in rows)
    acc=int(round((total_score/total_q)*100)) if total_q else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("학습 세트", f"{total_attempts}회")
    c2.metric("풀어본 문항", f"{total_q}문")
    c3.metric("정답률", f"{acc}%")
    c4.metric("오답", f"{total_wrong}개")

    st.markdown("---")
    st.markdown("### 🗂️ 최근 기록 (최대 12개)")
    if not rows:
        st.write("아직 기록이 없습니다. 훈련을 시작하면 자동으로 카드가 쌓입니다.")
        return

    for r in rows[:12]:
        dt=str(r.get("created_at") or "").replace("T"," ").split(".")[0]
        level=str(r.get("level") or "")
        mode=str(r.get("pos_mode") or "")
        qlen=int(r.get("quiz_len") or 0)
        score=int(r.get("score") or 0)
        wrong=int(r.get("wrong_count") or 0)
        pct=int(round((score/qlen)*100)) if qlen else 0
        st.markdown(
            f"""
<div style="border:1px solid rgba(0,0,0,0.08); border-radius:14px; padding:12px 14px;
            background:#fff; box-shadow:0 6px 18px rgba(0,0,0,0.04); margin-bottom:10px;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div style="font-weight:800;">{level} · {mode}</div>
    <div style="opacity:0.72; font-size:0.9rem;">{dt}</div>
  </div>
  <div style="margin-top:8px; display:flex; gap:10px; flex-wrap:wrap;">
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">점수 {score}/{qlen}</div>
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">정답률 {pct}%</div>
    <div style="padding:6px 10px; border-radius:999px; background:rgba(0,0,0,0.04);">오답 {wrong}개</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

render()
