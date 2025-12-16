import os
from functools import lru_cache
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI # <--- CORRECT

load_dotenv()


class SettingsError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@lru_cache
def get_llm() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SettingsError(
            "GEMINI_API_KEY not set. Please create a .env with the key before running the app."
        )
    
    # LangChain will automatically read GEMINI_API_KEY from environment
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0
    )
