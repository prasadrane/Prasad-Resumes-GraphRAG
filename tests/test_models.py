"""
Unit tests for src/generators/models.py (Pydantic resume data models).
"""

import unittest
from src.generators.models import JobEntry, ResumeData


class TestJobEntry(unittest.TestCase):

    def test_defaults(self):
        job = JobEntry()
        self.assertEqual(job.heading, "")
        self.assertEqual(job.title, "")
        self.assertEqual(job.company, "")
        self.assertEqual(job.location, "")
        self.assertEqual(job.dates, "")
        self.assertEqual(job.bullets, [])
        self.assertEqual(job.bullet_stories, [])

    def test_mutable_default_isolation(self):
        first, second = JobEntry(), JobEntry()
        first.bullets.append("Did things")
        first.bullet_stories.append("Story")
        self.assertEqual(second.bullets, [])
        self.assertEqual(second.bullet_stories, [])

    def test_field_assignment(self):
        job = JobEntry(
            heading="Engineer | Co | 2020",
            title="Engineer",
            company="Co",
            location="Remote",
            dates="2020 - Present",
            bullets=["Built X"],
        )
        self.assertEqual(job.title, "Engineer")
        self.assertEqual(job.company, "Co")
        self.assertEqual(job.bullets, ["Built X"])


class TestResumeData(unittest.TestCase):

    def test_defaults(self):
        data = ResumeData()
        self.assertEqual(data.name, "")
        self.assertEqual(data.summary, "")
        self.assertEqual(data.jobs, [])
        self.assertEqual(data.skills, [])
        self.assertEqual(data.certifications, [])
        self.assertEqual(data.education, [])

    def test_jobs_list_isolation(self):
        first, second = ResumeData(), ResumeData()
        first.jobs.append(JobEntry(company="A"))
        self.assertEqual(second.jobs, [])

    def test_round_trip(self):
        original = ResumeData(
            name="Alex Smith",
            jobs=[JobEntry(title="Lead", company="Google", bullets=["Led"])],
            skills=["Python"],
        )
        dumped = original.model_dump()
        restored = ResumeData.model_validate(dumped)
        self.assertEqual(restored.name, "Alex Smith")
        self.assertEqual(restored.jobs[0].company, "Google")
        self.assertEqual(restored.skills, ["Python"])


if __name__ == "__main__":
    unittest.main()
