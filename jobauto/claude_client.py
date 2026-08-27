import json
import re

import anthropic

from jobauto.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file (see .env.example)."
            )
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _extract_text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def ask_json(system: str, user: str, max_tokens: int = 8000) -> dict:
    """Send a prompt to Claude and parse a JSON object out of the reply.
    Raises ValueError if the reply isn't valid JSON (caller decides how to handle it)."""
    client = get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise ValueError(f"Claude declined the request: {response.stop_details}")
    raw = _strip_json_fence(_extract_text(response))
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude did not return valid JSON: {e}\n---\n{raw[:2000]}")


def ask_text(system: str, user: str, max_tokens: int = 4000) -> str:
    client = get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise ValueError(f"Claude declined the request: {response.stop_details}")
    return _extract_text(response).strip()
