"""
window_utils.py
--------------
Provides cross-platform window finding and activation utilities.
"""
import platform
import config
import logging

WINDOW_TITLE = config.GAME_TITLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_window_rect(title=WINDOW_TITLE):
    if platform.system() == "Darwin":
        try:
            import Quartz
            import subprocess
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
                    # Activate window using AppleScript
                    app_name = window.get('kCGWindowOwnerName', None)
                    if app_name:
                        subprocess.run([
                            'osascript', '-e', f'tell application "{app_name}" to activate'
                        ], check=False)
                    return left, top, width, height
            raise RuntimeError(f"Window '{title}' not found. Available windows: {[w.get('kCGWindowName', '') for w in windowList]}")
        except ImportError:
            raise RuntimeError("Quartz is required on macOS for window geometry. Install with 'pip install pyobjc-framework-Quartz'.")
    else:
        import pygetwindow as gw
        if not hasattr(gw, 'getWindowsWithTitle'):
            raise RuntimeError("pygetwindow does not support getWindowsWithTitle on this platform or version. Try updating pygetwindow or use another method.")
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            raise RuntimeError(f"Window '{title}' not found. Available windows: {gw.getAllTitles()}")
        win = windows[0]
        win.activate()  # Bring window to front
        return win.left, win.top, win.width, win.height
