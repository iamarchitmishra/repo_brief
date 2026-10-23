from pathlib import PurePosixPath

SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", "vendor",
    "dist", "build", "target", "coverage", ".next", ".idea", ".vscode",
}
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".tgz", ".7z", ".jar", ".war",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".pyc", ".class",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".mov", ".wav",
    ".min.js", ".map",
}
LOCKFILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Pipfile.lock", "Gemfile.lock", "Cargo.lock", "composer.lock", "go.sum",
}
MAX_FILE_BYTES = 500_000
MAX_PATHS = 1500


def filter_tree(tree, max_paths=MAX_PATHS):
    """Return file paths worth showing the LLM, shallowest first, capped at max_paths."""
    paths = [
        entry["path"]
        for entry in tree
        if entry.get("type") == "blob" and not _should_skip(entry["path"], entry.get("size", 0))
    ]
    # When we have to cut, keep top-level files: they say the most about a repo.
    paths.sort(key=lambda path: (path.count("/"), path))
    return paths[:max_paths]


def _should_skip(path, size):
    pure = PurePosixPath(path)
    if any(part in SKIP_DIRS for part in pure.parts[:-1]):
        return True
    if pure.name in LOCKFILES:
        return True
    if any(pure.name.endswith(ext) for ext in SKIP_EXTENSIONS):
        return True
    return size > MAX_FILE_BYTES
