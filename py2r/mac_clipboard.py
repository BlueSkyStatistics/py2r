import subprocess
from os import environ

from .pylogger import logger


def read_clipboard_text(timeout=30):
    """Read the macOS clipboard as text via pbpaste.

    Mirrors win_clipboard.read_clipboard_text(): Python reads the clipboard and
    hands R a plain string (clipboardText=) instead of R reading the clipboard
    itself. Returns None when the clipboard is empty or cannot be read, so the
    caller can fall back to R's own clipboard handling.

    Line endings are normalised to \\n because Excel for Mac can separate rows
    with a bare \\r, which readr would otherwise treat as part of the data.
    """
    env = dict(environ)
    # The backend is launched with a minimal environment; without a UTF-8
    # locale pbpaste can mangle non-ASCII characters.
    env['LANG'] = 'en_US.UTF-8'
    env['LC_ALL'] = 'en_US.UTF-8'
    env.setdefault('PATH', '/usr/bin:/bin')
    try:
        result = subprocess.run(['/usr/bin/pbpaste', '-Prefer', 'txt'], capture_output=True,
                                env=env, timeout=timeout, check=False)
    except Exception:
        logger.exception("read_clipboard_text: pbpaste failed")
        return None
    if result.returncode != 0:
        logger.warning("read_clipboard_text: pbpaste exited with %s: %s",
                       result.returncode, result.stderr.decode('utf-8', 'replace').strip())
        return None
    text = result.stdout.decode('utf-8', 'replace')
    if not text:
        return None
    return text.replace('\r\n', '\n').replace('\r', '\n')
