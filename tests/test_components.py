"""Unit tests for candidate-specific HTML components and localization."""

from pathlib import Path

import pytest

from career_ai_core import components
from career_ai_core.knowledge import load_knowledge

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-data"


class TestPresentation:
    """Verify profile presentation fallbacks and optional display fields."""

    def test_uses_candidate_defaults_for_empty_profile(self):
        """Use a generic name and empty optional fields when profile data is absent."""
        assert components._presentation({}) == ("Candidate", "", "", [])

    def test_prefers_presentation_fields_over_profile_fallbacks(self):
        """Prioritize explicit presentation fields and ignore empty highlights."""
        profile = {
            "personal": {"name": "Alex", "professional_title": "Engineer"},
            "summary": "Fallback summary",
            "presentation": {
                "tagline": "Architect",
                "description": "Preferred description",
                "highlights": ["Python", "", None, 42],
            },
        }
        assert components._presentation(profile) == (
            "Alex",
            "Architect",
            "Preferred description",
            ["Python", "42"],
        )

    def test_falls_back_to_personal_title_and_summary(self):
        """Use the professional title and summary when presentation fields are missing."""
        profile = {
            "personal": {"name": "Alex", "professional_title": "Engineer"},
            "summary": "Backend developer",
        }
        assert components._presentation(profile) == ("Alex", "Engineer", "Backend developer", [])

    def test_converts_presented_values_to_strings(self):
        """Normalize non-string display values before rendering."""
        assert components._presentation(
            {
                "personal": {"name": 123},
                "presentation": {"tagline": 456, "description": 789},
            }
        ) == ("123", "456", "789", [])


class TestProfileHeader:
    """Verify full profile header content and HTML escaping."""

    def test_renders_candidate_name_title_and_description(self):
        """Include the candidate's public presentation in the full header."""
        html = components.render_profile_header(
            {
                "personal": {"name": "Alex", "professional_title": "Engineer"},
                "summary": "Builds services",
            }
        )
        assert "<h1>Alex</h1>" in html
        assert 'class="subtitle">Engineer' in html
        assert 'class="description">Builds services' in html

    def test_escapes_user_supplied_profile_text(self):
        """Prevent markup injection through name, title, or description."""
        html = components.render_profile_header(
            {
                "personal": {"name": "<script>alert(1)</script>"},
                "presentation": {
                    "tagline": "<b>Engineer</b>",
                    "description": "<img src=x onerror=alert(1)>",
                },
            }
        )
        assert "<script>" not in html
        assert "<b>Engineer</b>" not in html
        assert "<img" not in html
        assert "&lt;script&gt;" in html
        assert "&lt;b&gt;" in html
        assert "&lt;img" in html


class TestTechStack:
    """Verify optional technology group rendering and HTML safety."""

    def test_renders_each_configured_technology_group(self):
        """Create a card for every configured category and technology value."""
        html = components.render_tech_stack(
            {"presentation": {"tech_groups": {"Backend": "Java, Python", "Cloud": "GCP"}}}
        )
        assert html.count('class="profile-card"') == 2
        assert "<h3>Backend</h3>" in html
        assert "<p>Java, Python</p>" in html
        assert "<h3>Cloud</h3>" in html

    @pytest.mark.parametrize(
        "profile", [{}, {"presentation": {}}, {"presentation": {"tech_groups": None}}]
    )
    def test_missing_technology_groups_render_empty_grid(self, profile):
        """Render a valid empty grid when technology groups are not configured."""
        assert components.render_tech_stack(profile) == '<div class="profile-grid"></div>'

    def test_escapes_category_names_and_technology_values(self):
        """Escape both keys and values supplied by the candidate."""
        html = components.render_tech_stack({"presentation": {"tech_groups": {"<b>": "<script>"}}})
        assert "&lt;b&gt;" in html
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestExperience:
    """Verify standard experience cards and localized headings."""

    def test_experience_headings_are_localized(self):
        """Render the correct section heading for English and Spanish."""
        assert "Professional experience" in components.render_experience([], locale="en")
        assert "Trayectoria profesional" in components.render_experience([], locale="es")

    def test_renders_each_company_and_role(self):
        """Render a separate experience item for each company."""
        html = components.render_experience(
            [
                {"company": "First", "role": "Engineer"},
                {"company": "Second", "role": "Architect"},
            ],
            locale="en",
        )
        assert html.count('class="experience-item"') == 2
        assert "<strong>First</strong>" in html
        assert "<span>Architect</span>" in html

    def test_escapes_company_and_role(self):
        """Escape HTML in company and role fields."""
        html = components.render_experience(
            [{"company": "<script>", "role": "<b>Engineer</b>"}], locale="en"
        )
        assert "<script>" not in html
        assert "<b>Engineer</b>" not in html
        assert "&lt;script&gt;" in html

    def test_missing_company_and_role_render_as_empty_text(self):
        """Allow experience entries without optional company and role values."""
        html = components.render_experience([{}], locale="en")
        assert "<strong></strong>" in html
        assert "<span></span>" in html


class TestCompactHeader:
    """Verify compact candidate branding, initials, highlights and escaping."""

    def test_render_is_candidate_specific(self):
        """Display the sample candidate rather than a hardcoded personal identity."""
        html = components.render_compact_header(load_knowledge(SAMPLE)["profile"])
        assert "Alex Example" in html

    def test_initials_use_first_three_name_words(self):
        """Limit brand initials to the first three words of the candidate name."""
        html = components.render_compact_header(
            {
                "personal": {"name": "Alex Beth Casey Davis"},
            }
        )
        assert 'class="brand-icon">ABC' in html

    def test_empty_name_uses_generic_initials(self):
        """Use CV as the initials when the candidate name has no words."""
        html = components.render_compact_header({"personal": {"name": " "}})
        assert 'class="brand-icon">CV' in html

    def test_renders_highlights_as_individual_tags(self):
        """Render nonempty highlights as separate escaped tag elements."""
        html = components.render_compact_header(
            {"presentation": {"highlights": ["Python", "Cloud", None]}}
        )
        assert "<span>Python</span>" in html
        assert "<span>Cloud</span>" in html
        assert "<span>None</span>" not in html

    def test_escapes_compact_header_content(self):
        """Prevent HTML injection through candidate name, tagline and highlights."""
        html = components.render_compact_header(
            {
                "personal": {"name": "<Alex>"},
                "presentation": {"tagline": "<b>Lead</b>", "highlights": ["<script>"]},
            }
        )
        assert "&lt;Alex&gt;" in html
        assert "&lt;b&gt;Lead&lt;/b&gt;" in html
        assert "&lt;script&gt;" in html
        assert "<script>" not in html


class TestCompactExperience:
    """Verify compact experience details, projects, periods and localization."""

    def test_compact_experience_is_localized(self):
        """Use the translated current-position label for open-ended employment."""
        experiences = [{"company": "Example", "role": "Engineer", "period": {"start": "2020"}}]
        assert "Present" in components.render_compact_experience(experiences, locale="en")
        assert "Actualidad" in components.render_compact_experience(experiences, locale="es")

    def test_formats_start_and_end_as_years(self):
        """Display only the year portion of both employment dates."""
        html = components.render_compact_experience(
            [{"company": "Example", "period": {"start": "2020-03", "end": "2024-11"}}], locale="en"
        )
        assert "2020 – 2024" in html
        assert "Present" not in html

    def test_missing_period_uses_current_position(self):
        """Treat a missing employment period as an open-ended position."""
        html = components.render_compact_experience([{}], locale="en")
        assert "Present" in html

    def test_renders_named_projects_but_ignores_unnamed_projects(self):
        """Show the project label only when at least one project has a name."""
        html = components.render_compact_experience(
            [
                {
                    "company": "Example",
                    "projects": [{"name": "Alpha"}, {}, {"name": ""}, {"name": "Beta"}],
                }
            ],
            locale="en",
        )
        assert "Alpha, Beta" in html
        assert "career-project-names" in html

    @pytest.mark.parametrize("projects", [None, [], [{}, {"name": ""}]])
    def test_omits_project_section_when_no_project_is_named(self, projects):
        """Avoid displaying an empty projects section."""
        html = components.render_compact_experience(
            [{"company": "Example", "projects": projects}], locale="en"
        )
        assert "career-project-names" not in html

    def test_escapes_all_candidate_supplied_experience_fields(self):
        """Escape company, role, description, dates and project names."""
        html = components.render_compact_experience(
            [
                {
                    "company": "<script>",
                    "role": "<b>Engineer</b>",
                    "description": "<img src=x>",
                    "period": {"start": "<2020>", "end": "<2024>"},
                    "projects": [{"name": "<Project>"}],
                }
            ],
            locale="en",
        )
        assert "<script>" not in html
        assert "<img" not in html
        assert "&lt;script&gt;" in html
        assert "&lt;b&gt;Engineer&lt;/b&gt;" in html
        assert "&lt;img src=x&gt;" in html
        assert "&lt;20" in html
        assert "&lt;Project&gt;" in html

    def test_empty_experience_list_renders_sidebar_without_jobs(self):
        """Keep the sidebar container when there are no positions to show."""
        html = components.render_compact_experience([], locale="en")
        assert 'class="career-sidebar"' in html
        assert 'class="compact-job"' not in html
