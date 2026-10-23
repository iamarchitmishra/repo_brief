import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.github_client import (
    Repo,
    fetch_file,
    fetch_files,
    get_default_branch,
    load_repo,
    parse_github_url,
)

# Patch only our module's session, not requests.get for the whole process.
SESSION_GET = "app.github_client.SESSION.get"


def make_response(status_code=200, json_data=None, headers=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.headers = headers or {}
    response.text = text
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    return response


def route_github(branch_response, tree_response):
    # Pick the response by URL so tests don't depend on call order.
    def fake_get(url, **kwargs):
        if "/git/trees/" in url:
            return tree_response
        return branch_response

    return fake_get


# --- parse_github_url ---

def test_parse_github_url_happy_path():
    assert parse_github_url("https://github.com/owner/repo") == ("owner", "repo")


def test_parse_github_url_strips_dot_git():
    assert parse_github_url("https://github.com/owner/repo.git") == ("owner", "repo")


def test_parse_github_url_ignores_extra_path():
    assert parse_github_url("https://github.com/owner/repo/tree/main/src") == ("owner", "repo")


def test_parse_github_url_rejects_non_github_host():
    with pytest.raises(ValueError, match="GitHub"):
        parse_github_url("https://gitlab.com/owner/repo")


def test_parse_github_url_rejects_missing_repo():
    with pytest.raises(ValueError):
        parse_github_url("https://github.com/owner")


# --- get_default_branch ---

@patch(SESSION_GET)
def test_get_default_branch_returns_branch(mock_get):
    mock_get.return_value = make_response(json_data={"default_branch": "master"})

    assert get_default_branch("owner", "repo") == "master"


@patch(SESSION_GET)
def test_get_default_branch_raises_on_404(mock_get):
    mock_get.return_value = make_response(status_code=404)

    with pytest.raises(requests.HTTPError):
        get_default_branch("owner", "missing-repo")


# --- load_repo / fetch_tree ---

@patch(SESSION_GET)
def test_load_repo_returns_entries_for_default_branch(mock_get):
    tree = [
        {"path": "README.md", "type": "blob"},
        {"path": "src", "type": "tree"},
    ]
    mock_get.side_effect = route_github(
        make_response(json_data={"default_branch": "develop"}),
        make_response(json_data={"tree": tree, "truncated": False}),
    )

    assert load_repo("https://github.com/owner/repo").tree == tree

    tree_call = next(c for c in mock_get.call_args_list if "/git/trees/" in c.kwargs["url"])
    assert tree_call.kwargs["url"].endswith("/repos/owner/repo/git/trees/develop")
    assert tree_call.kwargs["params"] == {"recursive": "1"}


@patch(SESSION_GET)
def test_load_repo_raises_clear_error_on_rate_limit(mock_get):
    mock_get.side_effect = route_github(
        make_response(json_data={"default_branch": "main"}),
        make_response(status_code=403, headers={"X-RateLimit-Remaining": "0"}),
    )

    with pytest.raises(RuntimeError, match="rate limit"):
        load_repo("https://github.com/owner/repo").tree


@patch(SESSION_GET)
def test_load_repo_passes_timeout_on_every_call(mock_get):
    mock_get.side_effect = route_github(
        make_response(json_data={"default_branch": "main"}),
        make_response(json_data={"tree": [], "truncated": False}),
    )

    load_repo("https://github.com/owner/repo").tree

    assert mock_get.call_count == 2
    for call in mock_get.call_args_list:
        assert call.kwargs.get("timeout") is not None


@patch(SESSION_GET)
def test_load_repo_warns_and_returns_partial_tree_when_truncated(mock_get, caplog):
    tree = [{"path": "README.md", "type": "blob"}]
    mock_get.side_effect = route_github(
        make_response(json_data={"default_branch": "main"}),
        make_response(json_data={"tree": tree, "truncated": True}),
    )

    with caplog.at_level(logging.WARNING):
        assert load_repo("https://github.com/owner/repo").tree == tree

    assert "truncated" in caplog.text


@patch(SESSION_GET)
def test_sends_token_header_when_github_token_set(mock_get, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    mock_get.return_value = make_response(json_data={"default_branch": "main"})

    get_default_branch("owner", "repo")

    assert mock_get.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"


# --- fetch_file ---

@patch(SESSION_GET)
def test_fetch_file_returns_text_from_raw_url(mock_get):
    mock_get.return_value = make_response(text="print('hi')\n")

    assert fetch_file("owner", "repo", "main", "src/app.py") == "print('hi')\n"
    assert mock_get.call_args.kwargs["url"] == (
        "https://raw.githubusercontent.com/owner/repo/main/src/app.py"
    )


@patch(SESSION_GET)
def test_load_repo_returns_owner_name_and_branch(mock_get):
    mock_get.side_effect = route_github(
        make_response(json_data={"default_branch": "develop"}),
        make_response(json_data={"tree": [], "truncated": False}),
    )

    repo = load_repo("https://github.com/owner/repo")

    assert (repo.owner, repo.name, repo.branch) == ("owner", "repo", "develop")


@patch(SESSION_GET)
def test_fetch_files_skips_files_that_fail(mock_get, caplog):
    def fake_get(url, **kwargs):
        if url.endswith("missing.py"):
            return make_response(status_code=404)
        return make_response(text="ok")

    mock_get.side_effect = fake_get
    repo = Repo(owner="owner", name="repo", branch="main", tree=[])

    with caplog.at_level(logging.WARNING):
        files = fetch_files(repo, ["README.md", "missing.py"])

    assert files == {"README.md": "ok"}
    assert "missing.py" in caplog.text
