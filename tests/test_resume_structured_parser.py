"""Tests for resume_structured_parser — validates parsing of
MASTER_RESUME.txt into ResumeData-shaped dicts."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.converters.resume_structured_parser import parse_master_resume


# Minimal fixture mirroring the real MASTER_RESUME.txt structure.
# Key elements: H1 name, contact line with emoji markers, canonical
# summary, domain variants, skills by category, a cert, education,
# and an experience section with ### company headers and #### story
# subsections separated by --- dividers.
FIXTURE = """\
**Prasad Rane**
📍 Lake Bluff, IL | 📞 513-967-9423 | ✉️ emailprasadrane@gmail.com | 🌐 [LinkedIn](https://linkedin.com/in/rane-prasad) | 💻 [Portfolio](https://prasadrane.io)

---

### Canonical Summary
Software Engineer with **10+ years** of experience.

### Domain-Specific Summary Variants
- **AI / LLM-Forward**: AI summary text here.
- **Cloud & Reliability-Forward**: Cloud summary text here.

---

## 🛠️ Complete Technical Skills Inventory

- **Backend & APIs**: C#, .NET Core, Python
- **Cloud & Infrastructure**: AWS ECS, Lambda, DynamoDB

---

## 🏆 Certifications

- [**AWS Certified Cloud Practitioner**](https://example.com) — Amazon Web Services *(Issued: Apr 2026)*

---

## 💼 Exhaustive Experience & Bullet Library

### **Software Engineer** — *Rocket Mortgage*
📍 *Lake Bluff, IL* | 🗓️ *Jan 2023 – Jul 2025*

#### Story 1 — Observability Integration
- **Diagnosed** a monitoring gap improving accuracy from 60% to 98%.
- **Redesigned** the health-check target reducing alert noise by 80%.

#### Story 2 — Product Configuration Engine
- **Architected** a self-service UI reducing deployment from 14 days to 1 day.

### **Software Developer** — *London Computer Systems*
📍 *Columbus, OH* | 🗓️ *Jun 2020 – Dec 2022*

#### Story 3 — SQL Server Optimization
- **Optimized** database queries cutting response time by 50%.

---

## 🎓 Education

- **M.S. Computer Science** — University of Cincinnati

---

## 📌 Gap-Framing & Skill Triage Cheat Sheet

| Skill | Demand | Coverage |
|-------|--------|----------|
| AWS   | High   | Strong   |
"""


class TestParseMasterResume(unittest.TestCase):
    """Validate parse_master_resume output shape and content."""

    def setUp(self):
        self.result = parse_master_resume(FIXTURE)

    # -- Name / contact --------------------------------------------------

    def test_name_extracted(self):
        # Fixture uses bold format (no H1)
        self.assertEqual(self.result['name'], 'Prasad Rane')

    def test_contact_fields(self):
        self.assertEqual(self.result['contact_phone'], '513-967-9423')
        self.assertIn('emailprasadrane', self.result['contact_email'])
        self.assertIn('linkedin.com', self.result['contact_linkedin'])

    # -- Summary ---------------------------------------------------------

    def test_domain_variants_extracted(self):
        summary = self.result['summary']
        # Summary may be a joined string or list depending on implementation
        self.assertTrue(len(summary) > 0, "summary should not be empty")

    # -- Skills ----------------------------------------------------------

    def test_skills_grouped_by_category(self):
        skills = self.result['skills']
        self.assertIsInstance(skills, dict)
        self.assertIn('Backend & APIs', skills)
        self.assertIn('C#', skills['Backend & APIs'])

    # -- Certifications --------------------------------------------------

    def test_certifications(self):
        certs = self.result['certifications']
        self.assertEqual(len(certs), 1)
        self.assertIn('AWS Certified Cloud Practitioner', certs[0])

    # -- Education -------------------------------------------------------

    def test_education(self):
        edu = self.result['education']
        self.assertEqual(len(edu), 1)
        self.assertIn('M.S.', edu[0])

    # -- Jobs (the bug under fix) ----------------------------------------

    def test_jobs_not_empty(self):
        """_extract_jobs must return at least one job entry."""
        jobs = self.result['jobs']
        self.assertGreater(len(jobs), 0,
            "_extract_jobs returned 0 jobs — regex or loop bug")

    def test_jobs_correct_count_per_story(self):
        """Each #### Story subsection should produce its own job entry."""
        jobs = self.result['jobs']
        # Fixture has 3 stories under 2 companies
        self.assertEqual(len(jobs), 3,
            f"Expected 3 job entries (one per story), got {len(jobs)}")

    def test_job_fields_populated(self):
        """Each job entry must have title, company, location, dates."""
        jobs = self.result['jobs']
        for job in jobs:
            self.assertTrue(job.get('title'), f"job missing title: {job}")
            self.assertTrue(job.get('company'), f"job missing company: {job}")
            self.assertTrue(job.get('location'), f"job missing location: {job}")
            self.assertTrue(job.get('dates'), f"job missing dates: {job}")

    def test_job_bullets_attached(self):
        """Bullets under each story must be captured."""
        jobs = self.result['jobs']
        for job in jobs:
            self.assertGreater(len(job.get('bullets', [])), 0,
                f"job '{job.get('heading')}' has no bullets")

    def test_company_inheritance(self):
        """Stories under the same company share title/company/location/dates."""
        jobs = self.result['jobs']
        rocket_jobs = [j for j in jobs if 'Rocket' in j.get('company', '')]
        self.assertEqual(len(rocket_jobs), 2)
        for j in rocket_jobs:
            self.assertEqual(j['title'], 'Software Engineer')
            self.assertEqual(j['company'], 'Rocket Mortgage')

    def test_heading_captures_story_title(self):
        """Each job's heading should reflect its #### Story title."""
        jobs = self.result['jobs']
        headings = [j['heading'] for j in jobs]
        self.assertTrue(any('Observability' in h for h in headings),
            f"Expected 'Observability' in a heading, got: {headings}")


class TestParseRealResume(unittest.TestCase):
    """Integration test: parse the actual MASTER_RESUME.txt if present."""

    RESUME_PATH = os.path.join(
        os.path.dirname(__file__), '..', 'input', 'MASTER_RESUME.txt'
    )

    @unittest.skipUnless(
        os.path.exists(RESUME_PATH),
        "input/MASTER_RESUME.txt not found"
    )
    def test_real_resume_produces_jobs(self):
        with open(self.RESUME_PATH, encoding='utf-8') as f:
            raw = f.read()
        result = parse_master_resume(raw)
        self.assertGreater(len(result['jobs']), 0,
            "Real resume produced 0 jobs")
        # The real resume has 16 stories across 4 companies
        self.assertGreaterEqual(len(result['jobs']), 10,
            f"Expected >=10 stories, got {len(result['jobs'])}")


if __name__ == '__main__':
    unittest.main()
