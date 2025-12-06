import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


class SettingsError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@lru_cache
def get_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SettingsError(
            "OPENAI_API_KEY not set. Please create a .env with the key before running the app."
        )
    return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
