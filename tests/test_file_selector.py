from unittest.mock import MagicMock

import pytest
from langchain_core.exceptions import OutputParserException

from app.file_selector import FileSelection, SelectionError, select_files

PATHS = ["README.md", "pyproject.toml", "app/main.py", "tests/test_main.py"]


def fake_llm(*results):
    """A stand-in chat model; each invoke() returns (or raises) the next result."""
    structured = MagicMock()
    structured.invoke.side_effect = list(results)
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    return llm, structured


def test_returns_selected_paths_in_model_order():
    llm, _ = fake_llm(FileSelection(files=["app/main.py", "README.md"]))

    assert select_files(PATHS, llm=llm) == ["app/main.py", "README.md"]


def test_drops_hallucinated_and_duplicate_paths():
    llm, _ = fake_llm(FileSelection(files=["README.md", "src/made_up.py", "README.md"]))

    assert select_files(PATHS, llm=llm) == ["README.md"]


def test_caps_selection_at_max_files():
    llm, _ = fake_llm(FileSelection(files=PATHS))

    assert select_files(PATHS, llm=llm, max_files=2) == ["README.md", "pyproject.toml"]


def test_retries_once_on_invalid_output():
    llm, structured = fake_llm(
        OutputParserException("bad json"),
        FileSelection(files=["README.md"]),
    )

    assert select_files(PATHS, llm=llm) == ["README.md"]
    assert structured.invoke.call_count == 2


def test_raises_selection_error_after_two_invalid_outputs():
    llm, _ = fake_llm(OutputParserException("bad"), OutputParserException("bad again"))

    with pytest.raises(SelectionError, match="invalid output"):
        select_files(PATHS, llm=llm)


def test_raises_selection_error_when_no_real_paths_selected():
    llm, _ = fake_llm(FileSelection(files=["nope.py"]))

    with pytest.raises(SelectionError, match="did not select"):
        select_files(PATHS, llm=llm)


def test_mode_changes_the_prompt():
    llm, structured = fake_llm(FileSelection(files=["README.md"]))

    select_files(PATHS, mode="onboarding", llm=llm)

    system_prompt = structured.invoke.call_args.args[0][0][1]
    assert "new contributor" in system_prompt


def test_rejects_unknown_mode():
    llm, _ = fake_llm()

    with pytest.raises(ValueError, match="Unknown mode"):
        select_files(PATHS, mode="poem", llm=llm)
