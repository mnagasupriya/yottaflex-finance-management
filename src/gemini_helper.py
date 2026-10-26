"""Gemini helper for YottaFlex budget insights.

The dashboard computes all financial figures in Python. Gemini only explains
those supplied figures and never changes transactions or budgets.
"""

import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None


def generate_budget_insight(budget_summary: dict) -> str:
    """Generate a plain-language explanation, retrying temporary 503 errors."""
    if not _client:
        return (
            "Gemini API key is missing. Add GEMINI_API_KEY to your project's "
            ".env file, then restart Streamlit."
        )

    prompt = f"""
You are a careful household finance analyst. Explain the following calculated
budget report for a user in clear, practical language.

- Summarize spending compared with budget limits.
- Point out categories or records that may need attention.
- Suggest practical next steps, without being judgmental.
- Use only the supplied values. Do not invent numbers or assume missing data.
- If the data does not support a conclusion, say so.
- Do not claim to have modified transactions, budgets, or account data.
- Keep the response concise, with headings and bullet points.

Calculated budget report (Python-generated):
{budget_summary}
"""

    # 503 UNAVAILABLE is often temporary. Retry with backoff rather than
    # immediately showing an error to the user.
    delays = (1, 3, 6)
    last_error = None
    for attempt, delay in enumerate(delays):
        try:
            response = _client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if text and text.strip():
                return text.strip()
            return "Gemini returned an empty response. Please try again."
        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()
            is_temporary = any(
                marker in error_text
                for marker in ("503", "unavailable", "429", "resource_exhausted", "500", "internal")
            )
            if not is_temporary or attempt == len(delays) - 1:
                break
            time.sleep(delay)

    error_text = str(last_error).lower() if last_error else ""
    if "503" in error_text or "unavailable" in error_text:
        return (
            "Gemini is temporarily busy (503 UNAVAILABLE), even after automatic "
            "retries. Your Python budget calculations are still available. "
            "Please wait a minute and click Generate budget insights again."
        )
    if "429" in error_text or "resource_exhausted" in error_text:
        return (
            "Gemini API quota or rate limit reached. Check your Gemini API quota "
            "and billing/rate limits, then try again later."
        )
    if "api key" in error_text or "permission_denied" in error_text or "unauthorized" in error_text:
        return (
            "Gemini authentication failed. Check that GEMINI_API_KEY is valid in "
            ".env, then restart Streamlit. Do not paste the key into chat."
        )
    return (
        "Gemini could not generate the explanation. Check your internet connection, "
        "API key, model access, and quota, then try again. "
        f"(Technical detail: {str(last_error)[:250]})"
    )
