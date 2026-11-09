"""Security tests for candidate data file resolution."""

from pathlib import Path

import pytest

from career_ai_core.knowledge import load_markdown, load_yaml


def test_nested_markdown_path_inside_data_directory(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "sample.md").write_text("# Sample", encoding="utf-8")

    assert load_markdown("projects/sample.md", tmp_path) == "# Sample"


def test_yaml_file_inside_data_directory(tmp_path: Path) -> None:
    (tmp_path / "profile.yaml").write_text("name: Example\n", encoding="utf-8")

    assert load_yaml("profile.yaml", tmp_path) == {"name": "Example"}


@pytest.mark.parametrize("loader", [load_yaml, load_markdown])
def test_parent_directory_escape_is_rejected(loader, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (tmp_path / "secret.md").write_text("private", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes the configured directory"):
        loader("../secret.md", data_dir)


@pytest.mark.parametrize("loader", [load_yaml, load_markdown])
def test_absolute_paths_are_rejected(loader, tmp_path: Path) -> None:
    outside = tmp_path / "secret.md"
    outside.write_text("private", encoding="utf-8")

    with pytest.raises(ValueError, match="Absolute data file paths"):
        loader(str(outside), tmp_path / "data")


@pytest.mark.parametrize("loader", [load_yaml, load_markdown])
def test_symlinks_outside_data_directory_are_rejected(loader, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    outside = tmp_path / "secret.md"
    outside.write_text("private", encoding="utf-8")
    (data_dir / "linked.md").symlink_to(outside)

    with pytest.raises(ValueError, match="escapes the configured directory"):
        loader("linked.md", data_dir)


def test_symlink_inside_data_directory_is_allowed(tmp_path: Path) -> None:
    (tmp_path / "target.md").write_text("allowed", encoding="utf-8")
    (tmp_path / "linked.md").symlink_to(tmp_path / "target.md")

    assert load_markdown("linked.md", tmp_path) == "allowed"
