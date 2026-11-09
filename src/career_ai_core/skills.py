from career_ai_core.models import Skill


def build_skill_index(skills_data: dict) -> dict:
    """Build a lookup of skills keyed by their identifiers."""

    return {
        skill["id"]: skill for category in skills_data["categories"] for skill in category["skills"]
    }


def resolve_skills(skill_ids: list[str], skill_index: dict) -> list[dict]:
    """Resolve skill identifiers to independent skill dictionaries."""

    return [skill_index[skill_id].copy() for skill_id in skill_ids]


def validate_skills(skills_data: dict) -> dict:
    """Validate skills with Pydantic and return normalized dictionaries."""

    validated_data = {
        **skills_data,
        "categories": [],
    }

    for category in skills_data["categories"]:
        validated_category = {
            **category,
            "skills": [],
        }

        for skill_data in category["skills"]:
            skill = Skill.model_validate(skill_data)

            validated_category["skills"].append(skill.model_dump(exclude_none=True))

        validated_data["categories"].append(validated_category)

    return validated_data
