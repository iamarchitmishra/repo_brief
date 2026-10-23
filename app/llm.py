import os

from langchain_openai import ChatOpenAI

DEFAULT_MODEL = "gpt-5.5"
TIMEOUT_SECONDS = 120


def get_chat_model():
    # Credentials come from OPENAI_API_KEY in the environment; never pass a key in code.
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")

    return ChatOpenAI(
        model=os.environ.get("REPO_BRIEF_MODEL", DEFAULT_MODEL),
        timeout=TIMEOUT_SECONDS,
        max_retries=2,
    )
