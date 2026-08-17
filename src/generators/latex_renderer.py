"""
latex_renderer.py — LaTeX Resume Markup Generator.

Generates Overleaf and pdflatex compatible LaTeX markup from ResumeData model.
"""

from __future__ import annotations

from src.generators.models import ResumeData


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters safely."""
    if not text:
        return ""
    # Escape backslash first to avoid double-escaping
    text = text.replace("\\", "\\textbackslash{}")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("&", "\\&")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_")
    text = text.replace("^", "\\textasciicircum{}")
    text = text.replace("~", "\\textasciitilde{}")
    return text


def render_latex_markup(data: ResumeData) -> str:
    """Generate clean LaTeX markup from ResumeData."""
    name_esc = _escape_latex(data.name)
    title_esc = _escape_latex(data.title)
    email_esc = _escape_latex(data.contact_email)
    phone_esc = _escape_latex(data.contact_phone)
    loc_esc = _escape_latex(data.contact_location)
    summary_esc = _escape_latex(data.summary)

    lines = [
        "\\documentclass[10pt,letterpaper]{article}",
        "\\usepackage[margin=0.5in]{geometry}",
        "\\usepackage{hyperref}",
        "\\usepackage{enumitem}",
        "\\setlist{nosep,leftmargin=*}",
        "\\pagestyle{empty}",
        "\\begin{document}",
        "",
        f"{{\\LARGE \\textbf{{{name_esc}}}}}\\\\",
        f"{{\\large \\textit{{{title_esc}}}}}\\\\",
        f"{email_esc} $\\cdot$ {phone_esc} $\\cdot$ {loc_esc}\\\\",
        "\\vspace{6pt}",
        "\\hrule",
        "\\vspace{6pt}",
        "",
        "\\section*{Professional Summary}",
        summary_esc,
        "",
        "\\section*{Technical Skills}",
        "\\begin{itemize}",
    ]

    for skill in data.skills:
        lines.append(f"  \\item {_escape_latex(skill)}")
    lines.append("\\end{itemize}")
    lines.append("")

    lines.append("\\section*{Professional Experience}")
    for job in data.jobs:
        j_title = _escape_latex(job.title)
        j_comp = _escape_latex(job.company)
        j_dates = _escape_latex(job.dates)
        lines.append(f"\\textbf{{{j_title}}} --- \\textit{{{j_comp}}} \\hfill {j_dates}\\\\")
        lines.append("\\begin{itemize}")
        for bullet in job.bullets:
            clean_b = _escape_latex(bullet.replace("•", "").strip())
            lines.append(f"  \\item {clean_b}")
        lines.append("\\end{itemize}")
        lines.append("\\vspace{4pt}")

    if data.education:
        lines.append("\\section*{Education}")
        lines.append("\\begin{itemize}")
        for edu in data.education:
            lines.append(f"  \\item {_escape_latex(edu)}")
        lines.append("\\end{itemize}")

    lines.append("\\end{document}")
    return "\n".join(lines)
