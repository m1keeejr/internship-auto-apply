"""
LinkedIn Easy Apply automation
Handles LinkedIn's multi-step Easy Apply modal flow
"""
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException
)

from src.profile.cv_manager import CVProfile

logger = logging.getLogger(__name__)


class LinkedInEasyApply:
    """
    Automates LinkedIn Easy Apply modal.

    Requires the browser to already be logged into LinkedIn.
    The driver is shared (created externally or here) so it persists
    across multiple applications in the same session.
    """

    # CSS selectors for the Easy Apply modal
    MODAL_SELECTORS = [
        ".jobs-easy-apply-modal",
        "[aria-label='Easy Apply']",
        ".artdeco-modal",
    ]

    EASY_APPLY_BTN_SELECTORS = [
        "button.jobs-apply-button",
        "button[data-control-name='jobdetails_topcard_inapply']",
        ".jobs-apply-button--top-card",
    ]

    def __init__(self, driver, wait_timeout: int = 15):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def apply(
        self,
        job_url: str,
        cv: CVProfile,
        resume_path: Optional[Path] = None,
        cover_letter: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Navigate to a LinkedIn job and complete the Easy Apply flow.

        Args:
            job_url: Full LinkedIn job URL
            cv: User's CV profile
            resume_path: Optional path to resume PDF
            cover_letter: Optional cover letter text
            dry_run: If True, fill all fields but don't click Submit

        Returns:
            result dict: {status, fields_filled, fields_skipped, errors, message}
        """
        result: Dict[str, Any] = {
            "status": "not_started",
            "job_url": job_url,
            "fields_filled": [],
            "fields_skipped": [],
            "errors": [],
            "message": "",
        }

        try:
            self.driver.get(job_url)
            time.sleep(3)

            btn = self._find_easy_apply_button()
            if not btn:
                result["status"] = "no_easy_apply"
                result["message"] = "No Easy Apply button found — this job may require an external application."
                return result

            btn.click()
            time.sleep(2)

            filled, skipped, errors = self._handle_modal(cv, resume_path, cover_letter, dry_run)
            result["fields_filled"] = filled
            result["fields_skipped"] = skipped
            result["errors"].extend(errors)

            if dry_run:
                result["status"] = "dry_run_complete"
                result["message"] = (
                    f"Reviewed {len(filled)} fields. Re-run with --submit to actually apply."
                )
            else:
                result["status"] = "submitted"
                result["message"] = "Application submitted via LinkedIn Easy Apply."

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            logger.exception("Easy Apply failed")

        return result

    def is_logged_in(self) -> bool:
        """Check if the browser is logged into LinkedIn."""
        try:
            self.driver.get("https://www.linkedin.com/feed/")
            time.sleep(2)
            return "feed" in self.driver.current_url
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Navigation helpers
    # ------------------------------------------------------------------ #

    def _find_easy_apply_button(self):
        """Find and return the Easy Apply button, or None if not present."""
        for selector in self.EASY_APPLY_BTN_SELECTORS:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                if btn.is_displayed():
                    return btn
            except NoSuchElementException:
                pass

        # Text-based fallback
        for btn in self.driver.find_elements(By.TAG_NAME, "button"):
            try:
                if "easy apply" in btn.text.lower() and btn.is_displayed():
                    return btn
            except StaleElementReferenceException:
                pass

        return None

    def _get_modal(self):
        """Return the Easy Apply modal element, or None."""
        for selector in self.MODAL_SELECTORS:
            try:
                modal = self.driver.find_element(By.CSS_SELECTOR, selector)
                if modal.is_displayed():
                    return modal
            except NoSuchElementException:
                pass
        return None

    def _is_modal_open(self) -> bool:
        return self._get_modal() is not None

    def _has_button_with_text(self, *texts: str) -> bool:
        modal = self._get_modal()
        container = modal if modal else self.driver
        for btn in container.find_elements(By.TAG_NAME, "button"):
            try:
                if btn.text.strip().lower() in [t.lower() for t in texts] and btn.is_displayed():
                    return True
            except StaleElementReferenceException:
                pass
        return False

    def _click_button_with_text(self, *texts: str) -> bool:
        """Click the first visible button whose text matches one of `texts`."""
        modal = self._get_modal()
        container = modal if modal else self.driver

        # Try aria-label selectors first (more stable)
        for label in ("Continue to next step", "Submit application", "Review your application"):
            try:
                btn = container.find_element(
                    By.CSS_SELECTOR, f"button[aria-label='{label}']"
                )
                if btn.is_displayed():
                    btn.click()
                    return True
            except NoSuchElementException:
                pass

        # Fall back to text matching
        for btn in container.find_elements(By.TAG_NAME, "button"):
            try:
                if btn.text.strip().lower() in [t.lower() for t in texts] and btn.is_displayed():
                    btn.click()
                    return True
            except StaleElementReferenceException:
                pass
        return False

    # ------------------------------------------------------------------ #
    #  Modal handling
    # ------------------------------------------------------------------ #

    def _handle_modal(
        self,
        cv: CVProfile,
        resume_path: Optional[Path],
        cover_letter: Optional[str],
        dry_run: bool,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Walk through all Easy Apply steps and fill each one."""
        filled: List[str] = []
        skipped: List[str] = []
        errors: List[str] = []

        for _step in range(12):  # safety cap
            if not self._is_modal_open():
                break

            time.sleep(1.5)

            sf, ss, se = self._fill_step(cv, resume_path, cover_letter)
            filled.extend(sf)
            skipped.extend(ss)
            errors.extend(se)

            submit_visible = self._has_button_with_text("submit application", "submit", "enviar")
            next_visible = self._has_button_with_text("next", "continue", "siguiente", "review")

            if submit_visible:
                if not dry_run:
                    self._click_button_with_text("submit application", "submit", "enviar")
                break
            elif next_visible:
                self._click_button_with_text("next", "continue", "siguiente", "review")
            else:
                break

        return filled, skipped, errors

    def _fill_step(
        self,
        cv: CVProfile,
        resume_path: Optional[Path],
        cover_letter: Optional[str],
    ) -> Tuple[List[str], List[str], List[str]]:
        """Fill all visible fields in the current modal step."""
        filled, skipped, errors = [], [], []
        modal = self._get_modal()
        container = modal if modal else self.driver

        # --- Text inputs ---
        for inp in container.find_elements(
            By.CSS_SELECTOR,
            "input[type='text'], input[type='email'], input[type='tel'], input:not([type])",
        ):
            try:
                if not inp.is_displayed():
                    continue
                label = self._get_label(inp, container)
                key, value = self._map_cv_value(label, inp, cv)
                if value:
                    inp.clear()
                    inp.send_keys(str(value))
                    filled.append(f"{label}: {str(value)[:40]}")
                else:
                    skipped.append(f"{label} (no CV data)")
            except ElementNotInteractableException:
                skipped.append(f"{self._get_label(inp, container)} (not interactable)")
            except Exception as e:
                errors.append(f"input: {e}")

        # --- Resume upload ---
        for fi in container.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            try:
                if resume_path and resume_path.exists():
                    fi.send_keys(str(resume_path.absolute()))
                    filled.append(f"Resume: {resume_path.name}")
                else:
                    skipped.append("Resume upload (no file path set)")
            except Exception as e:
                errors.append(f"resume upload: {e}")

        # --- Textareas (cover letter) ---
        for ta in container.find_elements(By.TAG_NAME, "textarea"):
            try:
                if not ta.is_displayed():
                    continue
                label_lower = self._get_label(ta, container).lower()
                if any(kw in label_lower for kw in ("cover", "letter", "motivation", "additional info")):
                    text = cover_letter or cv.summary
                    if text:
                        ta.clear()
                        ta.send_keys(text)
                        filled.append("Cover letter / additional info")
                    else:
                        skipped.append("Cover letter (no text provided)")
            except Exception as e:
                errors.append(f"textarea: {e}")

        # --- Yes/No radio buttons (work authorization, etc.) ---
        for fieldset in container.find_elements(By.CSS_SELECTOR, "fieldset"):
            try:
                legend_text = ""
                try:
                    legend_text = fieldset.find_element(By.TAG_NAME, "legend").text.lower()
                except NoSuchElementException:
                    pass

                if any(kw in legend_text for kw in ("authorization", "authoris", "legally", "eligible", "right to work")):
                    radios = fieldset.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    for radio in radios:
                        radio_label = self._get_radio_label(radio).lower()
                        if "yes" in radio_label:
                            radio.click()
                            filled.append(f"Work authorization: Yes")
                            break
            except Exception as e:
                errors.append(f"radio: {e}")

        # --- Select dropdowns ---
        for sel_elem in container.find_elements(By.TAG_NAME, "select"):
            try:
                if not sel_elem.is_displayed():
                    continue
                label = self._get_label(sel_elem, container)
                key, value = self._map_cv_value(label, sel_elem, cv)
                if value:
                    opts = [o.text for o in Select(sel_elem).options]
                    exact = next((o for o in opts if o.lower() == value.lower()), None)
                    partial = next((o for o in opts if value.lower() in o.lower()), None)
                    choice = exact or partial
                    if choice:
                        Select(sel_elem).select_by_visible_text(choice)
                        filled.append(f"{label}: {choice}")
                    else:
                        skipped.append(f"{label} select (no matching option for '{value}')")
                else:
                    skipped.append(f"{label} select (no CV mapping)")
            except Exception as e:
                errors.append(f"select: {e}")

        return filled, skipped, errors

    # ------------------------------------------------------------------ #
    #  Label + CV mapping
    # ------------------------------------------------------------------ #

    def _get_label(self, element, container) -> str:
        """Return the best human-readable label for a form element."""
        try:
            elem_id = element.get_attribute("id")
            if elem_id:
                labels = container.find_elements(By.CSS_SELECTOR, f"label[for='{elem_id}']")
                if labels:
                    return labels[0].text.strip()

            aria = element.get_attribute("aria-label")
            if aria:
                return aria.strip()

            ph = element.get_attribute("placeholder")
            if ph:
                return ph.strip()

            name = element.get_attribute("name") or ""
            if name:
                return name.replace("_", " ").replace("-", " ").title()

            parent = element.find_element(By.XPATH, "..")
            if parent.tag_name == "label":
                return parent.text.strip()
        except Exception:
            pass
        return "Unknown"

    def _get_radio_label(self, radio) -> str:
        try:
            radio_id = radio.get_attribute("id")
            if radio_id:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                return label.text.strip()
        except Exception:
            pass
        return ""

    def _map_cv_value(self, label: str, element, cv: CVProfile) -> Tuple[str, Optional[str]]:
        """Map a field label to a CV value."""
        hint = " ".join(
            [
                label.lower(),
                (element.get_attribute("name") or "").lower(),
                (element.get_attribute("id") or "").lower(),
                (element.get_attribute("placeholder") or "").lower(),
            ]
        )

        parts = cv.name.split()
        first = parts[0] if parts else cv.name
        last = parts[-1] if len(parts) > 1 else ""

        if any(k in hint for k in ("first", "given")):
            return "first_name", first
        if any(k in hint for k in ("last", "surname", "family")):
            return "last_name", last
        if "email" in hint:
            return "email", cv.email
        if any(k in hint for k in ("phone", "mobile", "tel")):
            return "phone", cv.phone
        if "linkedin" in hint:
            return "linkedin_url", cv.linkedin_url or ""
        if "github" in hint:
            return "github_url", cv.github_url or ""
        if any(k in hint for k in ("website", "portfolio", "url")) and "linkedin" not in hint:
            return "portfolio_url", cv.portfolio_url or ""
        if any(k in hint for k in ("city", "ciudad")) and "country" not in hint:
            return "city", cv.location
        if any(k in hint for k in ("country", "país")):
            return "country", cv.country
        if any(k in hint for k in ("address", "location")) and "email" not in hint:
            return "location", f"{cv.location}, {cv.country}"
        if "name" in hint and "company" not in hint and "school" not in hint and "university" not in hint:
            return "name", cv.name

        return "unmapped", None
