"""Distribution integrity checks that do not require calling Gemini."""

import importlib.util
from pathlib import Path
from zipfile import ZipFile

import pytest

from career_ai_core.styles import load_styles
from career_ai_core.voice import load_voice_js


def test_packaged_assets_are_readable() -> None:
    assert load_styles().strip()
    assert "<script>" in load_voice_js()
    assert "</script>" in load_voice_js()


def test_bundled_translation_catalogs_are_readable() -> None:
    from importlib.resources import files

    for language in ("en", "es"):
        contents = files("career_ai_core").joinpath("i18n", f"{language}.py").read_text("utf-8")
        assert contents.strip()


def test_wheel_verification_detects_missing_files(tmp_path: Path) -> None:
    verify_wheel = load_verify_distribution().verify_wheel

    wheel = tmp_path / "incomplete.whl"
    with ZipFile(wheel, "w") as archive:
        archive.writestr("career_ai_core/__init__.py", "pass\n")
    with pytest.raises(ValueError, match="missing required files"):
        verify_wheel(wheel)


def test_wheel_verification_accepts_complete_wheel(tmp_path: Path) -> None:
    module = load_verify_distribution()
    REQUIRED_FILES = module.REQUIRED_FILES
    verify_wheel = module.verify_wheel

    wheel = tmp_path / "complete.whl"
    with ZipFile(wheel, "w") as archive:
        for name in REQUIRED_FILES:
            archive.writestr(name, "example\n")
        archive.writestr("career_ai_core-0.1.0.dist-info/entry_points.txt", "[console_scripts]\n")
    verify_wheel(wheel)


def load_verify_distribution():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "verify_distribution.py"

    spec = importlib.util.spec_from_file_location("verify_distribution", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load distribution verification script")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
