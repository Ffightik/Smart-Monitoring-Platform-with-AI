import os
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from openai import OpenAI

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Lazy init — only created on first use, after .env is loaded."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client

SYSTEM_PROMPT = """You are an intelligent health assistant integrated into a health analytics platform.
You have access to the user's Apple Watch data from the last 30 days, including heart rate, 
sleep patterns, activity levels, calories, and workout history.

Your role is to:
1. Explain ML model prediction results in simple, clear language
2. Answer the user's health-related questions based on their actual data
3. Be honest when data is missing or insufficient to draw conclusions
4. Never diagnose medical conditions — always recommend consulting a doctor for medical concerns
5. Keep responses concise (3-5 sentences unless more detail is requested)

Tone: friendly, supportive, evidence-based."""


# ── Session store (in-memory, keyed by user_id) ───────────────────────────────
# In production, replace with Redis or a database-backed session store.
_sessions: dict[str, list[dict]] = {}


def _get_session(user_id: str) -> list[dict]:
    """Return existing conversation history or create a new session."""
    if user_id not in _sessions:
        _sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return _sessions[user_id]


def _build_context_message(stats: dict, prediction: dict) -> str:
    """Format model output + health stats into a GPT-readable context block."""
    lines = ["📊 User's current health context (last 30 days):"]

    if stats:
        if "avg_hr" in stats:
            lines.append(f"- Average heart rate: {stats['avg_hr']:.1f} bpm")
        if "avg_sleep_stage" in stats:
            stage_map = {-1: "Unknown", 0: "Awake", 1: "Light", 2: "REM", 3: "Deep"}
            label = stage_map.get(round(stats["avg_sleep_stage"]), "Unknown")
            lines.append(f"- Dominant sleep stage: {label}")
        if "avg_active_energy" in stats:
            lines.append(f"- Average active energy: {stats['avg_active_energy']:.1f} kcal")
        if "avg_bmi" in stats:
            lines.append(f"- Average BMI: {stats['avg_bmi']:.1f}")
        if "workout_days" in stats:
            lines.append(f"- Workout sessions in period: {stats['workout_days']}")

    if prediction:
        lines.append(f"\n🤖 ML Model Prediction:")
        lines.append(f"- Current activity level : {prediction.get('current', 'N/A')}")
        lines.append(f"- Predicted next state   : {prediction.get('next', 'N/A')}")
        lines.append(f"- Hybrid model result    : {prediction.get('hybrid', 'N/A')}")
        conf = prediction.get("confidence", {})
        if conf:
            lines.append(
                f"- Confidence (hybrid)    : {conf.get('hybrid', 0):.1%}"
            )

    return "\n".join(lines)


def chat(
    user_id: str,
    user_message: str,
    stats: Optional[dict] = None,
    prediction: Optional[dict] = None,
    inject_context: bool = False,
) -> str:
    """
    Send a message and get a response, maintaining full conversation history.

    Args:
        user_id:        Unique identifier for the user's session.
        user_message:   The user's question or message.
        stats:          Dict of aggregated health stats (optional).
        prediction:     Dict returned by hybrid_model.predict() (optional).
        inject_context: If True, prepend health context to this message.
                        Set to True on the first message of a session or
                        after new data is uploaded.

    Returns:
        The assistant's reply as a plain string.
    """
    history = _get_session(user_id)

    # Prepend context block when fresh data is available
    if inject_context and (stats or prediction):
        context_block = _build_context_message(stats or {}, prediction or {})
        full_message = f"{context_block}\n\n💬 User question: {user_message}"
    else:
        full_message = user_message

    history.append({"role": "user", "content": full_message})

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=history,
        temperature=0.7,
        max_tokens=512,
    )

    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})

    return reply


def reset_session(user_id: str) -> None:
    """Clear conversation history for a user (e.g. after new data upload)."""
    _sessions.pop(user_id, None)


def get_history(user_id: str) -> list[dict]:
    """Return the full conversation history (excluding system prompt)."""
    history = _get_session(user_id)
    return [m for m in history if m["role"] != "system"]
