"""Unit tests for skill indexing, resolution, and validation.

These tests verify the public behavior of career_ai_core.skills using small,
isolated datasets rather than candidate-specific knowledge files.
"""

from unittest.mock import Mock

import pytest

from career_ai_core import skills as skills_module


class TestBuildSkillIndex:
    """Verify how categorized skills are indexed by identifier."""

    def test_indexes_skills_across_multiple_categories(self):
        """Include skills from every category and preserve their attributes."""
        python = {"id": "python", "name": "Python"}
        java = {"id": "java", "name": "Java"}
        data = {
            "categories": [
                {"id": "languages", "skills": [python, java]},
                {"id": "tools", "skills": [{"id": "docker", "name": "Docker"}]},
            ]
        }

        result = skills_module.build_skill_index(data)

        assert result == {
            "python": python,
            "java": java,
            "docker": {"id": "docker", "name": "Docker"},
        }
        assert result["python"] is python

    def test_returns_empty_index_for_empty_categories(self):
        """Return an empty index when there are no skill categories."""
        assert skills_module.build_skill_index({"categories": []}) == {}

    def test_ignores_categories_without_skills(self):
        """Skip categories whose skills collection is empty."""
        data = {"categories": [{"id": "empty", "skills": []}]}

        assert skills_module.build_skill_index(data) == {}

    def test_last_duplicate_identifier_takes_precedence(self):
        """Use the last encountered skill when identifiers are duplicated."""
        data = {
            "categories": [
                {"skills": [{"id": "python", "name": "First"}]},
                {"skills": [{"id": "python", "name": "Second"}]},
            ]
        }

        assert skills_module.build_skill_index(data)["python"]["name"] == "Second"

    def test_requires_categories_collection(self):
        """Raise KeyError when the required categories field is absent."""
        with pytest.raises(KeyError, match="categories"):
            skills_module.build_skill_index({})


class TestResolveSkills:
    """Verify skill lookup, ordering, and independence of returned dictionaries."""

    def test_resolves_identifiers_in_requested_order(self):
        """Return matching skills in the same order as the requested IDs."""
        index = {
            "python": {"id": "python", "name": "Python"},
            "java": {"id": "java", "name": "Java"},
        }

        result = skills_module.resolve_skills(["java", "python"], index)

        assert [skill["id"] for skill in result] == ["java", "python"]

    def test_returns_empty_list_for_no_identifiers(self):
        """Return no skills when the requested identifier list is empty."""
        assert skills_module.resolve_skills([], {"python": {"id": "python"}}) == []

    def test_returns_independent_top_level_dictionaries(self):
        """Ensure modifying a resolved skill does not change the indexed skill."""
        index = {"python": {"id": "python", "name": "Python"}}

        result = skills_module.resolve_skills(["python"], index)
        result[0]["name"] = "Changed"

        assert index["python"]["name"] == "Python"
        assert result[0] is not index["python"]

    def test_returns_distinct_dictionaries_for_repeated_identifiers(self):
        """Create a separate dictionary for each occurrence of the same skill ID."""
        index = {"python": {"id": "python", "name": "Python"}}

        result = skills_module.resolve_skills(["python", "python"], index)

        assert result[0] == result[1]
        assert result[0] is not result[1]

    def test_raises_key_error_for_unknown_identifier(self):
        """Propagate KeyError when a requested skill is missing from the index."""
        with pytest.raises(KeyError, match="missing"):
            skills_module.resolve_skills(["missing"], {})


class TestValidateSkills:
    """Verify Pydantic delegation and normalized category structure."""

    def test_validates_every_skill_and_preserves_metadata(self, monkeypatch):
        """Validate each skill and retain top-level and category metadata."""
        validated_inputs = []

        def fake_model_validate(data):
            validated_inputs.append(data)
            return Mock(model_dump=Mock(return_value={"id": data["id"], "name": "Normalized"}))

        monkeypatch.setattr(skills_module.Skill, "model_validate", fake_model_validate)
        data = {
            "version": "1",
            "categories": [
                {"id": "languages", "label": "Languages", "skills": [{"id": "python"}]},
                {"id": "tools", "label": "Tools", "skills": [{"id": "docker"}]},
            ],
        }

        result = skills_module.validate_skills(data)

        assert validated_inputs == [{"id": "python"}, {"id": "docker"}]
        assert result == {
            "version": "1",
            "categories": [
                {
                    "id": "languages",
                    "label": "Languages",
                    "skills": [{"id": "python", "name": "Normalized"}],
                },
                {
                    "id": "tools",
                    "label": "Tools",
                    "skills": [{"id": "docker", "name": "Normalized"}],
                },
            ],
        }

    def test_excludes_none_values_when_serializing(self, monkeypatch):
        """Request Pydantic serialization with exclude_none enabled."""
        validated_skill = Mock()
        validated_skill.model_dump.return_value = {"id": "python"}
        validator = Mock(return_value=validated_skill)
        monkeypatch.setattr(skills_module.Skill, "model_validate", validator)

        result = skills_module.validate_skills(
            {"categories": [{"skills": [{"id": "python", "description": None}]}]}
        )

        validator.assert_called_once_with({"id": "python", "description": None})
        validated_skill.model_dump.assert_called_once_with(exclude_none=True)
        assert result["categories"][0]["skills"] == [{"id": "python"}]

    def test_preserves_empty_categories_and_skill_lists(self):
        """Preserve the structure of categories that contain no skills."""
        data = {"version": "1", "categories": [{"id": "empty", "skills": []}]}

        result = skills_module.validate_skills(data)

        assert result == data
        assert result is not data
        assert result["categories"] is not data["categories"]
        assert result["categories"][0] is not data["categories"][0]

    def test_propagates_validation_failures(self, monkeypatch):
        """Do not suppress errors raised while validating a skill."""
        validator = Mock(side_effect=ValueError("Invalid skill"))
        monkeypatch.setattr(skills_module.Skill, "model_validate", validator)

        with pytest.raises(ValueError, match="Invalid skill"):
            skills_module.validate_skills({"categories": [{"skills": [{"id": "bad"}]}]})

    def test_requires_categories_collection(self):
        """Raise KeyError when the required categories field is absent."""
        with pytest.raises(KeyError, match="categories"):
            skills_module.validate_skills({})
