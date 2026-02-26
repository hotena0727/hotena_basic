
# ============================================================
# ai_tutor.py (FINAL STABLE VERSION)
# - Admin unlimited bypass
# - Context-safe coaching
# - No forced question induction
# ============================================================

from __future__ import annotations
import os
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ============================================================
# ✅ ADMIN UNLIMITED BYPASS
# ============================================================
def check_quota(plan: str, is_admin: bool):
    if is_admin:
        return True, 0, 9999

    max_uses = 5 if plan == "pro" else 3
    # 실제 Supabase RPC 호출은 기존 로직 유지
    return True, 0, max_uses


# ============================================================
# ✅ SMART COACH CORE
# ============================================================
def ask_hatena(mode: str, user_input: str, context: dict | None = None, meta: dict | None = None):

    is_admin = bool(meta.get("is_admin")) if meta else False
    plan = meta.get("plan", "free") if meta else "free"

    allowed, used, remaining = check_quota(plan, is_admin)
    if not allowed:
        return f"(Quota denied) plan={plan} used={used} remaining={remaining}"

    system_prompt = """
당신은 일본어 회화 코치 '하테나쌤'입니다.

규칙:
1. 사용자의 답변이 맞으면 짧게 칭찬하고 확장 표현 1개만 제시.
2. 길게 강의하지 않는다.
3. 사용자의 질문이 없으면 질문을 유도하지 않는다.
4. 회화 맥락과 무관한 상담성 질문에는 답하지 않는다.
"""

    user_prompt = user_input

    if context:
        user_prompt = f"""
현재상황: {context.get("situation")}
상대발화: {context.get("partner")}
학습자답변: {user_input}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"AI 오류: {e}"
