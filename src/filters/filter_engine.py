"""
Advanced filter engine for job matching
Scores and filters jobs based on user criteria with semantic understanding
"""
import logging
from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from src.filters.job_parser import JobRequirementsParser, JobRequirements

logger = logging.getLogger(__name__)


class MatchScore(Enum):
    """Job match scoring levels"""
    EXCELLENT = 100  # Perfect match
    VERY_GOOD = 85   # Missing minor criteria
    GOOD = 70        # Missing some criteria but core requirements met
    FAIR = 50        # Meets basic requirements
    POOR = 25        # Marginal match
    NO_MATCH = 0     # Doesn't meet core requirements


@dataclass
class JobMatch:
    """Result of job matching against user filter"""
    job_id: str
    job_title: str
    company: str
    match_score: int
    match_level: str  # 'excellent', 'very_good', 'good', 'fair', 'poor', 'no_match'
    matched_criteria: List[str]
    unmatched_criteria: List[str]
    notes: str
    job_requirements: JobRequirements


@dataclass
class FilterCriteria:
    """User's filter criteria"""
    # Location filtering
    countries: Set[str]  # {Spain, France, etc.}
    cities: Set[str]
    remote_type_preference: Optional[str]  # 'remote', 'hybrid', 'on-site', or None (any)
    
    # Language requirements
    required_languages: Set[str]  # User's required languages
    optional_languages: Set[str]  # Nice to have
    min_language_proficiency: Dict[str, str]  # {English: intermediate}
    
    # Time commitment
    min_hours_per_week: Optional[int]
    max_hours_per_week: Optional[int]
    hours_type_preference: Optional[str]  # 'full-time', 'part-time', 'flexible', None (any)
    
    # Skills
    required_skills: Set[str]
    nice_to_have_skills: Set[str]
    
    # Job specifics
    experience_level: Set[str]  # {entry-level, mid-level, senior}
    paid_only: bool
    duration_months: Optional[int]
    
    # Keywords
    include_keywords: Set[str]  # Must contain
    exclude_keywords: Set[str]  # Must not contain
    
    # Other
    match_threshold: int = 50  # Minimum match score (0-100)


class FilterEngine:
    """Advanced job filtering engine with semantic understanding"""
    
    def __init__(self):
        self.parser = JobRequirementsParser()
    
    def create_filter(
        self,
        countries: Optional[List[str]] = None,
        cities: Optional[List[str]] = None,
        required_languages: Optional[List[str]] = None,
        optional_languages: Optional[List[str]] = None,
        remote_preference: Optional[str] = None,
        min_hours: Optional[int] = None,
        max_hours: Optional[int] = None,
        required_skills: Optional[List[str]] = None,
        nice_skills: Optional[List[str]] = None,
        experience_levels: Optional[List[str]] = None,
        paid_only: bool = False,
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        match_threshold: int = 50
    ) -> FilterCriteria:
        """Create a filter criteria object"""
        
        return FilterCriteria(
            countries=set(countries or ["Spain"]),
            cities=set(cities or []),
            remote_type_preference=remote_preference,
            required_languages=set(required_languages or ["English", "Spanish"]),
            optional_languages=set(optional_languages or []),
            min_language_proficiency={},
            min_hours_per_week=min_hours,
            max_hours_per_week=max_hours,
            hours_type_preference=None,
            required_skills=set(required_skills or []),
            nice_to_have_skills=set(nice_skills or []),
            experience_level=set(experience_levels or ["entry-level"]),
            paid_only=paid_only,
            duration_months=None,
            include_keywords=set(include_keywords or ["internship"]),
            exclude_keywords=set(exclude_keywords or []),
            match_threshold=match_threshold
        )
    
    def filter_jobs(
        self,
        jobs: List[Dict[str, Any]],
        filter_criteria: FilterCriteria
    ) -> List[JobMatch]:
        """
        Filter and score jobs against criteria
        
        Args:
            jobs: List of job dictionaries from scrapers
            filter_criteria: User's filter criteria
        
        Returns:
            Sorted list of JobMatch results (best matches first)
        """
        matches = []
        
        for job in jobs:
            # Parse job to extract requirements
            job_requirements = self.parser.parse_job(job)
            
            # Score the job against criteria
            score, matched, unmatched, notes = self._score_job(
                job,
                job_requirements,
                filter_criteria
            )
            
            # Determine match level
            if score >= 90:
                level = "excellent"
            elif score >= 80:
                level = "very_good"
            elif score >= 70:
                level = "good"
            elif score >= 50:
                level = "fair"
            elif score >= 25:
                level = "poor"
            else:
                level = "no_match"
            
            # Only include if meets minimum threshold
            if score >= filter_criteria.match_threshold:
                match = JobMatch(
                    job_id=job.get("job_id", "unknown"),
                    job_title=job.get("position", "Unknown"),
                    company=job.get("company", "Unknown"),
                    match_score=score,
                    match_level=level,
                    matched_criteria=matched,
                    unmatched_criteria=unmatched,
                    notes=notes,
                    job_requirements=job_requirements
                )
                matches.append(match)
        
        # Sort by score (best first)
        matches.sort(key=lambda x: x.match_score, reverse=True)
        
        logger.info(f"✓ Filtered {len(matches)} jobs from {len(jobs)} total (threshold: {filter_criteria.match_threshold})")
        
        return matches
    
    def _score_job(
        self,
        job: Dict[str, Any],
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, List[str], List[str], str]:
        """
        Score a job against filter criteria
        
        Returns: (score, matched_criteria, unmatched_criteria, notes)
        """
        score = 0
        matched = []
        unmatched = []
        notes = []
        
        # 1. Core requirement: Location match (essential - fallback if missing other data)
        location_score, location_matched = self._score_location(job, requirements, criteria)
        score += location_score * 0.25  # 25% weight
        if location_matched:
            matched.append("Location")
        else:
            unmatched.append("Location")
        
        # 2. Core requirement: Internship keyword
        internship_score, internship_matched = self._score_internship_type(job, requirements, criteria)
        score += internship_score * 0.15  # 15% weight
        if internship_matched:
            matched.append("Internship type")
        else:
            unmatched.append("Not an internship")
        
        # 3. Language matching (critical for user)
        language_score, lang_matched, lang_notes = self._score_languages(requirements, criteria)
        score += language_score * 0.20  # 20% weight
        if lang_matched:
            matched.append(f"Languages: {lang_notes}")
        else:
            notes.append(f"Language: {lang_notes}")
        
        # 4. Hours/Time commitment
        hours_score, hours_matched = self._score_hours(requirements, criteria)
        score += hours_score * 0.15  # 15% weight
        if hours_matched:
            matched.append(f"Hours: {requirements.hours_per_week}h/week")
        else:
            if requirements.hours_per_week:
                notes.append(f"Hours: {requirements.hours_per_week}h/week")
        
        # 5. Skills matching
        skills_score, skills_matched = self._score_skills(requirements, criteria)
        score += skills_score * 0.15  # 15% weight
        if skills_matched:
            matched.append("Required skills")
        
        # 6. Remote type preference
        remote_score, remote_matched = self._score_remote(requirements, criteria)
        score += remote_score * 0.10  # 10% weight
        if remote_matched:
            matched.append(f"Remote: {requirements.remote_type}")
        else:
            if requirements.remote_type != "unknown":
                notes.append(f"Remote: {requirements.remote_type}")
        
        # Bonus scoring for nice-to-have criteria
        bonus = 0
        
        # Paid internship bonus
        if criteria.paid_only and requirements.is_paid:
            bonus += 10
            matched.append("Paid")
        
        # Extra language bonus
        if len(requirements.languages) > len(criteria.required_languages):
            bonus += 5
        
        # Nice skills bonus
        nice_skills_found = len(requirements.skills_nice_to_have & criteria.nice_to_have_skills)
        if nice_skills_found > 0:
            bonus += nice_skills_found * 2
        
        score = min(100, score + bonus)
        
        # Fallback logic: If core requirements met but other data missing, still show job
        if location_matched and internship_matched:
            if score < 50 and len(requirements.languages) == 0:
                # Job has location + internship but no language info, be lenient
                score = max(score, 60)
                notes.append("Language info not specified in listing")
        
        return int(score), matched, unmatched, "; ".join(notes)
    
    def _score_location(
        self,
        job: Dict[str, Any],
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool]:
        """Score location match"""
        job_country = requirements.country.lower()
        job_city = requirements.city.lower()
        
        # Check country match
        criteria_countries = {c.lower() for c in criteria.countries}
        country_match = job_country in criteria_countries
        
        if not country_match:
            return 0, False
        
        # Check city match if specified
        if criteria.cities:
            criteria_cities = {c.lower() for c in criteria.cities}
            city_match = any(
                job_city.startswith(city) or city.startswith(job_city)
                for city in criteria_cities
            )
            return (100 if city_match else 70), country_match
        
        return 80, True
    
    def _score_internship_type(
        self,
        job: Dict[str, Any],
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool]:
        """Score if job is internship"""
        is_internship = "internship" in requirements.employment_type.lower()
        
        # Check for internship in title/description too
        if not is_internship:
            text = (job.get("position", "") + " " + job.get("description", "")).lower()
            is_internship = "internship" in text or "stage" in text or "practicum" in text
        
        return (100 if is_internship else 20), is_internship
    
    def _score_languages(
        self,
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool, str]:
        """Score language match"""
        job_langs = requirements.languages.copy()
        
        if not job_langs:
            # Language not specified - this is OK (fallback)
            return 60, True, "Not specified (likely in English/Spanish)"
        
        # Check if at least one required language is met
        required_found = job_langs & criteria.required_languages
        
        if not required_found:
            # No required language found
            return 20, False, f"Requires {job_langs}, user needs {criteria.required_languages}"
        
        # Score based on match quality
        score = 70  # Base score for having required language
        
        # Bonus if multiple languages match
        bonus = 0
        if len(required_found) > 1:
            bonus = 15
        
        # Check optional languages
        optional_found = job_langs & criteria.optional_languages
        if optional_found:
            bonus += 10
        
        return min(100, score + bonus), True, ", ".join(required_found)
    
    def _score_hours(
        self,
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool]:
        """Score hours/time commitment match"""
        hours = requirements.hours_per_week
        
        if hours is None:
            # Hours not specified - neutral
            return 70, True
        
        # Check against criteria
        min_hours = criteria.min_hours_per_week or 0
        max_hours = criteria.max_hours_per_week or 40
        
        if min_hours <= hours <= max_hours:
            return 100, True
        elif hours < min_hours:
            return max(30, 100 - (min_hours - hours) * 5), False
        else:
            return max(30, 100 - (hours - max_hours) * 5), False
    
    def _score_skills(
        self,
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool]:
        """Score required skills match"""
        if not criteria.required_skills:
            return 80, True
        
        if not requirements.skills_required:
            # Skills not specified
            return 60, True
        
        # Check how many required skills match
        matches = requirements.skills_required & criteria.required_skills
        match_ratio = len(matches) / len(criteria.required_skills)
        
        score = int(match_ratio * 100)
        return score, match_ratio >= 0.7
    
    def _score_remote(
        self,
        requirements: JobRequirements,
        criteria: FilterCriteria
    ) -> tuple[int, bool]:
        """Score remote type preference"""
        if not criteria.remote_type_preference or requirements.remote_type == "unknown":
            return 70, True
        
        if requirements.remote_type == criteria.remote_type_preference:
            return 100, True
        
        # Partial credit for hybrid
        if criteria.remote_type_preference == "remote" and requirements.remote_type == "hybrid":
            return 80, False
        
        return 40, False


def apply_filters(
    jobs: List[Dict[str, Any]],
    countries: Optional[List[str]] = None,
    cities: Optional[List[str]] = None,
    required_languages: Optional[List[str]] = None,
    remote_preference: Optional[str] = None,
    exclude_keywords: Optional[List[str]] = None,
    match_threshold: int = 50
) -> List[JobMatch]:
    """
    Convenience function to filter jobs
    
    Args:
        jobs: List of job dictionaries
        countries: Countries to search in
        cities: Cities to filter by
        required_languages: Required language(s)
        remote_preference: Preferred work location type
        exclude_keywords: Keywords to exclude
        match_threshold: Minimum match score
    
    Returns:
        Filtered and scored jobs
    """
    engine = FilterEngine()
    
    criteria = engine.create_filter(
        countries=countries or ["Spain"],
        cities=cities,
        required_languages=required_languages or ["English", "Spanish"],
        remote_preference=remote_preference,
        exclude_keywords=exclude_keywords or [],
        match_threshold=match_threshold
    )
    
    return engine.filter_jobs(jobs, criteria)


if __name__ == "__main__":
    # Test the filter
    test_jobs = [
        {
            "job_id": "li_001",
            "position": "Python Developer Internship",
            "company": "TechCorp",
            "description": "Fluent English required. Spanish nice. Python + Django. 30h/week hybrid.",
            "location": "Madrid, Spain",
            "country": "Spain"
        },
        {
            "job_id": "li_002",
            "position": "Data Analyst Intern",
            "company": "DataCo",
            "description": "Entry-level position. SQL, Python. Remote. Part-time (20h/week).",
            "location": "Barcelona",
            "country": "Spain"
        },
        {
            "job_id": "ind_001",
            "position": "Marketing Intern",
            "company": "Marketing Plus",
            "description": "No specific tech requirements mentioned.",
            "location": "Madrid",
            "country": "Spain"
        }
    ]
    
    matches = apply_filters(
        test_jobs,
        countries=["Spain"],
        cities=["Madrid", "Barcelona"],
        required_languages=["English"],
        match_threshold=50
    )
    
    print("\n📊 Filter Results:")
    print(f"Found {len(matches)} matching jobs\n")
    
    for match in matches:
        print(f"  [{match.match_score}%] {match.job_title} @ {match.company}")
        print(f"       Match: {', '.join(match.matched_criteria)}")
        if match.unmatched_criteria:
            print(f"       Missing: {', '.join(match.unmatched_criteria)}")
        if match.notes:
            print(f"       Notes: {match.notes}")
        print()
