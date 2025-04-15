"""
mouse_controller.py
------------------
Provides WASD-style mouse movement and click/double-click actions.
"""
import pyautogui
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MouseController:
    def __init__(self, step_size=30):
        self.step_size = step_size  # Pixels per movement step

    def move(self, direction, duration_ms=100):
        x, y = pyautogui.position()
        dx, dy = 0, 0
        if direction in ('w', 'up'):
            dy = -self.step_size
        elif direction in ('s', 'down'):
            dy = self.step_size
        elif direction in ('a', 'left'):
            dx = -self.step_size
        elif direction in ('d', 'right'):
            dx = self.step_size
        else:
            logger.warning(f"Unknown mouse move direction: {direction}")
            return
        steps = max(1, duration_ms // 20)
        for _ in range(steps):
            pyautogui.moveRel(dx / steps, dy / steps, duration=0)
            time.sleep(duration_ms / steps / 1000.0)
        logger.info(f"Mouse moved {direction} for {duration_ms}ms")

    def click(self, duration_ms=100, button='left'):
        x, y = pyautogui.position()
        pyautogui.mouseDown(x=x, y=y, button=button)
        time.sleep(duration_ms / 1000.0)
        pyautogui.mouseUp(x=x, y=y, button=button)
        logger.info(f"Mouse {button}-clicked at ({x},{y}) for {duration_ms}ms")

    def double_click(self, duration_ms=100, button='left'):
        x, y = pyautogui.position()
        for i in range(2):
            pyautogui.mouseDown(x=x, y=y, button=button)
            time.sleep(duration_ms / 1000.0)
            pyautogui.mouseUp(x=x, y=y, button=button)
            if i == 0:
                time.sleep(0.05)  # Short pause between clicks
        logger.info(f"Mouse {button}-double-clicked at ({x},{y}) with {duration_ms}ms per click")
