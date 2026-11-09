import os
from pathlib import Path

import yaml

from career_ai_core.skills import build_skill_index, resolve_skills, validate_skills
from career_ai_core.validator import validate_skill_references


def default_data_dir() -> Path:
    """Resolve the consuming application knowledge directory."""
    configured = os.getenv("CAREER_AI_DATA_DIR")
    if not configured:
        raise ValueError("CAREER_AI_DATA_DIR is required when no data_dir is supplied")
    return Path(configured)


def load_knowledge(data_dir: str | Path | None = None) -> dict:
    """Load candidate knowledge from a configurable data directory."""
    knowledge = {
        "profile": load_yaml("profile.yaml", data_dir),
        "experience": load_yaml("experience.yaml", data_dir),
        "skills": load_yaml("skills.yaml", data_dir),
    }

    # Validación de estructura y tipos con Pydantic
    knowledge["skills"] = validate_skills(knowledge["skills"])

    # Validamos las referencias antes de resolverlas
    validate_skill_references(knowledge)

    # Construimos el índice de tecnologías
    skill_index = build_skill_index(knowledge["skills"])

    for company in knowledge["experience"]["experiences"]:
        # Tecnologías de la empresa
        company["resolved_skills"] = resolve_skills(
            company.get("skill_ids", []),
            skill_index,
        )

        for project in company.get("projects", []):
            # Tecnologías del proyecto
            project["resolved_skills"] = resolve_skills(
                project.get("skill_ids", []),
                skill_index,
            )

            # Documentación Markdown
            details_file = project.get("details_file")

            if details_file:
                project["details"] = load_markdown(details_file, data_dir)

    return knowledge


def load_yaml(filename: str, data_dir: str | Path | None = None) -> dict:
    """Carga un fichero YAML desde el directorio data."""

    file_path = (Path(data_dir) if data_dir is not None else default_data_dir()) / filename

    if not file_path.is_file():
        raise FileNotFoundError(f"No se encuentra el fichero: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"El fichero {filename} debe contener un objeto YAML.")

    return data


def load_markdown(filename: str, data_dir: str | Path | None = None) -> str:
    """Carga un documento Markdown desde data/."""

    file_path = (Path(data_dir) if data_dir is not None else default_data_dir()) / filename

    if not file_path.is_file():
        raise FileNotFoundError(f"No se encuentra el documento: {file_path}")

    return file_path.read_text(encoding="utf-8")
