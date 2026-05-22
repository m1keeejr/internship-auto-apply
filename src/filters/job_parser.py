"""
Job requirements parser
Extracts and analyzes job characteristics including language, hours, location, etc.
"""
import re
import logging
from typing import Dict, Optional, Set, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JobRequirements:
    """Extracted job requirements"""
    languages: Set[str]  # {English, Spanish, French, etc.}
    language_proficiency: Dict[str, str]  # {English: fluent, Spanish: basic}
    location: str
    country: str
    city: str
    hours_per_week: Optional[int]
    hours_type: str  # 'full-time', 'part-time', 'flexible', 'unknown'
    employment_type: str  # 'internship', 'contract', etc.
    remote_type: str  # 'on-site', 'hybrid', 'remote'
    skills_required: Set[str]
    skills_nice_to_have: Set[str]
    experience_level: str  # 'entry-level', 'mid-level', 'senior'
    salary: Optional[str]
    duration_months: Optional[int]
    is_paid: bool


class JobRequirementsParser:
    """Parses job descriptions to extract requirements"""
    
    # Language patterns
    ENGLISH_PATTERNS = [
        r"\benglish\b", r"\bengles\b", r"\bfluent\s+english\b",
        r"\badvanced\s+english\b", r"\bworking\s+english\b",
        r"\bbilingue.*english\b", r"\benglish\s+(required|essential|needed)",
    ]
    
    SPANISH_PATTERNS = [
        r"\bspanish\b", r"\bspañol\b", r"\bfluent\s+spanish\b",
        r"\badvanced\s+spanish\b", r"\bnative\s+spanish\b",
        r"\bbilingue.*spanish\b", r"\bspanish\s+(required|essential|needed)",
    ]
    
    # Hours patterns
    HOURS_PATTERNS = [
        (r"(\d+)\s*(?:horas?|hours?)\s*(?:a la semana|per week|a week|/week|pw)", "hours_per_week"),
        (r"(\d+)\s*h/week", "hours_per_week"),
        (r"(\d+)\s*h\.?\s*s", "hours_per_week"),
    ]
    
    # Employment type patterns
    FULL_TIME_PATTERNS = [
        r"\bfull.?time\b", r"\bfull-time\b", r"\ba tiempo completo\b",
        r"\b40\s*(?:horas?|hours?)", r"\bjornada\s+completa\b"
    ]
    
    PART_TIME_PATTERNS = [
        r"\bpart.?time\b", r"\bpart-time\b", r"\ba tiempo parcial\b",
        r"\b20\s*(?:horas?|hours?)", r"\b30\s*(?:horas?|hours?)"
    ]
    
    FLEXIBLE_PATTERNS = [
        r"\bflexible\s+hours\b", r"\bflexible\b", r"\horario\s+flexible\b"
    ]
    
    # Remote patterns
    REMOTE_PATTERNS = [
        r"\bremote\b", r"\bwork\s+from\s+home\b", r"\bwfh\b",
        r"\bteletrabajo\b", r"\bdesde\s+casa\b"
    ]
    
    HYBRID_PATTERNS = [
        r"\bhybrid\b", r"\bhidrido\b", r"\bflexible\s+location\b",
        r"\b2\s*(?:days?|dias?)\s+office\b", r"\b3\s*(?:days?|dias?)\s+office\b"
    ]
    
    ON_SITE_PATTERNS = [
        r"\bon.?site\b", r"\bpresencial\b", r"\bin\s+office\b",
        r"\b5\s*days?.*office\b"
    ]
    
    # Common tech skills
    TECH_SKILLS = {
        "Python", "Java", "JavaScript", "C++", "C#", "PHP", "Ruby", "Go",
        "Rust", "TypeScript", "React", "Vue", "Angular", "Django", "Flask",
        "Node.js", "Express", "SQL", "MongoDB", "PostgreSQL", "MySQL",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Git", "Linux",
        "HTML", "CSS", "REST", "API", "GraphQL", "ML", "AI", "TensorFlow",
        "Pandas", "NumPy", "Data Science", "Analytics", "DevOps", "CI/CD"
    }
    
    # Proficiency levels
    PROFICIENCY_LEVELS = {
        "fluent", "advanced", "intermediate", "basic", "native",
        "working knowledge", "professional", "conversational"
    }
    
    def __init__(self, location: str = "Spain", city: str = "Unknown"):
        self.location = location
        self.city = city
    
    def parse_job(self, job_data: Dict[str, Any]) -> JobRequirements:
        """Parse a job posting and extract requirements"""
        
        text = self._combine_text(job_data)
        text_lower = text.lower()
        
        # Extract languages
        languages, proficiency = self._extract_languages(text_lower)
        
        # Extract hours
        hours = self._extract_hours(text_lower)
        hours_type = self._determine_hours_type(text_lower, hours)
        
        # Extract remote type
        remote_type = self._extract_remote_type(text_lower)
        
        # Extract location info
        location = job_data.get("location", self.location)
        country = job_data.get("country", "Spain")
        city_parsed = job_data.get("location", self.city).split(",")[0].strip()
        
        # Extract skills
        skills_required, skills_nice = self._extract_skills(text_lower)
        
        # Extract experience level
        experience_level = self._extract_experience_level(text_lower)
        
        # Determine if paid
        is_paid = self._is_paid_internship(text_lower)
        
        # Extract duration
        duration = self._extract_duration(text_lower)
        
        # Employment type
        employment_type = "Internship" if "internship" in text_lower or "stage" in text_lower else "Job"
        
        return JobRequirements(
            languages=languages,
            language_proficiency=proficiency,
            location=location,
            country=country,
            city=city_parsed,
            hours_per_week=hours,
            hours_type=hours_type,
            employment_type=employment_type,
            remote_type=remote_type,
            skills_required=skills_required,
            skills_nice_to_have=skills_nice,
            experience_level=experience_level,
            salary=job_data.get("salary"),
            duration_months=duration,
            is_paid=is_paid
        )
    
    def _combine_text(self, job_data: Dict[str, Any]) -> str:
        """Combine all text fields for analysis"""
        parts = [
            job_data.get("position", ""),
            job_data.get("company", ""),
            job_data.get("description", ""),
        ]
        return " ".join(str(p) for p in parts if p)
    
    def _extract_languages(self, text: str) -> tuple[Set[str], Dict[str, str]]:
        """Extract language requirements with proficiency levels"""
        languages = set()
        proficiency = {}
        
        # Check for English
        for pattern in self.ENGLISH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                languages.add("English")
                prof = self._extract_proficiency_level(text, "english")
                proficiency["English"] = prof
                break
        
        # Check for Spanish
        for pattern in self.SPANISH_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                languages.add("Spanish")
                prof = self._extract_proficiency_level(text, "spanish")
                proficiency["Spanish"] = prof
                break
        
        # Check for other common languages
        other_langs = {
            "French": [r"\bfrench\b", r"\bfrançais\b"],
            "German": [r"\bgerman\b", r"\bdeutsch\b"],
            "Italian": [r"\bitalian\b", r"\bitaliano\b"],
            "Portuguese": [r"\bportuguese\b", r"\bportuguês\b"],
        }
        
        for lang, patterns in other_langs.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    languages.add(lang)
                    prof = self._extract_proficiency_level(text, lang.lower())
                    proficiency[lang] = prof
                    break
        
        # Default to English if no language specified but job is in English
        if not languages and len(text) > 50:
            # Simple heuristic: if most text is English words
            english_words = len(re.findall(r"\b(the|and|to|of|in|for|is|be)\b", text, re.IGNORECASE))
            if english_words > len(text.split()) * 0.1:
                languages.add("English")
                proficiency["English"] = "unknown"
        
        return languages, proficiency
    
    def _extract_proficiency_level(self, text: str, language: str) -> str:
        """Extract proficiency level for a language"""
        # Look for proficiency keywords near the language
        window = 50
        lang_pos = text.find(language.lower())
        
        if lang_pos == -1:
            return "unknown"
        
        context = text[max(0, lang_pos - window):min(len(text), lang_pos + window)]
        
        for level in self.PROFICIENCY_LEVELS:
            if level in context:
                return level
        
        return "unknown"
    
    def _extract_hours(self, text: str) -> Optional[int]:
        """Extract hours per week requirement"""
        for pattern, _ in self.HOURS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    hours = int(match.group(1))
                    if 0 < hours <= 168:  # Valid hours range
                        return hours
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _determine_hours_type(self, text: str, hours: Optional[int]) -> str:
        """Determine if full-time, part-time, or flexible"""
        for pattern in self.FULL_TIME_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "full-time"
        
        for pattern in self.PART_TIME_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "part-time"
        
        for pattern in self.FLEXIBLE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "flexible"
        
        # Heuristic based on hours
        if hours:
            if hours >= 35:
                return "full-time"
            elif hours >= 20:
                return "part-time"
            else:
                return "flexible"
        
        return "unknown"
    
    def _extract_remote_type(self, text: str) -> str:
        """Determine if remote, hybrid, or on-site"""
        for pattern in self.REMOTE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "remote"
        
        for pattern in self.HYBRID_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "hybrid"
        
        for pattern in self.ON_SITE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return "on-site"
        
        return "unknown"
    
    def _extract_skills(self, text: str) -> tuple[Set[str], Set[str]]:
        """Extract required and nice-to-have skills"""
        required = set()
        nice_to_have = set()
        
        # Look for "required" or "must have" section
        required_match = re.search(
            r"(?:required|must have|essential|must-have)[\s:]*(.{0,300}?)(?:nice|optional|preferred|good|knowledge)",
            text, re.IGNORECASE | re.DOTALL
        )
        
        nice_match = re.search(
            r"(?:nice|optional|preferred|good to have|plus|advantage)[\s:]*(.{0,200}?)(?:\.|$)",
            text, re.IGNORECASE | re.DOTALL
        )
        
        # Extract skills from both sections
        if required_match:
            required = self._find_skills_in_text(required_match.group(1))
        else:
            # If no section found, look for skills in full text
            required = self._find_skills_in_text(text)
        
        if nice_match:
            nice_to_have = self._find_skills_in_text(nice_match.group(1))
        
        # Remove duplicates
        nice_to_have = nice_to_have - required
        
        return required, nice_to_have
    
    def _find_skills_in_text(self, text: str) -> Set[str]:
        """Find all recognized skills in text"""
        found_skills = set()
        
        for skill in self.TECH_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE):
                found_skills.add(skill)
        
        return found_skills
    
    def _extract_experience_level(self, text: str) -> str:
        """Determine experience level required"""
        if any(re.search(pat, text, re.IGNORECASE) for pat in [
            r"\bentry.?level\b", r"\bentrada\b", r"\bprimer\s+empleo\b",
            r"\brecién\s+graduado\b", r"\bfresh\b", r"\nintern"
        ]):
            return "entry-level"
        
        if any(re.search(pat, text, re.IGNORECASE) for pat in [
            r"\bmid.?level\b", r"\b\d+\s*years?\s*experience\b", r"\bintermedio\b"
        ]):
            return "mid-level"
        
        if any(re.search(pat, text, re.IGNORECASE) for pat in [
            r"\bsenior\b", r"\b5\+\s*years?\b", r"\blead\b"
        ]):
            return "senior"
        
        return "unknown"
    
    def _is_paid_internship(self, text: str) -> bool:
        """Determine if internship is paid"""
        paid_indicators = [
            r"\bpaid\s+internship\b", r"\bcompensation\b", r"\bsalary\b",
            r"\b€\b", r"\b\$\b", r"\bmonthly\s+allowance\b",
            r"\bstipend\b", r"\bremuneración\b"
        ]
        
        unpaid_indicators = [
            r"\bunpaid\b", r"\bno.*compensation\b", r"\bvoluntary\b",
            r"\bgratuito\b", r"\bsin\s+remuneración\b"
        ]
        
        # If paid indicators found, likely paid
        for pattern in paid_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # If unpaid indicators found, likely unpaid
        for pattern in unpaid_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return False
        
        # Default: assume unpaid for internships
        return False
    
    def _extract_duration(self, text: str) -> Optional[int]:
        """Extract internship duration in months"""
        patterns = [
            (r"(\d+)\s*(?:months?|meses?)", 1),
            (r"(\d+)\s*(?:weeks?|semanas?)", 1/4),
        ]
        
        for pattern, multiplier in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    return int(value * multiplier)
                except (ValueError, IndexError):
                    continue
        
        return None


if __name__ == "__main__":
    # Test the parser
    test_job = {
        "position": "Python Developer Internship",
        "company": "TechCorp",
        "description": """
        We are looking for a Python developer intern! 
        Requirements:
        - Fluent English (or advanced working knowledge)
        - Spanish nice to have
        - Python and Django required
        - HTML/CSS nice to have
        - 20-30 hours per week, flexible schedule
        - Hybrid (2 days office, 3 days remote)
        - Paid internship (€400/month)
        - 3-6 months duration
        - Entry-level candidates welcome
        Location: Madrid, Spain
        """,
        "location": "Madrid, Spain",
        "country": "Spain"
    }
    
    parser = JobRequirementsParser()
    requirements = parser.parse_job(test_job)
    
    print("📋 Extracted Job Requirements:")
    print(f"  Languages: {requirements.languages}")
    print(f"  Language Proficiency: {requirements.language_proficiency}")
    print(f"  Hours/Week: {requirements.hours_per_week} ({requirements.hours_type})")
    print(f"  Remote Type: {requirements.remote_type}")
    print(f"  Required Skills: {requirements.skills_required}")
    print(f"  Nice Skills: {requirements.skills_nice_to_have}")
    print(f"  Experience Level: {requirements.experience_level}")
    print(f"  Paid: {requirements.is_paid}")
    print(f"  Duration: {requirements.duration_months} months")
