from app.tree_filter import filter_tree


def blob(path, size=100):
    return {"path": path, "type": "blob", "size": size}


def test_keeps_only_files_not_directories():
    tree = [blob("README.md"), {"path": "src", "type": "tree"}]

    assert filter_tree(tree) == ["README.md"]


def test_drops_binaries_and_media():
    tree = [blob("logo.png"), blob("fonts/a.woff2"), blob("app.py")]

    assert filter_tree(tree) == ["app.py"]


def test_drops_vendor_dirs_at_any_depth():
    tree = [blob("node_modules/x/index.js"), blob("web/node_modules/y.js"), blob("web/app.js")]

    assert filter_tree(tree) == ["web/app.js"]


def test_drops_lockfiles():
    tree = [blob("package-lock.json"), blob("uv.lock"), blob("package.json")]

    assert filter_tree(tree) == ["package.json"]


def test_drops_oversized_files():
    tree = [blob("data.json", size=5_000_000), blob("small.json", size=10)]

    assert filter_tree(tree) == ["small.json"]


def test_cap_keeps_shallowest_paths():
    tree = [blob("a/b/deep.py"), blob("a/mid.py"), blob("top.py")]

    assert filter_tree(tree, max_paths=2) == ["top.py", "a/mid.py"]
