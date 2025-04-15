"""
action_executor.py
-----------------
Executes a sequence of timed actions with blending and timing logic, using mouse and keyboard controllers.
"""
import time
import random
import logging
from mouse_controller import MouseController
from keyboard_controller import key_down, key_up, key_press
from window_utils import get_window_rect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mouse_controller = MouseController()

COMMON_KEYS = ['up', 'down', 'left', 'right', 'w', 'a', 's', 'd', 'enter', 'space', 'shift', 'ctrl', 'alt']
MOUSE_BUTTONS = ['left', 'middle', 'right']

def reset_all_inputs():
    for key in COMMON_KEYS:
        try:
            key_up(key)
        except Exception as e:
            logger.debug(f"Error releasing key {key}: {e}")
    import pyautogui
    for button in MOUSE_BUTTONS:
        try:
            pyautogui.mouseUp(button=button)
        except Exception as e:
            logger.debug(f"Error releasing mouse button {button}: {e}")
    logger.info("All inputs reset to prevent stuck keys/buttons")

def _execute_single_action(action):
    action_type = action.get('type')
    left, top, _, _ = get_window_rect()
    if action_type == 'key_press':
        key = action.get('key')
        duration = action.get('duration_ms')
        if key:
            key_press(key, duration)
    elif action_type == 'key_down':
        key = action.get('key')
        if key:
            key_down(key)
    elif action_type == 'key_up':
        key = action.get('key')
        if key:
            key_up(key)
    elif action_type == 'mouse_move_direction':
        direction = action.get('direction')
        duration = action.get('duration_ms', 100)
        mouse_controller.move(direction, duration)
    elif action_type == 'mouse_click':
        button = action.get('button', 'left')
        duration = action.get('duration_ms', 100)
        mouse_controller.click(duration, button)
    elif action_type == 'mouse_double_click':
        button = action.get('button', 'left')
        duration = action.get('duration_ms', 100)
        mouse_controller.double_click(duration, button)
    elif action_type == 'mouse_move':
        x, y = action.get('x'), action.get('y')
        if x is not None and y is not None:
            import pyautogui
            pyautogui.moveTo(left + x, top + y)
    elif action_type == 'mouse_press':
        x, y = action.get('x'), action.get('y')
        button = action.get('button', 'left')
        duration = action.get('duration_ms', 100)
        if x is not None and y is not None:
            import pyautogui
            pyautogui.mouseDown(x=left + x, y=top + y, button=button)
            time.sleep(duration / 1000.0)
            pyautogui.mouseUp(x=left + x, y=top + y, button=button)
    # Add more action types as needed

def execute_actions(actions):
    BLEND_DELAY_MS = 150
    BLEND_THRESHOLD_MS = 300
    blended_actions = []
    last_key_action = {}
    for i, action in enumerate(actions):
        action_type = action.get('type')
        key = action.get('key')
        t = action.get('time_offset_ms', 0)
        if action_type in ('key_press', 'key_release', 'key_down', 'key_up') and key:
            last = last_key_action.get(key)
            if last:
                last_time, last_type = last
                if t - last_time < BLEND_THRESHOLD_MS:
                    blended_actions.append({
                        'type': 'sleep',
                        'duration_ms': BLEND_DELAY_MS,
                        'time_offset_ms': t
                    })
                    t += BLEND_DELAY_MS
                    action = dict(action)
                    action['time_offset_ms'] = t
            last_key_action[key] = (t, action_type)
        blended_actions.append(action)
    actions = blended_actions
    start_time = time.monotonic()
    current_offset_ms = 0
    logger.debug(f"Starting timed action sequence ({len(actions)} actions)...")
    try:
        for action in actions:
            target_offset_ms = action.get('time_offset_ms', 0)
            if target_offset_ms > 2000:
                logger.warning(f"Action offset {target_offset_ms}ms exceeds 2000ms limit. Skipping: {action}")
                continue
            delay_ms = target_offset_ms - current_offset_ms
            if delay_ms > 0:
                entropy = random.uniform(-0.03, 0.03)
                delay_ms = int(delay_ms * (1 + entropy))
                time.sleep(delay_ms / 1000.0)
                current_offset_ms = target_offset_ms
            elif delay_ms < 0:
                logger.warning(f"Negative delay calculated ({delay_ms}ms). Executing immediately. Action: {action}")
                current_offset_ms = target_offset_ms
            if action.get('type') == 'sleep':
                duration = action.get('duration_ms', 0)
                if duration > 0:
                    entropy = random.uniform(-0.03, 0.03)
                    duration = int(duration * (1 + entropy))
                    logger.debug(f"Blending delay: sleeping {duration}ms to smooth repeated key actions.")
                    time.sleep(duration / 1000.0)
                    current_offset_ms += duration
                continue
            _execute_single_action(action)
            if ('duration_ms' in action and action['type'] in ['key_press', 'mouse_press']):
                entropy = random.uniform(-0.03, 0.03)
                adj_duration = int(action['duration_ms'] * (1 + entropy))
                current_offset_ms += adj_duration
    finally:
        reset_all_inputs()
    end_time = time.monotonic()
    total_duration = (end_time - start_time) * 1000
    logger.debug(f"Finished action sequence in {total_duration:.2f}ms.")
