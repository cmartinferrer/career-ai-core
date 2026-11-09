from pydantic import BaseModel, ConfigDict, Field, field_validator


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    level: str | None = None
    versions: list[str] | None = None
    description: str | None = None

    @field_validator("id", "name")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El campo no puede estar vacío")

        return value.strip()
