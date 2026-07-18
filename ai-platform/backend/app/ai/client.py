"""
Thin wrapper around the Anthropic client so the rest of the codebase never
imports the SDK directly — makes it easy to swap models or add retries later.
"""

import anthropic
from app.config import settings

MODEL = "claude-sonnet-4-6"

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
