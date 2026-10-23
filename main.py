import argparse
import logging
import sys

import requests

from app.brief_writer import stream_brief
from app.file_selector import MAX_SELECTED_FILES, SelectionError, select_files
from app.github_client import fetch_files, load_repo
from app.tree_filter import filter_tree


def print_tree(tree):
    for entry in tree:
        if entry["type"] == "blob":
            print(entry["path"])


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Generate a README or onboarding guide for a GitHub repo.")
    parser.add_argument("repo_url", help="e.g. https://github.com/owner/repo")
    parser.add_argument("--mode", choices=["readme", "onboarding"], default="readme")
    parser.add_argument("--max-files", type=int, default=MAX_SELECTED_FILES)
    parser.add_argument("--tree", action="store_true", help="only print the repo's file tree")
    return parser.parse_args(argv)


def run(args):
    repo = load_repo(args.repo_url)
    if args.tree:
        print_tree(repo.tree)
        return

    paths = select_files(filter_tree(repo.tree), mode=args.mode, max_files=args.max_files)
    # Progress goes to stderr so stdout stays clean for `> README.md`.
    print(f"Selected {len(paths)} files: {', '.join(paths)}", file=sys.stderr)

    files = fetch_files(repo, paths)
    for chunk in stream_brief(f"{repo.owner}/{repo.name}", files, mode=args.mode):
        print(chunk, end="", flush=True)
    print()


def main(argv=None):
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    try:
        run(args)
    except (ValueError, RuntimeError, SelectionError, requests.RequestException) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
