"""
Cover letter generator
Creates personalized cover letters from CV data and job info
"""
from typing import Optional, Dict, Any
from src.profile.cv_manager import CVProfile


class CoverLetterGenerator:
    """Generates cover letters based on CV and job data"""

    def generate(
        self,
        cv: CVProfile,
        job: Optional[Dict[str, Any]] = None,
        tone: str = "professional"
    ) -> str:
        """
        Generate a cover letter for a job application.

        Args:
            cv: User's CV profile
            job: Job data dict (company, position, description, etc.)
            tone: 'professional', 'enthusiastic', or 'concise'

        Returns:
            Formatted cover letter string
        """
        company = job.get("company", "your company") if job else "your company"
        position = job.get("position", "the internship position") if job else "the internship position"

        skills_str = ", ".join(cv.skills[:5]) if cv.skills else "technical and analytical skills"

        langs = [f"{lang} ({level})" for lang, level in cv.languages.items()]
        lang_str = " and ".join(langs[:2]) if langs else "English"

        edu = cv.education[0] if cv.education else None
        edu_str = (
            f"pursuing a {edu.degree} in {edu.field} at {edu.university}"
            if edu else "currently enrolled in university"
        )

        exp_str = ""
        if cv.experience:
            exp = cv.experience[0]
            exp_str = (
                f" I previously gained hands-on experience as {exp.position} at {exp.company}, "
                f"where I developed skills in {', '.join(exp.skills[:3])}."
            )

        linkedin_line = ""
        if cv.linkedin_url:
            linkedin_line = f"\nYou can find more about my work at {cv.linkedin_url}."

        if tone == "concise":
            return self._concise_template(cv, company, position, skills_str, edu_str, lang_str, linkedin_line)
        elif tone == "enthusiastic":
            return self._enthusiastic_template(cv, company, position, skills_str, edu_str, lang_str, exp_str, linkedin_line)
        else:
            return self._professional_template(cv, company, position, skills_str, edu_str, lang_str, exp_str, linkedin_line)

    def _professional_template(self, cv, company, position, skills_str, edu_str, lang_str, exp_str, linkedin_line) -> str:
        return f"""Dear Hiring Team at {company},

I am writing to express my interest in the {position} opportunity at {company}. I am {edu_str}, and I am eager to apply my knowledge in a practical, professional environment.

My core technical competencies include {skills_str}. I am proficient in {lang_str}, which allows me to collaborate effectively in international and multicultural teams.{exp_str}

I am particularly drawn to {company} because of its reputation and the opportunity to contribute meaningfully during my internship. I am a fast learner, highly motivated, and committed to delivering quality work.{linkedin_line}

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team.

Best regards,
{cv.name}
{cv.email}
{cv.phone}"""

    def _enthusiastic_template(self, cv, company, position, skills_str, edu_str, lang_str, exp_str, linkedin_line) -> str:
        return f"""Hi {company} Team,

I'm thrilled to apply for the {position} role at {company}! As a student {edu_str}, I've been building a strong foundation in {skills_str} and I'm excited to put those skills to work.

I speak {lang_str}, love tackling challenging problems, and thrive in fast-paced environments.{exp_str} I'm someone who dives deep, asks questions, and always delivers.{linkedin_line}

I'd love the chance to bring my energy and skills to {company}. Let's connect!

Cheers,
{cv.name}
{cv.email} | {cv.phone}"""

    def _concise_template(self, cv, company, position, skills_str, edu_str, lang_str, linkedin_line) -> str:
        return f"""Dear {company} Team,

I'm applying for the {position} position. I am {edu_str} with skills in {skills_str}. I'm proficient in {lang_str}.{linkedin_line}

I'm motivated, quick to learn, and excited to contribute. Please find my CV attached.

Best,
{cv.name} | {cv.email} | {cv.phone}"""

    def preview(self, cv: CVProfile, job: Optional[Dict[str, Any]] = None, tone: str = "professional") -> None:
        """Print a preview of the generated cover letter"""
        letter = self.generate(cv, job, tone)
        print("\n" + "="*60)
        print("COVER LETTER PREVIEW")
        print("="*60)
        print(letter)
        print("="*60 + "\n")
