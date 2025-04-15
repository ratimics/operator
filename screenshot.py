"""
screenshot.py
-------------
This module provides functions to capture screenshots of a specific window using platform-specific APIs.
It includes robust error handling and logs issues for diagnostics.
"""
from PIL import Image
import pyautogui
import sys
import platform
import logging
import config

WINDOW_TITLE = config.GAME_TITLE  # Use the game title from config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_window_rect(title=WINDOW_TITLE):
    if platform.system() == "Darwin":
        try:
            import Quartz
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            windowList = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            for window in windowList:
                if title.lower() in window.get('kCGWindowName', '').lower():
                    bounds = window['kCGWindowBounds']
                    left = int(bounds['X'])
                    top = int(bounds['Y'])
                    width = int(bounds['Width'])
                    height = int(bounds['Height'])
                    # Adjust for macOS title bar (commonly 22px)
                    TITLE_BAR_HEIGHT = 22
                    top += TITLE_BAR_HEIGHT
                    height -= TITLE_BAR_HEIGHT
                    return left, top, width, height
            raise RuntimeError(f"Window '{title}' not found. Available windows: {[w.get('kCGWindowName', '') for w in windowList]}")
        except ImportError:
            logger.error("Quartz is required on macOS for window geometry. Install with 'pip install pyobjc-framework-Quartz'.")
            raise RuntimeError("Quartz is required on macOS for window geometry. Install with 'pip install pyobjc-framework-Quartz'.")
        except Exception as e:
            logger.error(f"Error getting window rect: {e}")
            raise
    else:
        import pygetwindow as gw
        if not hasattr(gw, 'getWindowsWithTitle'):
            logger.error("pygetwindow does not support getWindowsWithTitle on this platform or version. Try updating pygetwindow or use another method.")
            raise RuntimeError("pygetwindow does not support getWindowsWithTitle on this platform or version. Try updating pygetwindow or use another method.")
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            logger.error(f"Window '{title}' not found. Available windows: {gw.getAllTitles()}")
            raise RuntimeError(f"Window '{title}' not found. Available windows: {gw.getAllTitles()}")
        win = windows[0]
        return win.left, win.top, win.width, win.height

def take_screenshot(path: str, quality: int = 70):
    """
    Take a screenshot of the window at full resolution and save as PNG. No scaling or compression is applied.
    """
    try:
        left, top, width, height = get_window_rect()
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screenshot.save(path, 'PNG')
        logger.info(f"Screenshot saved to {path}")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        raise