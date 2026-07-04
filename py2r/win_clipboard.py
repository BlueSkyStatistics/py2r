import ctypes
from ctypes import wintypes
from time import sleep

from .pylogger import logger

CF_UNICODETEXT = 13

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t


def read_clipboard_text(open_retries=10, open_retry_delay=0.05):
    """Read CF_UNICODETEXT straight off the Win32 clipboard.

    R's readClipboard()/clipr::read_clip() crash when called from an
    embedded/headless R (rpy2) on large selections (tens of thousands of
    rows) copied from Excel, even though the identical call works fine in
    RGui. RGui owns a real window and message loop, so it can service the
    WM_RENDERFORMAT round-trip Excel needs for its delayed-rendered clipboard
    formats; embedded R has neither, and its internal clipboard buffer
    handling isn't built for that. Reading the clipboard here in Python
    instead (the same OpenClipboard/GetClipboardData/GlobalLock path
    Notepad++ uses, including the retry loop below) sidesteps that path
    entirely, and the text is handed to R as an ordinary string.
    """
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None

    opened = False
    for attempt in range(open_retries):
        if user32.OpenClipboard(None):
            opened = True
            break
        sleep(open_retry_delay)
    if not opened:
        logger.warning("read_clipboard_text: OpenClipboard failed after %d retries", open_retries)
        return None

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        locked_ptr = kernel32.GlobalLock(handle)
        if not locked_ptr:
            return None
        try:
            size_bytes = kernel32.GlobalSize(handle)
            text = ctypes.wstring_at(locked_ptr, size_bytes // ctypes.sizeof(ctypes.c_wchar))
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()

    return text.split("\x00", 1)[0]
