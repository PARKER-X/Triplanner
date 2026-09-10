import time
import logging

from openai import (
    OpenAI,
    APIError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
    RateLimitError,
)

from ai_engine.core.llm.base import LLMProvider
from ai_engine.core.config import settings

logger = logging.getLogger(__name__)

# How long (seconds) to wait for a Groq response before treating it as a timeout
_REQUEST_TIMEOUT = 60
_MAX_RETRIES = 4
_RETRY_BACKOFF = [2, 5, 10, 20]  # seconds between retries

# All exception types that indicate a transient / infrastructure problem
_TRANSIENT_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    InternalServerError,   # Groq 500s — includes "stream reading error: wsarecv"
)


class GroqProvider(LLMProvider):

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            timeout=_REQUEST_TIMEOUT,
            max_retries=0,  # We handle retries ourselves for full control
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0,
                    response_format={"type": "json_object"},
                    timeout=_REQUEST_TIMEOUT,
                )
                return response.choices[0].message.content

            except RateLimitError as exc:
                # Rate limit: back off longer
                last_exc = exc
                wait = _RETRY_BACKOFF[min(attempt - 1, len(_RETRY_BACKOFF) - 1)] * 2
                logger.warning(
                    "Groq rate limit hit (attempt %d/%d). Retrying in %ds...",
                    attempt, _MAX_RETRIES, wait,
                )
                time.sleep(wait)

            except _TRANSIENT_ERRORS as exc:
                # Connection drop, timeout, or Groq-side stream error ("wsarecv" etc.)
                last_exc = exc
                wait = _RETRY_BACKOFF[min(attempt - 1, len(_RETRY_BACKOFF) - 1)]
                logger.warning(
                    "Groq transient error (attempt %d/%d): %s. Retrying in %ds...",
                    attempt, _MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)

            except APIError as exc:
                # Any other OpenAI-SDK-level error (auth, bad request, etc.)
                # — not retryable, fail fast
                logger.error("Groq non-retryable API error: %s", exc)
                raise

        raise RuntimeError(
            f"Groq API failed after {_MAX_RETRIES} retries. "
            f"Last error: {type(last_exc).__name__}: {last_exc}"
        )