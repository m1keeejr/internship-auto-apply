"""
Generic form filler for job application pages
Works across different job sites using heuristic field detection
"""
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    ElementNotInteractableException, StaleElementReferenceException
)

from src.profile.cv_manager import CVProfile

logger = logging.getLogger(__name__)


class GenericFormFiller:
    """
    Fills job application forms on arbitrary job sites.
    Uses label text, placeholder, name/id attributes to map fields to CV data.
    """

    def __init__(self, driver):
        self.driver = driver

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def detect_and_fill(
        self,
        cv: CVProfile,
        resume_path: Optional[Path] = None,
        cover_letter: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Detect form fields on the current page and fill them with CV data.

        Args:
            cv: User's CV profile
            resume_path: Path to resume PDF file
            cover_letter: Optional cover letter text
            dry_run: If True, log what would be filled but don't actually type

        Returns:
            {fields_detected, fields_filled, fields_skipped, errors}
        """
        result: Dict[str, Any] = {
            "fields_detected": [],
            "fields_filled": [],
            "fields_skipped": [],
            "errors": [],
        }

        # Collect all containers — prefer explicit <form> tags, fall back to body
        containers = self.driver.find_elements(By.TAG_NAME, "form")
        if not containers:
            containers = [self.driver.find_element(By.TAG_NAME, "body")]

        for container in containers:
            r = self._fill_container(container, cv, resume_path, cover_letter, dry_run)
            for key in ("fields_detected", "fields_filled", "fields_skipped", "errors"):
                result[key].extend(r[key])

        return result

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _fill_container(
        self,
        container,
        cv: CVProfile,
        resume_path: Optional[Path],
        cover_letter: Optional[str],
        dry_run: bool,
    ) -> Dict[str, List]:
        filled, skipped, detected, errors = [], [], [], []

        # --- Text / email / tel inputs ---
        inputs = container.find_elements(
            By.CSS_SELECTOR,
            "input[type='text'], input[type='email'], input[type='tel'], "
            "input[type='number'], input:not([type])",
        )
        for inp in inputs:
            try:
                if not inp.is_displayed():
                    continue
                label = self._get_label(inp)
                mapped_key, value = self._map_to_cv(label, inp, cv)
                detected.append(f"{label} ({mapped_key})")

                if value:
                    if not dry_run:
                        inp.clear()
                        inp.send_keys(str(value))
                    filled.append(f"{'[DRY RUN] ' if dry_run else ''}{label}: {str(value)[:40]}")
                else:
                    skipped.append(f"{label} (no CV mapping)")
            except ElementNotInteractableException:
                skipped.append(f"{self._get_label(inp)} (not interactable)")
            except StaleElementReferenceException:
                pass
            except Exception as e:
                errors.append(f"input error: {e}")

        # --- Textareas (cover letter, summary, etc.) ---
        for ta in container.find_elements(By.TAG_NAME, "textarea"):
            try:
                if not ta.is_displayed():
                    continue
                label_lower = self._get_label(ta).lower()
                if any(kw in label_lower for kw in ("cover", "letter", "motivation", "why", "describe")):
                    text = cover_letter or cv.summary
                    detected.append(f"Textarea: {label_lower[:40]}")
                    if text:
                        if not dry_run:
                            ta.clear()
                            ta.send_keys(text)
                        filled.append(f"{'[DRY RUN] ' if dry_run else ''}Cover letter / motivation")
                    else:
                        skipped.append("Cover letter textarea (no text provided)")
                elif any(kw in label_lower for kw in ("summary", "about", "bio", "profile")):
                    if cv.summary:
                        if not dry_run:
                            ta.clear()
                            ta.send_keys(cv.summary)
                        filled.append(f"{'[DRY RUN] ' if dry_run else ''}Summary/Bio")
            except Exception as e:
                errors.append(f"textarea error: {e}")

        # --- File upload (resume) ---
        for fi in container.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            try:
                detected.append("File upload (resume)")
                if resume_path and resume_path.exists():
                    if not dry_run:
                        fi.send_keys(str(resume_path.absolute()))
                    filled.append(f"{'[DRY RUN] ' if dry_run else ''}Resume: {resume_path.name}")
                else:
                    skipped.append("Resume upload (no file configured)")
            except Exception as e:
                errors.append(f"file upload error: {e}")

        # --- Select / dropdowns ---
        for sel in container.find_elements(By.TAG_NAME, "select"):
            try:
                if not sel.is_displayed():
                    continue
                label = self._get_label(sel)
                mapped_key, value = self._map_to_cv(label, sel, cv)
                detected.append(f"Select: {label} ({mapped_key})")
                if value:
                    try:
                        Select(sel).select_by_visible_text(value)
                        filled.append(f"{'[DRY RUN] ' if dry_run else ''}{label}: {value}")
                    except Exception:
                        # Try partial match
                        opts = [o.text for o in Select(sel).options]
                        match = next((o for o in opts if value.lower() in o.lower()), None)
                        if match and not dry_run:
                            Select(sel).select_by_visible_text(match)
                            filled.append(f"{label}: {match}")
                        else:
                            skipped.append(f"{label} (couldn't match '{value}' in options)")
                else:
                    skipped.append(f"{label} select (no CV mapping)")
            except Exception as e:
                errors.append(f"select error: {e}")

        return {
            "fields_detected": detected,
            "fields_filled": filled,
            "fields_skipped": skipped,
            "errors": errors,
        }

    def _get_label(self, element) -> str:
        """Return the best human-readable label for a form element."""
        try:
            # Explicit <label for="id">
            elem_id = element.get_attribute("id")
            if elem_id:
                labels = self.driver.find_elements(
                    By.CSS_SELECTOR, f"label[for='{elem_id}']"
                )
                if labels:
                    return labels[0].text.strip()

            # aria-label
            aria = element.get_attribute("aria-label")
            if aria:
                return aria.strip()

            # placeholder
            ph = element.get_attribute("placeholder")
            if ph:
                return ph.strip()

            # name attribute (humanised)
            name = element.get_attribute("name") or ""
            if name:
                return name.replace("_", " ").replace("-", " ").title()

            # Wrapping <label>
            parent = element.find_element(By.XPATH, "..")
            if parent.tag_name == "label":
                return parent.text.strip()
        except Exception:
            pass
        return "Unknown"

    def _map_to_cv(
        self, label: str, element, cv: CVProfile
    ) -> Tuple[str, Optional[str]]:
        """Map a field label/hint to a CV value. Returns (key_name, value)."""
        hint = " ".join(
            [
                label.lower(),
                (element.get_attribute("name") or "").lower(),
                (element.get_attribute("id") or "").lower(),
                (element.get_attribute("placeholder") or "").lower(),
            ]
        )

        parts = cv.name.split()
        first_name = parts[0] if parts else cv.name
        last_name = parts[-1] if len(parts) > 1 else ""

        if any(k in hint for k in ("first", "given")):
            return "first_name", first_name
        if any(k in hint for k in ("last", "surname", "family")):
            return "last_name", last_name
        if "email" in hint:
            return "email", cv.email
        if any(k in hint for k in ("phone", "mobile", "tel")):
            return "phone", cv.phone
        if "linkedin" in hint:
            return "linkedin_url", cv.linkedin_url or ""
        if "github" in hint:
            return "github_url", cv.github_url or ""
        if any(k in hint for k in ("website", "portfolio", "url")) and "linkedin" not in hint and "github" not in hint:
            return "portfolio_url", cv.portfolio_url or ""
        if any(k in hint for k in ("city", "ciudad")) and "country" not in hint:
            return "city", cv.location
        if any(k in hint for k in ("country", "país")):
            return "country", cv.country
        if any(k in hint for k in ("address", "location")) and "email" not in hint:
            return "location", f"{cv.location}, {cv.country}"
        # Full name catch-all (must come after specific checks)
        if "name" in hint and "company" not in hint and "school" not in hint and "university" not in hint:
            return "name", cv.name

        return "unmapped", None
