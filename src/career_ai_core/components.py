from html import escape


def _presentation(profile: dict) -> tuple[str, str, str, list[str]]:
    """Resolve candidate-facing UI text without embedding personal information."""
    personal = profile.get("personal") or {}
    display = profile.get("presentation") or {}
    name = str(personal.get("name") or "Candidate")
    title = str(display.get("tagline") or personal.get("professional_title") or "")
    description = str(display.get("description") or profile.get("summary") or "")
    tags = [str(tag) for tag in (display.get("highlights") or []) if tag]
    return name, title, description, tags


def render_profile_header(profile: dict) -> str:
    name, title, description, _ = _presentation(profile)
    return (
        '<div class="hero">'
        f"<h1>{escape(name)}</h1>"
        f'<div class="subtitle">{escape(title)}</div>'
        f'<p class="description">{escape(description)}</p>'
        "</div>"
    )


def render_tech_stack(profile: dict) -> str:
    """Render optional, user-configured technology groups."""
    categories = (profile.get("presentation") or {}).get("tech_groups") or {}
    cards = "".join(
        '<div class="profile-card">'
        f"<h3>{escape(str(category))}</h3>"
        f"<p>{escape(str(technologies))}</p>"
        "</div>"
        for category, technologies in categories.items()
    )
    return f'<div class="profile-grid">{cards}</div>'


def render_experience(experiences: list) -> str:
    companies = []

    for experience in experiences:
        company = escape(experience.get("company", ""))
        role = escape(experience.get("role", ""))

        companies.append(
            f"""
            <div class="experience-item">
                <strong>{company}</strong>
                <span>{role}</span>
            </div>
            """
        )

    return (
        '<div class="experience-section">'
        "<h2>Trayectoria profesional</h2>"
        '<div class="experience-grid">' + "".join(companies) + "</div></div>"
    )


def render_compact_header(profile: dict) -> str:
    name, title, _, tags = _presentation(profile)
    initials = "".join(word[0].upper() for word in name.split()[:3]) or "CV"
    tags_html = "".join(f"<span>{escape(tag)}</span>" for tag in tags)
    return (
        '<div class="compact-header">'
        f'<div class="brand-icon">{escape(initials)}<span>✦</span></div>'
        '<div class="brand-content">'
        f"<h1>{escape(name)}</h1>"
        f"<p>{escape(title)}</p>"
        f'<div class="skill-tags">{tags_html}</div>'
        "</div></div>"
    )


def render_compact_experience(experiences: list) -> str:
    items = []

    for experience in experiences:
        company = escape(str(experience.get("company", "")))
        role = escape(str(experience.get("role", "")))

        period = experience.get("period") or {}
        start = str(period.get("start") or "")[:4]
        end_value = period.get("end")
        end = str(end_value)[:4] if end_value else "Actualidad"

        projects = experience.get("projects") or []

        project_names = ", ".join(
            escape(str(project.get("name", ""))) for project in projects if project.get("name")
        )

        projects_html = (
            f'<p class="career-project-names"><strong>Proyectos:</strong> {project_names}</p>'
            if project_names
            else ""
        )

        items.append(f"""
            <details class="compact-job">
                <summary>
                    <div class="job-summary">
                        <div class="job-name">{company}</div>
                        <div class="job-role">{role}</div>
                        <div class="job-period">
                            {escape(start)} – {escape(end)}
                        </div>
                    </div>
                    <span class="job-chevron"></span>
                </summary>

                <div class="career-details">
                    <p>{escape(str(experience.get("description", "")))}</p>
                    {projects_html}
                    <div class="career-chat-hint">
                        ✦ ¿Quieres saber más? Pregunta al asistente IA.
                    </div>
                </div>
            </details>
        """)

    return (
        '<div class="career-sidebar">'
        '<div class="sidebar-heading">TRAYECTORIA PROFESIONAL</div>' + "".join(items) + "</div>"
    )
