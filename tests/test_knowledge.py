"""Tests for secure knowledge-file loading and skill enrichment."""

from pathlib import Path
from unittest.mock import Mock, call

import pytest

from career_ai_core import knowledge as knowledge_module
from career_ai_core.knowledge import load_knowledge, load_markdown, load_yaml

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-data"


class TestKnowledgePaths:
    """Verify configuration and filesystem boundaries for knowledge files."""

    def test_default_data_dir_uses_environment_variable(self, monkeypatch, tmp_path):
        """Resolve the consumer's data directory from CAREER_AI_DATA_DIR."""
        monkeypatch.setenv("CAREER_AI_DATA_DIR", str(tmp_path))
        assert knowledge_module.default_data_dir() == tmp_path

    def test_missing_configuration_is_explicit(self, monkeypatch):
        """Reject implicit knowledge loading when no directory is configured."""
        monkeypatch.delenv("CAREER_AI_DATA_DIR", raising=False)
        with pytest.raises(ValueError, match="CAREER_AI_DATA_DIR"):
            load_knowledge()

    def test_explicit_directory_does_not_require_environment_variable(self, monkeypatch, tmp_path):
        """Allow an explicit data directory without global configuration."""
        monkeypatch.delenv("CAREER_AI_DATA_DIR", raising=False)
        (tmp_path / "profile.yaml").write_text("name: Example\n", encoding="utf-8")
        assert load_yaml("profile.yaml", tmp_path) == {"name": "Example"}

    @pytest.mark.parametrize("loader", [load_yaml, load_markdown])
    def test_parent_directory_escape_is_rejected(self, loader, tmp_path: Path):
        """Prevent traversal to a parent directory outside the knowledge root."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (tmp_path / "secret.md").write_text("private", encoding="utf-8")
        with pytest.raises(ValueError, match="escapes the configured directory"):
            loader("../secret.md", data_dir)

    @pytest.mark.parametrize("loader", [load_yaml, load_markdown])
    def test_absolute_paths_are_rejected(self, loader, tmp_path: Path):
        """Reject absolute paths even when they point to existing files."""
        outside = tmp_path / "secret.md"
        outside.write_text("private", encoding="utf-8")
        with pytest.raises(ValueError, match="Absolute data file paths"):
            loader(str(outside), tmp_path / "data")

    @pytest.mark.parametrize("loader", [load_yaml, load_markdown])
    def test_symlinks_outside_data_directory_are_rejected(self, loader, tmp_path: Path):
        """Reject symlinks whose resolved target escapes the knowledge root."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        outside = tmp_path / "secret.md"
        outside.write_text("private", encoding="utf-8")
        (data_dir / "linked.md").symlink_to(outside)
        with pytest.raises(ValueError, match="escapes the configured directory"):
            loader("linked.md", data_dir)

    def test_symlink_inside_data_directory_is_allowed(self, tmp_path: Path):
        """Allow symlinks that resolve to another file inside the knowledge root."""
        (tmp_path / "target.md").write_text("allowed", encoding="utf-8")
        (tmp_path / "linked.md").symlink_to(tmp_path / "target.md")
        assert load_markdown("linked.md", tmp_path) == "allowed"


class TestYamlLoading:
    """Verify YAML mapping requirements and file-loading failures."""

    def test_yaml_file_inside_data_directory(self, tmp_path: Path):
        """Read a valid YAML mapping from the knowledge directory."""
        (tmp_path / "profile.yaml").write_text("name: Example\n", encoding="utf-8")
        assert load_yaml("profile.yaml", tmp_path) == {"name": "Example"}

    def test_missing_yaml_file_uses_english_error(self, tmp_path):
        """Raise a descriptive English error when the YAML file is absent."""
        with pytest.raises(FileNotFoundError, match="YAML file not found:"):
            load_yaml("missing.yaml", tmp_path)

    @pytest.mark.parametrize("content", ["- item\n", "", "null\n", "hello\n"])
    def test_non_mapping_yaml_is_rejected(self, tmp_path, content):
        """Reject YAML documents that do not deserialize to dictionaries."""
        (tmp_path / "invalid.yaml").write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match="must contain a mapping"):
            load_yaml("invalid.yaml", tmp_path)

    def test_empty_yaml_mapping_is_allowed(self, tmp_path):
        """Accept an empty YAML mapping as a valid dictionary."""
        (tmp_path / "empty.yaml").write_text("{}\n", encoding="utf-8")
        assert load_yaml("empty.yaml", tmp_path) == {}


class TestMarkdownLoading:
    """Verify Markdown text loading and missing-file errors."""

    def test_nested_markdown_path_inside_data_directory(self, tmp_path: Path):
        """Read Markdown files in nested directories within the knowledge root."""
        projects = tmp_path / "projects"
        projects.mkdir()
        (projects / "sample.md").write_text("# Sample", encoding="utf-8")
        assert load_markdown("projects/sample.md", tmp_path) == "# Sample"

    def test_missing_markdown_file_uses_english_error(self, tmp_path):
        """Raise a descriptive English error when the Markdown file is absent."""
        with pytest.raises(FileNotFoundError, match="Markdown file not found:"):
            load_markdown("missing.md", tmp_path)

    def test_markdown_preserves_unicode_and_line_breaks(self, tmp_path):
        """Return Markdown text unchanged, including Unicode and newlines."""
        content = "# Experiencia\n\nDescripción técnica.\n"
        (tmp_path / "details.md").write_text(content, encoding="utf-8")
        assert load_markdown("details.md", tmp_path) == content


class TestKnowledgeAssembly:
    """Verify validation, skill resolution, and optional project details."""

    def test_sample_candidate_loads(self):
        """Load the distributed sample candidate as an integration smoke test."""
        knowledge = load_knowledge(SAMPLE)
        assert knowledge["profile"]["personal"]["name"] == "Alex Example"

    def test_loads_and_enriches_companies_and_projects(self, monkeypatch, tmp_path):
        """Validate skills before resolving IDs and load only configured details."""
        raw = {
            "profile.yaml": {"name": "Example"},
            "experience.yaml": {
                "experiences": [
                    {
                        "skill_ids": ["python"],
                        "projects": [
                            {"skill_ids": ["java"], "details_file": "projects/one.md"},
                            {"skill_ids": []},
                            {},
                        ],
                    },
                    {"projects": []},
                ]
            },
            "skills.yaml": {"categories": [{"skills": [{"id": "python"}, {"id": "java"}]}]},
        }
        load = Mock(side_effect=lambda filename, data_dir: raw[filename])
        validate = Mock(side_effect=lambda skills: skills)
        check = Mock()
        index = Mock(return_value={"python": {"id": "python"}, "java": {"id": "java"}})
        resolve = Mock(side_effect=lambda ids, lookup: [lookup[key].copy() for key in ids])
        markdown = Mock(return_value="# Details")
        monkeypatch.setattr(knowledge_module, "load_yaml", load)
        monkeypatch.setattr(knowledge_module, "validate_skills", validate)
        monkeypatch.setattr(knowledge_module, "validate_skill_references", check)
        monkeypatch.setattr(knowledge_module, "build_skill_index", index)
        monkeypatch.setattr(knowledge_module, "resolve_skills", resolve)
        monkeypatch.setattr(knowledge_module, "load_markdown", markdown)

        result = load_knowledge(tmp_path)

        assert load.call_args_list == [
            call("profile.yaml", tmp_path),
            call("experience.yaml", tmp_path),
            call("skills.yaml", tmp_path),
        ]
        validate.assert_called_once_with(raw["skills.yaml"])
        check.assert_called_once_with(result)
        index.assert_called_once_with(raw["skills.yaml"])
        assert [args.args[0] for args in resolve.call_args_list] == [
            ["python"],  # First company's skills
            ["java"],  # First project's skills
            [],  # Second project's skills
            [],  # Third project's skills
            [],  # Second company's skills
        ]
        companies = result["experience"]["experiences"]
        assert companies[0]["resolved_skills"] == [{"id": "python"}]
        assert companies[0]["projects"][0]["resolved_skills"] == [{"id": "java"}]
        assert companies[0]["projects"][0]["details"] == "# Details"
        assert companies[0]["projects"][1]["resolved_skills"] == []
        assert companies[0]["projects"][2]["resolved_skills"] == []
        assert companies[1]["resolved_skills"] == []
        markdown.assert_called_once_with("projects/one.md", tmp_path)

    def test_validation_failure_stops_skill_resolution(self, monkeypatch):
        """Propagate invalid skill references before building a skill index."""
        raw = {
            "profile.yaml": {},
            "experience.yaml": {"experiences": []},
            "skills.yaml": {"categories": []},
        }
        monkeypatch.setattr(knowledge_module, "load_yaml", lambda filename, data_dir: raw[filename])
        monkeypatch.setattr(knowledge_module, "validate_skills", lambda skills: skills)
        index = Mock()
        monkeypatch.setattr(knowledge_module, "build_skill_index", index)

        def reject(_knowledge):
            raise ValueError("Invalid skill reference")

        monkeypatch.setattr(knowledge_module, "validate_skill_references", reject)

        with pytest.raises(ValueError, match="Invalid skill reference"):
            load_knowledge("unused")

        index.assert_not_called()
