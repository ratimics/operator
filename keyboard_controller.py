"""
keyboard_controller.py
---------------------
Provides functions for keyboard key press and release actions.
"""
import pyautogui
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def key_down(key):
    try:
        pyautogui.keyDown(key if key != '\n' else 'enter')
        logger.info(f"KeyDown: {key}")
    except Exception as e:
        logger.error(f"Error pressing key {key}: {e}")

def key_up(key):
    try:
        pyautogui.keyUp(key if key != '\n' else 'enter')
        logger.info(f"KeyUp: {key}")
    except Exception as e:
        logger.error(f"Error releasing key {key}: {e}")

def key_press(key, duration_ms=None):
    key_down(key)
    if duration_ms:
        import time
        time.sleep(duration_ms / 1000.0)
        key_up(key)
