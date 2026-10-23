from unittest.mock import patch

import pytest

from app.github_client import Repo
from main import main, print_tree

REPO = Repo(
    owner="owner",
    name="repo",
    branch="main",
    tree=[{"path": "README.md", "type": "blob", "size": 10}, {"path": "src", "type": "tree"}],
)


def test_print_tree_prints_only_file_paths(capsys):
    tree = [
        {"path": "README.md", "type": "blob"},
        {"path": "src", "type": "tree"},
        {"path": "src/app.py", "type": "blob"},
    ]

    print_tree(tree)

    assert capsys.readouterr().out == "README.md\nsrc/app.py\n"


@patch("main.stream_brief", return_value=iter(["# Repo", "\nBrief"]))
@patch("main.fetch_files", return_value={"README.md": "hi"})
@patch("main.select_files", return_value=["README.md"])
@patch("main.load_repo", return_value=REPO)
def test_main_runs_pipeline_and_streams_brief(load_repo, select_files, fetch_files, stream_brief, capsys):
    exit_code = main(["https://github.com/owner/repo", "--mode", "onboarding", "--max-files", "5"])

    assert exit_code == 0
    assert capsys.readouterr().out == "# Repo\nBrief\n"
    select_files.assert_called_once_with(["README.md"], mode="onboarding", max_files=5)
    fetch_files.assert_called_once_with(REPO, ["README.md"])
    stream_brief.assert_called_once_with("owner/repo", {"README.md": "hi"}, mode="onboarding")


@patch("main.select_files")
@patch("main.load_repo", return_value=REPO)
def test_main_tree_flag_prints_tree_without_llm(load_repo, select_files, capsys):
    assert main(["https://github.com/owner/repo", "--tree"]) == 0

    assert capsys.readouterr().out == "README.md\n"
    select_files.assert_not_called()


def test_main_bad_url_exits_non_zero_with_message(capsys):
    assert main(["https://gitlab.com/owner/repo"]) == 1

    assert "error: Not a GitHub URL" in capsys.readouterr().err


def test_main_rejects_unknown_mode():
    with pytest.raises(SystemExit):
        main(["https://github.com/owner/repo", "--mode", "poem"])
