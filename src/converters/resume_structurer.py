"""
resume_structurer.py — Section detection and clean Markdown resume formatting.
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
    "CORE SKILLS & COMPETENCIES",
    "AREAS OF EXPERTISE", "EXPERTISE", "TECHNOLOGIES", "TOOLS",
    # Experience
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE",
    "EMPLOYMENT HISTORY", "CAREER HISTORY", "WORK HISTORY",
    # Education
    "EDUCATION", "ACADEMIC BACKGROUND", "QUALIFICATIONS",
    "ACADEMIC QUALIFICATIONS",
    # Projects
    "PROJECTS", "ACADEMIC PROJECTS", "PERSONAL PROJECTS", "KEY PROJECTS",
    "NOTABLE PROJECTS", "SELECTED PROJECTS",
    # Other
    "CERTIFICATIONS", "CERTIFICATES", "LICENSES", "CREDENTIALS",
    "AWARDS", "HONORS", "ACHIEVEMENTS", "ACCOMPLISHMENTS",
    "PUBLICATIONS", "RESEARCH", "PATENTS",
    "LEADERSHIP", "VOLUNTEER", "COMMUNITY",
    "LANGUAGES", "INTERESTS", "HOBBIES",
}

def clean_text(text: str) -> str:
    """Remove excessive whitespace while preserving line breaks and structure."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()

def is_standard_header(line: str) -> bool:
    """Check if a line matches standard resume section headers."""
    clean_line = re.sub(r"[^A-Za-z0-9&\s/#-]", "", line).strip().upper()
    if clean_line in STANDARD_HEADERS or line.strip().upper() in STANDARD_HEADERS:
        return True
    return False

def structure_resume(raw_text: str) -> str:
    """Structure raw resume text into standardized Markdown sections."""
    lines = [line.strip() for line in raw_text.split("\n")]
    lines = [l for l in lines if l]
    
    if not lines:
        return ""
        
    name = lines[0]
    title = ""
    contact_info = ""
    start_idx = 1
    
    if is_standard_header(name):
        start_idx = 0
        name = "Candidate Resume"
    else:
        # Check if line 2 is title/designation vs section header vs contact
        if len(lines) > 1:
            line2 = lines[1]
            if not is_standard_header(line2):
                email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", line2)
                phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", line2)
                if not (email_match or phone_match or "linkedin.com" in line2.lower() or "github.io" in line2.lower()):
                    title = line2
                    start_idx = 2

        # Check for contact info
        if len(lines) > start_idx and not is_standard_header(lines[start_idx]):
            line_contact = lines[start_idx]
            email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", line_contact)
            phone_match = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", line_contact)
            if email_match or phone_match or "linkedin.com" in line_contact.lower() or "github.io" in line_contact.lower():
                contact_info = line_contact
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
            
    md = []
    md.append(f"# {name}")
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
        for line in section_lines:
            md.append(line)
        md.append("")
        
    return "\n".join(md)
