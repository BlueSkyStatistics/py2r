"""
Single source of truth for trial-period expiry.

Import `check_trial()` and call it at:
  - process startup (console.py)
  - every command dispatch point (console_shell.py, console_http.py)

so that a trial that expires while the app is left running is enforced
on the very next command, not just at launch.
"""
from time import time

# Thursday, December 31, 2026 at 11:59:59 PM
TRIAL_EXPIRY_TS = 1798761599


class TrialExpiredError(Exception):
    """Raised when the trial period has expired."""
    pass


def check_trial() -> None:
    """Raise TrialExpiredError if the trial period has expired."""
    if time() > TRIAL_EXPIRY_TS:
        raise TrialExpiredError("Trial period expired.")
g