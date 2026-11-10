"""Tests for career_ai_core.validator or its public behavior."""

import pytest

from career_ai_core.validator import validate_skill_references


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
