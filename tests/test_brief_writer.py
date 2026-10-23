from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessageChunk

from app.brief_writer import build_context, stream_brief


def fake_llm(*chunks):
    llm = MagicMock()
    llm.stream.return_value = iter(AIMessageChunk(content=c) for c in chunks)
    return llm


def test_build_context_labels_each_file():
    context = build_context({"README.md": "hello", "app.py": "print(1)"})

    assert context == "=== README.md ===\nhello\n\n=== app.py ===\nprint(1)"


def test_build_context_truncates_long_files_with_marker():
    context = build_context({"big.py": "x" * 50}, max_chars_per_file=10)

    assert context == "=== big.py ===\n" + "x" * 10 + "\n[truncated]"


def test_build_context_respects_total_budget():
    files = {"a.py": "a" * 10, "b.py": "b" * 10, "c.py": "c" * 10}

    context = build_context(files, max_chars_per_file=10, max_total_chars=15)

    assert "a" * 10 in context
    assert "b" * 5 + "\n[truncated]" in context
    assert "c.py" not in context


def test_stream_brief_yields_chunks_in_order_and_skips_empty():
    llm = fake_llm("# Title", "", "\nBody")

    assert list(stream_brief("owner/repo", {"README.md": "hi"}, llm=llm)) == ["# Title", "\nBody"]


def test_stream_brief_prompt_contains_mode_and_files():
    llm = fake_llm("ok")

    list(stream_brief("owner/repo", {"app.py": "print(1)"}, mode="onboarding", llm=llm))

    system, human = llm.stream.call_args.args[0]
    assert "onboarding guide" in system[1]
    assert "owner/repo" in human[1] and "print(1)" in human[1]


def test_stream_brief_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unknown mode"):
        list(stream_brief("owner/repo", {}, mode="poem", llm=fake_llm()))
