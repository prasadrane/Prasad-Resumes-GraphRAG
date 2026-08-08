"""
resume_structurer.py — Section detection and clean Markdown resume formatting.
Applies KISS and YAGNI for clean section header matching.
"""

import re
from typing import Dict, List

STANDARD_HEADERS = {
    # Summary
    "PROFESSIONAL SUMMARY", "SUMMARY", "EXECUTIVE SUMMARY", "OBJECTIVE",
    "CAREER OBJECTIVE", "CAREER SUMMARY", "PROFILE",
    # Skills
    "SKILLS", "TECHNICAL SKILLS", "CORE SKILLS", "KEY SKILLS",
    "COMPETENCIES", "CORE COMPETENCIES", "TECHNICAL COMPETENCIES",
    "TECHNICAL SKILLS & COMPETENCIES", "SKILLS & COMPETENCIES",
    "TECHNICAL SKILLS AND COMPETENCIES", "SKILLS AND COMPETENCIES",
    "CORE SKILLS & COMPETENCIES", "AREAS OF EXPERTISE", "EXPERTISE", "TECHNOLOGIES", "TOOLS",
    # Experience
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE",
    "EMPLOYMENT HISTORY", "CAREER HISTORY", "WORK HISTORY",
    # Education
    "EDUCATION", "ACADEMIC BACKGROUND", "QUALIFICATIONS", "ACADEMIC QUALIFICATIONS",
    # Projects & Credentials
    "PROJECTS", "ACADEMIC PROJECTS", "PERSONAL PROJECTS", "KEY PROJECTS",
    "CERTIFICATIONS", "CERTIFICATES", "LICENSES", "CREDENTIALS",
    "AWARDS", "HONORS", "ACHIEVEMENTS", "PUBLICATIONS", "LEADERSHIP", "LANGUAGES"
}

def clean_text(text: str) -> str:
    """Remove excessive whitespace while preserving line breaks (KISS)."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def is_standard_header(line: str) -> bool:
    """Check if a line matches standard resume section headers (KISS)."""
    if not line or len(line.strip()) > 60:
        return False
    clean_line = re.sub(r"[^A-Za-z0-9&\s/#-]", "", line).strip().upper()
    return clean_line in STANDARD_HEADERS

def structure_resume(raw_text: str) -> str:
    """Structure raw resume text into standardized Markdown sections (KISS)."""
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    if not lines:
        return ""
        
    name = lines[0]
    title = ""
    contact_info = ""
    start_idx = 1
    
    if is_standard_header(name):
        name = "Candidate Resume"
        start_idx = 0
    else:
        if len(lines) > 1 and not is_standard_header(lines[1]):
            line2 = lines[1]
            if not any(token in line2.lower() for token in ["@", "phone", "linkedin", "github"]):
                title = line2
                start_idx = 2

        if len(lines) > start_idx and not is_standard_header(lines[start_idx]):
            contact_info = lines[start_idx]
            start_idx += 1

    sections: Dict[str, List[str]] = {}
    current_section = "Header"
    sections[current_section] = []
    
    for line in lines[start_idx:]:
        if is_standard_header(line):
            current_section = line.strip().upper()
            sections[current_section] = []
        else:
            sections[current_section].append(line)
            
    md = [f"# {name}"]
    if title:
        md.append(f"**Title:** {title}")
    if contact_info:
        md.append(f"**Contact:** {contact_info}")
    md.append("")
    
    for section_name, section_lines in sections.items():
        if section_name == "Header":
            if section_lines:
                md.extend(section_lines)
                md.append("")
            continue
            
        md.append(f"## {section_name}")
        md.append("")
        md.extend(section_lines)
        md.append("")
        
    return "\n".join(md)
