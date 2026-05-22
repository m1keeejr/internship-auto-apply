"""
Tests for the forms automation module (non-browser components)
"""
import pytest
from src.profile.cv_manager import CVProfile, Education
from src.forms.cover_letter import CoverLetterGenerator
from src.forms.form_filler import GenericFormFiller


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def sample_cv():
    return CVProfile(
        name="Maria Garcia",
        email="maria.garcia@example.com",
        phone="+34 600 123 456",
        location="Madrid",
        country="Spain",
        summary="Computer Science student passionate about AI and data science.",
        education=[
            Education(
                degree="Bachelor",
                field="Computer Science",
                university="Universidad Complutense de Madrid",
                graduation_year=2025,
            )
        ],
        experience=[],
        skills=["Python", "SQL", "Machine Learning", "Django", "Git"],
        languages={"Spanish": "Native", "English": "Fluent"},
        linkedin_url="https://linkedin.com/in/mariagarcia",
        github_url="https://github.com/mariagarcia",
    )


@pytest.fixture
def sample_job():
    return {
        "company": "TechCorp Spain",
        "position": "Data Science Internship",
        "description": "Python, pandas, scikit-learn. English required. Madrid.",
        "location": "Madrid",
        "country": "Spain",
        "platform": "linkedin",
    }


# --------------------------------------------------------------------------- #
#  CoverLetterGenerator tests
# --------------------------------------------------------------------------- #

class TestCoverLetterGenerator:
    def test_professional_letter_contains_key_info(self, sample_cv, sample_job):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job, tone="professional")

        assert "Maria Garcia" in letter
        assert "TechCorp Spain" in letter
        assert "Data Science Internship" in letter
        assert "maria.garcia@example.com" in letter
        assert "+34 600 123 456" in letter

    def test_enthusiastic_tone(self, sample_cv, sample_job):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job, tone="enthusiastic")
        assert "TechCorp Spain" in letter
        assert "Maria Garcia" in letter

    def test_concise_tone(self, sample_cv, sample_job):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job, tone="concise")
        # Concise letters should be shorter than professional ones
        professional = gen.generate(sample_cv, sample_job, tone="professional")
        assert len(letter) < len(professional)

    def test_skills_mentioned(self, sample_cv, sample_job):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job)
        # At least some skills should appear
        skill_hits = sum(1 for s in sample_cv.skills[:5] if s in letter)
        assert skill_hits >= 1

    def test_linkedin_url_included(self, sample_cv, sample_job):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job)
        assert "linkedin.com/in/mariagarcia" in letter

    def test_no_job_provided(self, sample_cv):
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, job=None)
        assert "Maria Garcia" in letter
        assert len(letter) > 100

    def test_cv_without_linkedin(self, sample_cv, sample_job):
        sample_cv.linkedin_url = None
        gen = CoverLetterGenerator()
        letter = gen.generate(sample_cv, sample_job)
        assert "linkedin.com" not in letter


# --------------------------------------------------------------------------- #
#  GenericFormFiller — field mapping tests (no browser needed)
# --------------------------------------------------------------------------- #

class TestGenericFormFillerMapping:
    """Test the _map_to_cv logic in isolation using a mock element."""

    class MockElement:
        def __init__(self, name="", id_="", placeholder=""):
            self._attrs = {"name": name, "id": id_, "placeholder": placeholder}

        def get_attribute(self, attr):
            return self._attrs.get(attr, "")

    def _filler(self):
        """Return a filler with a dummy driver (mapping doesn't need one)."""
        class FakeDriver:
            def find_elements(self, *a, **kw): return []
        filler = GenericFormFiller.__new__(GenericFormFiller)
        filler.driver = FakeDriver()
        return filler

    def test_email_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(name="email_address", placeholder="Enter email")
        key, value = filler._map_to_cv("Email", elem, sample_cv)
        assert key == "email"
        assert value == sample_cv.email

    def test_phone_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(name="phone_number")
        key, value = filler._map_to_cv("Phone", elem, sample_cv)
        assert key == "phone"
        assert value == sample_cv.phone

    def test_first_name_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(placeholder="First Name")
        key, value = filler._map_to_cv("First Name", elem, sample_cv)
        assert key == "first_name"
        assert value == "Maria"

    def test_last_name_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(placeholder="Last Name")
        key, value = filler._map_to_cv("Last Name", elem, sample_cv)
        assert key == "last_name"
        assert value == "Garcia"

    def test_city_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(name="city")
        key, value = filler._map_to_cv("City", elem, sample_cv)
        assert key == "city"
        assert value == "Madrid"

    def test_unmapped_field(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(name="some_random_field_xyz")
        key, value = filler._map_to_cv("Random Field", elem, sample_cv)
        assert key == "unmapped"
        assert value is None

    def test_linkedin_mapping(self, sample_cv):
        filler = self._filler()
        elem = self.MockElement(name="linkedin_url")
        key, value = filler._map_to_cv("LinkedIn URL", elem, sample_cv)
        assert key == "linkedin_url"
        assert value == sample_cv.linkedin_url
