"""
Forms automation module
Handles auto-filling and submitting job applications
"""
# Imports are intentionally lazy — selenium is only needed at runtime,
# not at import time (avoids breaking tests that don't use a browser).

__all__ = ["ApplyManager", "GenericFormFiller", "LinkedInEasyApply", "CoverLetterGenerator"]


def __getattr__(name):
    if name == "CoverLetterGenerator":
        from src.forms.cover_letter import CoverLetterGenerator
        return CoverLetterGenerator
    if name == "GenericFormFiller":
        from src.forms.form_filler import GenericFormFiller
        return GenericFormFiller
    if name == "LinkedInEasyApply":
        from src.forms.linkedin_apply import LinkedInEasyApply
        return LinkedInEasyApply
    if name == "ApplyManager":
        from src.forms.apply_manager import ApplyManager
        return ApplyManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
