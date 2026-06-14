"""Regression tests for project naming consistency in repository text files."""

from pathlib import Path


FORBIDDEN_NAME_FRAGMENT = "code" + "-" + "ass"
EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "dist",
    "htmlcov",
}


def iter_repository_files(root: Path):
    """Yield repository files that should be checked for stale naming."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if EXCLUDED_DIRECTORIES.intersection(path.relative_to(root).parts):
            continue
        yield path


def read_text_if_possible(path: Path):
    """Return file text when it is UTF-8 text, otherwise skip binary files."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def find_forbidden_name_fragment(root: Path):
    """Return path:line matches for stale case-insensitive project name fragments."""
    matches = []
    for path in iter_repository_files(root):
        text = read_text_if_possible(path)
        if text is None:
            continue

        relative_path = path.relative_to(root)
        for line_number, line in enumerate(text.splitlines(), start=1):
            if FORBIDDEN_NAME_FRAGMENT in line.lower():
                matches.append(f"{relative_path}:{line_number}: {line}")
    return matches


def test_repository_text_files_do_not_use_stale_project_name_prefix():
    """Prevent regressions to the old hyphenated project-name prefix."""
    repository_root = Path(__file__).resolve().parents[1]

    matches = find_forbidden_name_fragment(repository_root)

    assert matches == [], "Found stale project-name references:\n" + "\n".join(matches)
