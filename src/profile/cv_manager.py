"""
CV/Profile data manager
Handles loading, saving, and validating user CV information
"""
from pathlib import Path
from typing import Optional, Dict, Any
import json
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class Education(BaseModel):
    degree: str
    field: str
    university: str
    graduation_year: int
    grade: Optional[str] = None


class Experience(BaseModel):
    company: str
    position: str
    duration_months: int
    description: str
    skills: list[str]
    start_date: str  # Format: YYYY-MM
    end_date: Optional[str] = None  # Format: YYYY-MM or "Present"


class CVProfile(BaseModel):
    """User's CV/Resume data"""
    name: str
    email: EmailStr
    phone: str
    location: str
    country: str
    summary: str
    education: list[Education] = []
    experience: list[Experience] = []
    skills: list[str] = []
    languages: Dict[str, str] = {}  # {language: proficiency_level}
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "+34 600 123 456",
                "location": "Madrid",
                "country": "Spain",
                "summary": "Recent graduate with AI/ML interest",
                "education": [
                    {
                        "degree": "Bachelor",
                        "field": "Computer Science",
                        "university": "University of Madrid",
                        "graduation_year": 2024
                    }
                ],
                "experience": [],
                "skills": ["Python", "ML", "Data Analysis"],
                "languages": {"Spanish": "Native", "English": "Fluent"},
                "linkedin_url": "https://linkedin.com/in/johndoe"
            }
        }


class ProfileManager:
    """Manages CV profile storage and retrieval"""
    
    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.cv_path = self.config_dir / "cv_template.json"
    
    def create_default_cv(self) -> CVProfile:
        """Create a default CV template"""
        return CVProfile(
            name="Your Name",
            email="your.email@example.com",
            phone="+34 600 000 000",
            location="Madrid",
            country="Spain",
            summary="Describe yourself and your internship goals",
            education=[
                Education(
                    degree="Bachelor",
                    field="Computer Science",
                    university="Your University",
                    graduation_year=2025
                )
            ],
            experience=[],
            skills=["Skill 1", "Skill 2", "Skill 3"],
            languages={"Spanish": "Native", "English": "Fluent"}
        )
    
    def save_cv(self, cv: CVProfile) -> None:
        """Save CV profile to JSON file"""
        with open(self.cv_path, 'w', encoding='utf-8') as f:
            json.dump(cv.model_dump(), f, indent=2, ensure_ascii=False)
        print(f"✓ CV saved to {self.cv_path}")
    
    def load_cv(self) -> CVProfile:
        """Load CV profile from JSON file"""
        if not self.cv_path.exists():
            print(f"CV file not found at {self.cv_path}")
            print("Creating default template...")
            cv = self.create_default_cv()
            self.save_cv(cv)
            print("Please edit the CV file with your information.")
            return cv
        
        with open(self.cv_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return CVProfile(**data)
    
    def add_education(self, cv: CVProfile, education: Education) -> CVProfile:
        """Add education entry to CV"""
        cv.education.append(education)
        return cv
    
    def add_experience(self, cv: CVProfile, experience: Experience) -> CVProfile:
        """Add experience entry to CV"""
        cv.experience.append(experience)
        return cv
    
    def update_skills(self, cv: CVProfile, skills: list[str]) -> CVProfile:
        """Update skills list"""
        cv.skills = skills
        return cv
    
    def validate_cv(self, cv: CVProfile) -> tuple[bool, list[str]]:
        """Validate CV completeness and return warnings if needed"""
        warnings = []
        
        if not cv.summary or cv.summary.startswith("Describe"):
            warnings.append("⚠ CV summary is empty or default. Update it for better applications.")
        
        if not cv.experience:
            warnings.append("⚠ No experience added. Some applications may require this.")
        
        if len(cv.skills) < 3:
            warnings.append("⚠ Add more skills for better matching with job listings.")
        
        if not cv.linkedin_url:
            warnings.append("ℹ Consider adding your LinkedIn URL for applications.")
        
        return len(warnings) == 0, warnings


if __name__ == "__main__":
    # Test the profile manager
    manager = ProfileManager()
    cv = manager.load_cv()
    print("\n📄 CV Profile Loaded:")
    print(json.dumps(cv.model_dump(), indent=2, ensure_ascii=False))