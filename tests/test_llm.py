import pytest

from app.llm import get_chat_model


def test_get_chat_model_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_chat_model()


def test_get_chat_model_uses_model_override(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("REPO_BRIEF_MODEL", "some-model")

    assert get_chat_model().model_name == "some-model"
