# ai_tutor.py
from __future__ import annotations
import streamlit as st
from typing import Any, Dict, Tuple

def _check_quota(max_uses: int, is_admin: bool) -> Tuple[bool, int, int]:
    if is_admin:
        return True, 0, 9999

    try:
        sb = st.session_state.get("sb")
        if not sb:
            return False, None, None

        res = sb.rpc("ai_check_and_inc_kst", {"max_uses": max_uses}).execute()
        data = res.data[0]

        return data.get("allowed"), data.get("used"), data.get("remaining")

    except Exception:
        return False, None, None


def ask_hatena(
    mode: str,
    user_input: str,
    context: Any = None,
    meta: Dict[str, Any] | None = None,
) -> str:

    meta = meta or {}
    is_admin = bool(meta.get("is_admin", False))
    plan = meta.get("plan", "free")

    max_uses = 5 if plan == "pro" else 3
    allowed, used, remaining = _check_quota(max_uses, is_admin)

    if not allowed:
        return f"(Quota denied) used={used} remaining={remaining}"

    situation = ""
    correct = ""
    user_ans = ""

    if isinstance(context, dict):
        situation = context.get("situation", "")
        correct = context.get("correct", "")
        user_ans = context.get("user_answer", "")

    if mode == "talk":
        response = (
            f"좋아요 🙂\n"
            f"현재 상황: {situation}\n"
            f"당신의 답변: {user_ans}\n"
            f"정답 예시: {correct}\n"
            f"아주 자연스러운 표현이에요."
        )
    else:
        response = "잘하고 있어요 🙂"

    return response
