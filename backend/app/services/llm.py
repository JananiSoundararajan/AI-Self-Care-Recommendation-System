"""
LLM service — generates personalized self-care plans.

Uses OpenAI gpt-4o-mini by default.
Falls back to a deterministic mock plan when:
  - USE_MOCK_LLM=true in .env
  - OPENAI_API_KEY is missing or empty
"""

import json
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Prompt template ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a compassionate, evidence-based self-care coach.
Your role is to generate practical, personalized daily self-care plans.
Always respond with valid JSON only — no markdown, no preamble.
"""

PLAN_TEMPLATE = """
User check-in data:
- Mood: {mood}/10
- Sleep last night: {sleep_hours} hours
- Stress level: {stress_level}/10
- Activity level: {activity_level}/10
- Wellness state (ML-classified): {mood_label}
- Personal note: "{note}"

Recent history (last 3 check-ins):
{history_summary}

Relevant wellness guidance retrieved for this user's state:
{rag_context}

Based on the above, generate a personalized self-care plan for today.
Return ONLY this JSON structure (no extra keys, no markdown):

{{
  "morning": "specific actionable task for the morning (1-2 sentences)",
  "afternoon": "specific actionable task for the afternoon (1-2 sentences)",
  "evening": "specific actionable task for the evening (1-2 sentences)",
  "focus_tip": "one evidence-based insight about the user's current pattern (1 sentence)"
}}
"""

# ── Mock fallback plans ────────────────────────────────────────────────────────

MOCK_PLANS = {
    "low": {
        "morning": "Start with 5 minutes of box breathing before checking your phone. Eat a protein-rich breakfast to stabilize blood sugar.",
        "afternoon": "Step outside for a 10-minute walk — even brief sunlight and movement reset cortisol levels.",
        "evening": "Put screens away 30 minutes before bed. Try the 4-7-8 breathing technique to ease into sleep.",
        "focus_tip": "Your stress and sleep patterns suggest your nervous system needs recovery mode. Protect your evening aggressively.",
    },
    "medium": {
        "morning": "Set one clear intention for today before opening email. A 10-minute stretch routine will sharpen your focus.",
        "afternoon": "Use the Pomodoro technique (25 min on, 5 min off) to maintain energy without burning out.",
        "evening": "Wind down with 15 minutes of light reading or journaling — note 3 specific things that went well today.",
        "focus_tip": "You're in a maintenance zone — small consistent actions now will tip you toward high wellness within a few days.",
    },
    "high": {
        "morning": "Capitalize on your good state — tackle your most important task within 2 hours of waking.",
        "afternoon": "A short resistance training session or brisk walk will extend today's positive momentum.",
        "evening": "Use your evening to invest in a relationship — even a 10-minute call with a friend compounds well-being.",
        "focus_tip": "You're thriving — lock in the habits driving this (sleep consistency, activity) so they become automatic.",
    },
}


# ── LLM call ──────────────────────────────────────────────────────────────────

def _should_use_mock() -> bool:
    if settings.use_mock_llm:
        return True
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        logger.warning("OPENAI_API_KEY not set — using mock LLM fallback.")
        return True
    return False


def _format_history(history: list[dict]) -> str:
    if not history:
        return "No previous check-ins available."
    lines = []
    for h in history[-3:]:
        lines.append(
            f"  • {h.get('created_at', 'unknown date')}: "
            f"mood={h['mood']}, sleep={h['sleep_hours']}h, "
            f"stress={h['stress_level']}, activity={h['activity_level']}"
        )
    return "\n".join(lines)


def generate_plan(
    mood: int,
    sleep_hours: float,
    stress_level: int,
    activity_level: int,
    mood_label: str,
    note: Optional[str],
    history: list[dict],
    rag_context: list[str],
) -> dict:
    """
    Returns a dict with keys: morning, afternoon, evening, focus_tip
    """
    if _should_use_mock():
        plan = MOCK_PLANS.get(mood_label, MOCK_PLANS["medium"]).copy()
        logger.info(f"Mock LLM plan returned for mood_label={mood_label}")
        return plan

    # Real OpenAI call
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        prompt = PLAN_TEMPLATE.format(
            mood=mood,
            sleep_hours=sleep_hours,
            stress_level=stress_level,
            activity_level=activity_level,
            mood_label=mood_label,
            note=note or "None provided",
            history_summary=_format_history(history),
            rag_context="\n".join(f"  • {tip}" for tip in rag_context) or "  • No context retrieved.",
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=400,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        plan = json.loads(raw)
        logger.info("OpenAI plan generated successfully.")
        return plan

    except Exception as e:
        logger.error(f"OpenAI call failed: {e}. Falling back to mock plan.")
        return MOCK_PLANS.get(mood_label, MOCK_PLANS["medium"]).copy()
