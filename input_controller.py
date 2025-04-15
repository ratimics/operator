"""
input_controller.py
------------------
This module provides functions to execute keyboard and mouse actions on the target window.
It includes input blending, timing, and safety mechanisms to prevent stuck keys or mouse buttons.
All actions are logged, and errors are handled robustly.
"""
import pyautogui
import time
import threading
import platform
import random
import logging

import config  # Importing the config module for game title

WINDOW_TITLE = config.GAME_TITLE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common keys and mouse buttons that might need to be reset
COMMON_KEYS = ['up', 'down', 'left', 'right', 'w', 'a', 's', 'd', 'enter', 'space', 'shift', 'ctrl', 'alt']
MOUSE_BUTTONS = ['left', 'middle', 'right']

def reset_all_inputs():
    """Reset all inputs to ensure no keys or mouse buttons remain pressed."""
    # Release all common keys
    for key in COMMON_KEYS:
        try:
            pyautogui.keyUp(key)
        except Exception as e:
            # Just log but continue with other keys
            logger.debug(f"Error releasing key {key}: {e}")
    
    # Release all mouse buttons
    for button in MOUSE_BUTTONS:
        try:
            pyautogui.mouseUp(button=button)
        except Exception as e:
            logger.debug(f"Error releasing mouse button {button}: {e}")
            
    logger.info("All inputs reset to prevent stuck keys/buttons")

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
                    TITLE_BAR_HEIGHT = 0
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

def _execute_single_action(action):
    """Executes a single action dictionary."""
    action_type = action.get('type')
    try:
        left, top, _, _ = get_window_rect()
        if action_type == 'key_press':
            key = action.get('key')
            if key:
                pyautogui.keyDown(key if key != '\n' else 'enter')
                logger.info(f"KeyDown: {key}")
                # Handle duration directly if specified, otherwise needs separate key_release
                if 'duration_ms' in action:
                    duration_sec = action['duration_ms'] / 1000.0
                    time.sleep(duration_sec)
                    pyautogui.keyUp(key if key != '\n' else 'enter')
                    logger.info(f"KeyUp: {key} (after {duration_sec:.2f}s)")
            else:
                logger.debug(f"Skipping key_press with missing key: {action}")
        elif action_type == 'key_release':
            key = action.get('key')
            if key:
                pyautogui.keyUp(key if key != '\n' else 'enter')
                logger.info(f"KeyUp: {key}")
            else:
                logger.debug(f"Skipping key_release with missing key: {action}")
        elif action_type == 'key_down':
            key = action.get('key')
            if key:
                pyautogui.keyDown(key if key != '\n' else 'enter')
                logger.info(f"KeyDown: {key}")
            else:
                logger.debug(f"Skipping key_down with missing key: {action}")
        elif action_type == 'key_up':
            key = action.get('key')
            if key:
                pyautogui.keyUp(key if key != '\n' else 'enter')
                logger.info(f"KeyUp: {key}")
            else:
                logger.debug(f"Skipping key_up with missing key: {action}")
        elif action_type == 'mouse_move':
            x, y = action.get('x'), action.get('y')
            if x is not None and y is not None:
                pyautogui.moveTo(left + x, top + y)
                logger.info(f"MouseMove: ({x}, {y}) in window")
            else:
                logger.debug(f"Skipping mouse_move with missing coordinates: {action}")
        elif action_type == 'mouse_press':
            x, y = action.get('x'), action.get('y')
            button = action.get('button', 'left')
            if x is not None and y is not None:
                pyautogui.mouseDown(x=left + x, y=top + y, button=button)
                logger.info(f"MouseDown: {button} at ({x}, {y}) in window")
                # Handle duration directly if specified
                if 'duration_ms' in action:
                    duration_sec = action['duration_ms'] / 1000.0
                    time.sleep(duration_sec)
                    pyautogui.mouseUp(button=button)
                    logger.info(f"MouseUp: {button} (after {duration_sec:.2f}s)")
            else:
                logger.debug(f"Skipping mouse_press with missing coordinates: {action}")
        elif action_type == 'mouse_release':
            button = action.get('button', 'left')
            pyautogui.mouseUp(button=button)
            logger.info(f"MouseUp: {button}")
        elif action_type == 'mouse_drag':
            x, y = action.get('x'), action.get('y')
            button = action.get('button', 'left')
            duration_ms = action.get('duration_ms', 500) # Default drag time if not specified
            if x is not None and y is not None:
                pyautogui.dragTo(left + x, top + y, duration=duration_ms / 1000.0, button=button)
                logger.info(f"MouseDrag: to ({x}, {y}) in window over {duration_ms}ms with {button} button")
            else:
                logger.debug(f"Skipping mouse_drag with missing coordinates: {action}")
        elif action_type == 'plan': # Keep plan logging
            content = action.get('content', None)
            if content:
                try:
                    with open('memory.md', 'a') as f:
                        f.write(f"\n{content}\n")
                    logger.info(f"Appended plan/memory: {content}")
                except Exception as e:
                    logger.error(f"Failed to append plan/memory: {e}")
            else:
                logger.debug("Skipping empty plan action.")
        else:
            logger.warning(f"Unknown action type: {action_type}")
    except Exception as e:
        logger.error(f"Failed executing action {action}: {e}")

def execute_actions(actions: list):
    """Execute a list of timed actions within a 2-second window, blending repeated key actions if too close together."""
    if not actions:
        return

    # Sort actions by time offset
    actions.sort(key=lambda a: a.get('time_offset_ms', 0))

    # --- Smooth blending logic ---
    BLEND_DELAY_MS = 150
    BLEND_THRESHOLD_MS = 300
    blended_actions = []
    last_key_action = {}  # key: (last_time, last_type)
    for i, action in enumerate(actions):
        action_type = action.get('type')
        key = action.get('key')
        t = action.get('time_offset_ms', 0)
        # Only blend for key_press/key_release/key_down/key_up
        if action_type in ('key_press', 'key_release', 'key_down', 'key_up') and key:
            last = last_key_action.get(key)
            if last:
                last_time, last_type = last
                # If this is a repeat for the same key within threshold, insert a delay
                if t - last_time < BLEND_THRESHOLD_MS:
                    # Insert a dummy delay action (sleep)
                    blended_actions.append({
                        'type': 'sleep',
                        'duration_ms': BLEND_DELAY_MS,
                        'time_offset_ms': t  # Keep the same offset, will be handled in timing
                    })
                    t += BLEND_DELAY_MS  # Shift this action forward
                    action = dict(action)
                    action['time_offset_ms'] = t
            last_key_action[key] = (t, action_type)
        blended_actions.append(action)
    actions = blended_actions
    # --- End blending logic ---

    start_time = time.monotonic()
    current_offset_ms = 0

    logger.debug(f"Starting timed action sequence ({len(actions)} actions)...")

    try:
        for action in actions:
            target_offset_ms = action.get('time_offset_ms', 0)

            # Ensure offset is within the 2-second window
            if target_offset_ms > 2000:
                logger.warning(f"Action offset {target_offset_ms}ms exceeds 2000ms limit. Skipping: {action}")
                continue

            # Calculate delay needed
            delay_ms = target_offset_ms - current_offset_ms
            if delay_ms > 0:
                # Add entropy to sleep delay
                entropy = random.uniform(-0.03, 0.03)
                delay_ms = int(delay_ms * (1 + entropy))
                time.sleep(delay_ms / 1000.0)
                current_offset_ms = target_offset_ms
            elif delay_ms < 0:
                logger.warning(f"Negative delay calculated ({delay_ms}ms). Executing immediately. Action: {action}")
                current_offset_ms = target_offset_ms

            # Handle sleep action for blending
            if action.get('type') == 'sleep':
                duration = action.get('duration_ms', 0)
                if duration > 0:
                    # Add entropy to blending delay
                    entropy = random.uniform(-0.03, 0.03)
                    duration = int(duration * (1 + entropy))
                    logger.debug(f"Blending delay: sleeping {duration}ms to smooth repeated key actions.")
                    time.sleep(duration / 1000.0)
                    current_offset_ms += duration
                continue

            # Execute the action
            _execute_single_action(action)

            # Update offset if action had duration handled internally
            if ('duration_ms' in action and action['type'] in ['key_press', 'mouse_press']):
                # Add entropy to action duration
                entropy = random.uniform(-0.03, 0.03)
                adj_duration = int(action['duration_ms'] * (1 + entropy))
                current_offset_ms += adj_duration
    finally:
        # Always reset inputs, even if an exception occurs
        reset_all_inputs()

    end_time = time.monotonic()
    total_duration = (end_time - start_time) * 1000
    logger.debug(f"Finished action sequence in {total_duration:.2f}ms.")