"""Tests for career_ai_core.models."""

import pytest
from pydantic import ValidationError

from career_ai_core.models import Skill


def test_blank_skill_id_uses_english_validation_message():
    with pytest.raises(ValidationError, match="Field must not be blank"):
        Skill(id="   ", name="Python")
