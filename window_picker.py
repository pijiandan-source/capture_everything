from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass

from ctypes import wintypes


GA_ROOT = 2
VK_LBUTTON = 0x01
_USER32 = None


@dataclass
class PickedWindow:
    hwnd: int = 0
    raw_hwnd: int = 0
    x: int = 0
    y: int = 0
    window_name: str = ""
    class_name: str = ""
    error: str = ""

    @property
    def handle_text(self) -> str:
        return format_hwnd(self.hwnd)


def format_hwnd(hwnd: int) -> str:
    if not hwnd:
        return ""
    return f"0x{int(hwnd):08X}"


def _user32():
    global _USER32
    if os.name != "nt":
        return None
    if _USER32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        user32.GetCursorPos.restype = wintypes.BOOL
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        user32.GetAsyncKeyState.restype = ctypes.c_short
        _USER32 = user32
    return _USER32


def is_left_button_down() -> bool:
    user32 = _user32()
    if not user32:
        return False
    return bool(user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000)


def get_window_under_cursor(use_root_window: bool = True, logger=None) -> PickedWindow:
    result = PickedWindow()
    user32 = _user32()
    if not user32:
        result.error = "Window picker is only available on Windows."
        if logger:
            logger.debug("WindowPicker", result.error)
        return result

    try:
        point = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            err = ctypes.get_last_error()
            result.error = f"GetCursorPos failed: winerror={err}"
            if logger:
                logger.error("WindowPicker", result.error)
            return result

        result.x = int(point.x)
        result.y = int(point.y)
        hwnd = int(user32.WindowFromPoint(point) or 0)
        result.raw_hwnd = hwnd
        if logger:
            logger.debug("WindowPicker", f"cursor=({result.x}, {result.y})")
            logger.debug("WindowPicker", f"use_root_window={use_root_window}")
            logger.debug("WindowPicker", f"hwnd={format_hwnd(hwnd)}")

        if hwnd and use_root_window:
            root_hwnd = int(user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT) or hwnd)
            if logger:
                logger.debug("WindowPicker", f"root_hwnd={format_hwnd(root_hwnd)}")
            hwnd = root_hwnd

        result.hwnd = hwnd
        if not hwnd or not user32.IsWindow(wintypes.HWND(hwnd)):
            result.error = f"Invalid hwnd: {format_hwnd(hwnd)}"
            if logger:
                logger.debug("WindowPicker", result.error)
            return result

        text_length = int(user32.GetWindowTextLengthW(wintypes.HWND(hwnd)))
        text_buffer = ctypes.create_unicode_buffer(max(text_length + 1, 1))
        if text_length > 0:
            copied = int(user32.GetWindowTextW(wintypes.HWND(hwnd), text_buffer, len(text_buffer)))
            if copied == 0:
                err = ctypes.get_last_error()
                if logger:
                    logger.debug("WindowPicker", f"GetWindowTextW returned empty, GetLastError={err}")
        result.window_name = text_buffer.value or ""

        class_buffer = ctypes.create_unicode_buffer(512)
        copied_class = int(user32.GetClassNameW(wintypes.HWND(hwnd), class_buffer, len(class_buffer)))
        if copied_class == 0:
            err = ctypes.get_last_error()
            result.error = f"GetClassNameW failed: winerror={err}"
            if logger:
                logger.error("WindowPicker", result.error)
        result.class_name = class_buffer.value or ""

        if logger:
            logger.debug("WindowPicker", f"final_hwnd={format_hwnd(result.hwnd)}")
            logger.debug("WindowPicker", f"window_name={result.window_name}")
            logger.debug("WindowPicker", f"class_name={result.class_name}")
    except Exception as exc:
        result.error = str(exc)
        if logger:
            logger.exception("WindowPicker", "Read window under cursor failed", exc)
    return result
