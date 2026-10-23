# repo-brief

Generate a README or contributor onboarding guide for any public GitHub repo.

## Usage

```bash
uv sync
export OPENAI_API_KEY=...          # required
export GITHUB_TOKEN=...            # optional: raises GitHub's limit from 60 to 5,000 requests/hour
export REPO_BRIEF_MODEL=gpt-5.5    # optional model override

uv run python main.py https://github.com/owner/repo                      # README to stdout
uv run python main.py https://github.com/owner/repo --mode onboarding > ONBOARDING.md
uv run python main.py https://github.com/owner/repo --tree               # just list files
```

Run the tests (offline; GitHub and the LLM are mocked):

```bash
uv run pytest -q
```

## How it works

1. **Fetch the tree** (`app/github_client.py`): parse the URL, look up the default branch, then fetch
   the recursive git tree. If the tree is truncated, it warns and continues with partial results.
2. **Filter in plain code** (`app/tree_filter.py`): drop vendor/build dirs, lockfiles, binaries and
   files over 500KB, then keep the shallowest 1,500 paths.
3. **LLM picks files** (`app/file_selector.py`): structured output validated against a Pydantic
   schema, one retry on invalid output, and invented paths dropped.
4. **Fetch the chosen files** from `raw.githubusercontent.com`, which doesn't count against the API rate limit.
   Files that fail to fetch are skipped with a warning.
5. **Write the brief** (`app/brief_writer.py`): file contents within a size budget (6k characters per file, 60k
   in total, marked `[truncated]`), streamed to stdout as it's generated.

## Limits

- The recursive tree API caps at about 100k entries; bigger repos get a partial tree.
- Only the first 6k characters of each file reach the model.
- Unauthenticated GitHub access allows 60 API requests per hour.
