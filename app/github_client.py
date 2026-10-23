import logging
import os
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

GITHUB_HOSTS = {"github.com", "www.github.com"}
API_BASE = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"
TIMEOUT_SECONDS = 30

# One shared session: retries transient failures (429, 5xx) with backoff.
# raise_on_status=False hands the final response back so _get can turn it into a clear error.
SESSION = requests.Session()
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
    ),
)


@dataclass # @claude explain
class Repo:
    owner: str
    name: str
    branch: str
    tree: list


def parse_github_url(url):
    parsed = urlparse(url)
    if parsed.netloc not in GITHUB_HOSTS:
        raise ValueError(f"Not a GitHub URL: {url}")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"GitHub URL must include owner and repo: {url}")

    return parts[0], parts[1].rstrip(".git")


def get_default_branch(owner, repo):
    return _get(f"{API_BASE}/repos/{owner}/{repo}").json()["default_branch"]


def load_repo(repo_url):
    owner, repo = parse_github_url(repo_url)
    branch = get_default_branch(owner, repo)
    return Repo(owner=owner, name=repo, branch=branch, tree=fetch_tree(owner, repo, branch))


def fetch_tree(owner, repo, branch):
    data = _get(
        f"{API_BASE}/repos/{owner}/{repo}/git/trees/{branch}",
        params={"recursive": "1"},
    ).json()

    if data.get("truncated"):
        # The recursive tree API caps at ~100k entries / 7MB and has no pagination.
        logger.warning("Tree for %s/%s is truncated; continuing with a partial file list", owner, repo)

    return data.get("tree", [])


def fetch_file(owner, repo, branch, path):
    # raw.githubusercontent.com does not count against the REST API rate limit.
    return _get(f"{RAW_BASE}/{owner}/{repo}/{branch}/{quote(path)}").text


def fetch_files(repo, paths):
    """Return {path: text} for the paths we could fetch; one bad file doesn't sink the brief."""
    files = {}
    for path in paths:
        try:
            files[path] = fetch_file(repo.owner, repo.name, repo.branch, path)
        except requests.RequestException as error:
            logger.warning("Skipping %s: %s", path, error)
    return files


def _headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(url, params=None):
    response = SESSION.get(url=url, params=params, headers=_headers(), timeout=TIMEOUT_SECONDS)

    if response.status_code in (403, 429) and response.headers.get("X-RateLimit-Remaining") == "0":
        raise RuntimeError("GitHub API rate limit exceeded; set GITHUB_TOKEN to raise the limit")

    response.raise_for_status()
    return response
