"""
Apply manager — orchestrates the full application workflow
search -> filter -> pick job -> auto-fill -> review -> submit -> track
"""
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.profile.cv_manager import CVProfile, ProfileManager
from src.database.db_manager import ApplicationDatabase
from src.forms.linkedin_apply import LinkedInEasyApply
from src.forms.form_filler import GenericFormFiller
from src.forms.cover_letter import CoverLetterGenerator

logger = logging.getLogger(__name__)


class ApplyManager:
    """
    High-level orchestrator for applying to jobs.

    Usage:
        manager = ApplyManager(db, profile_manager, resume_path=Path("my_cv.pdf"))
        result = manager.apply_to_job(app_id=42, dry_run=True)
        manager.close()
    """

    def __init__(
        self,
        db: ApplicationDatabase,
        profile_manager: ProfileManager,
        resume_path: Optional[Path] = None,
        headless: bool = False,
    ):
        self.db = db
        self.profile_manager = profile_manager
        self.resume_path = resume_path
        self.headless = headless
        self.driver = None
        self._cover_gen = CoverLetterGenerator()

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def _setup_driver(self):
        opts = Options()
        if self.headless:
            opts.add_argument("--headless")
        opts.add_argument("--start-maximized")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(options=opts)
        logger.info("Chrome driver ready for applications")

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def apply_to_job(
        self,
        app_id: int,
        dry_run: bool = True,
        cover_letter: Optional[str] = None,
        cover_letter_tone: str = "professional",
        generate_cover_letter: bool = True,
    ) -> Dict[str, Any]:
        """
        Apply to a specific job by its database ID.

        Args:
            app_id: ID from the applications table
            dry_run: Fill form but don't click Submit (safe default)
            cover_letter: Custom cover letter text (overrides generated one)
            cover_letter_tone: 'professional', 'enthusiastic', or 'concise'
            generate_cover_letter: Auto-generate a cover letter if none provided

        Returns:
            result dict with status, fields_filled, fields_skipped, errors
        """
        result: Dict[str, Any] = {
            "app_id": app_id,
            "status": "not_started",
            "platform": None,
            "job_url": None,
            "fields_filled": [],
            "fields_skipped": [],
            "errors": [],
            "message": "",
        }

        cv = self.profile_manager.load_cv()
        job = self._load_job(app_id)

        if not job:
            result["status"] = "not_found"
            result["errors"].append(f"Application ID {app_id} not found")
            return result

        job_url: str = job.get("job_url", "")
        platform: str = job.get("platform", "").lower()
        result["platform"] = platform
        result["job_url"] = job_url

        if not job_url:
            result["status"] = "no_url"
            result["errors"].append("Job has no URL stored in database")
            return result

        # Generate cover letter if not provided
        if not cover_letter and generate_cover_letter:
            cover_letter = self._cover_gen.generate(cv, job, tone=cover_letter_tone)

        if not self.driver:
            self._setup_driver()

        # Dispatch to the right applier
        if platform == "linkedin":
            applier = LinkedInEasyApply(self.driver)

            # Warn if not logged in
            if not applier.is_logged_in():
                result["status"] = "login_required"
                result["message"] = (
                    "Please log into LinkedIn in the browser window that opens, "
                    "then re-run this command."
                )
                result["errors"].append("Not logged into LinkedIn")
                return result

            apply_result = applier.apply(
                job_url=job_url,
                cv=cv,
                resume_path=self.resume_path,
                cover_letter=cover_letter,
                dry_run=dry_run,
            )
        else:
            # Generic filler for Indeed, Glassdoor, direct applications
            try:
                self.driver.get(job_url)
                time.sleep(3)
                filler = GenericFormFiller(self.driver)
                apply_result = filler.detect_and_fill(
                    cv=cv,
                    resume_path=self.resume_path,
                    cover_letter=cover_letter,
                    dry_run=dry_run,
                )
                apply_result.setdefault("status", "dry_run_complete" if dry_run else "submitted")
                apply_result.setdefault("message", "Generic form filled.")
            except Exception as e:
                result["status"] = "error"
                result["errors"].append(str(e))
                logger.exception("Generic apply failed")
                return result

        result["fields_filled"] = apply_result.get("fields_filled", [])
        result["fields_skipped"] = apply_result.get("fields_skipped", [])
        result["errors"].extend(apply_result.get("errors", []))
        result["status"] = apply_result.get("status", "unknown")
        result["message"] = apply_result.get("message", "")

        # Persist status change
        if not dry_run and result["status"] == "submitted":
            note = f"Auto-applied. Fields filled: {len(result['fields_filled'])}"
            self.db.update_application_status(app_id, "submitted", notes=note)
        elif dry_run and result["status"] == "dry_run_complete":
            # Mark as 'preview' so the user knows it's been reviewed
            self.db.update_application_status(app_id, "preview", notes="Dry-run review completed")

        return result

    def apply_batch(
        self,
        app_ids: List[int],
        dry_run: bool = True,
        delay_seconds: float = 5.0,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Apply to multiple jobs sequentially.

        Args:
            app_ids: List of application IDs
            dry_run: Safe mode — fill but don't submit
            delay_seconds: Pause between applications to avoid rate-limiting
            **kwargs: Passed through to apply_to_job

        Returns:
            List of result dicts
        """
        results = []
        for i, app_id in enumerate(app_ids, 1):
            logger.info(f"[{i}/{len(app_ids)}] Applying to job {app_id}...")
            result = self.apply_to_job(app_id, dry_run=dry_run, **kwargs)
            results.append(result)
            if i < len(app_ids):
                time.sleep(delay_seconds)
        return results

    def preview_cover_letter(
        self,
        app_id: int,
        tone: str = "professional",
    ) -> str:
        """Generate and print a cover letter preview for a job."""
        cv = self.profile_manager.load_cv()
        job = self._load_job(app_id)
        letter = self._cover_gen.generate(cv, job, tone=tone)
        self._cover_gen.preview(cv, job, tone=tone)
        return letter

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _load_job(self, app_id: int) -> Optional[Dict[str, Any]]:
        """Load a job record from the database by ID."""
        # Try pending first (most common case)
        for app in self.db.get_pending_applications(limit=1000):
            if app["id"] == app_id:
                return app

        # Fall back to full search
        for app in self.db.search_applications():
            if app["id"] == app_id:
                return app

        return None
