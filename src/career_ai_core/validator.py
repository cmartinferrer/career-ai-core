def validate_skill_references(knowledge: dict) -> None:
    """Check that company and project skill IDs exist in the skill catalog."""

    skills = knowledge["skills"]
    experience = knowledge["experience"]

    valid_skill_ids = {
        skill["id"] for category in skills["categories"] for skill in category["skills"]
    }

    errors = []

    def check_references(entity: dict, entity_name: str) -> None:
        """Collect unresolved skill references for a company or project."""
        for skill_id in entity.get("skill_ids", []):
            if skill_id not in valid_skill_ids:
                errors.append(f"{entity_name}: skill desconocida '{skill_id}'")

    for company in experience["experiences"]:
        check_references(company, f"Empresa '{company['company']}'")

        for project in company.get("projects", []):
            check_references(project, f"Proyecto '{project['name']}'")

    if errors:
        raise ValueError("Errores de validación:\n" + "\n".join(errors))
