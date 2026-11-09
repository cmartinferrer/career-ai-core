import pytest
from pydantic import ValidationError

from career_ai_core.knowledge import load_markdown, load_yaml
from career_ai_core.models import Skill
from career_ai_core.validator import validate_skill_references


def test_blank_skill_id_uses_english_validation_message():
    with pytest.raises(ValidationError, match="Field must not be blank"):
        Skill(id="   ", name="Python")


def test_missing_yaml_file_uses_english_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="YAML file not found:"):
        load_yaml("missing.yaml", tmp_path)


def test_invalid_yaml_mapping_uses_english_error(tmp_path):
    (tmp_path / "invalid.yaml").write_text("- item\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a mapping"):
        load_yaml("invalid.yaml", tmp_path)


def test_missing_markdown_file_uses_english_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="Markdown file not found:"):
        load_markdown("missing.md", tmp_path)


def test_unknown_company_and_project_skills_use_english_errors():
    knowledge = {
        "skills": {"categories": [{"skills": [{"id": "python"}]}]},
        "experience": {
            "experiences": [
                {
                    "company": "Example Co",
                    "skill_ids": ["unknown-company"],
                    "projects": [{"name": "Demo", "skill_ids": ["unknown-project"]}],
                }
            ]
        },
    }

    with pytest.raises(ValueError) as exc_info:
        validate_skill_references(knowledge)

    message = str(exc_info.value)
    assert "Skill reference validation failed:" in message
    assert "Company 'Example Co': unknown skill 'unknown-company'" in message
    assert "Project 'Demo': unknown skill 'unknown-project'" in message
