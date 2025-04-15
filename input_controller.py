"""
input_controller.py
------------------
Main interface for executing keyboard and mouse actions on the target window.
Delegates to action_executor, mouse_controller, keyboard_controller, and window_utils modules.
"""
from action_executor import execute_actions, reset_all_inputs
from mouse_controller import MouseController
from keyboard_controller import key_down, key_up, key_press
from window_utils import get_window_rect

# Expose main interface
__all__ = [
    "execute_actions",
    "reset_all_inputs",
    "MouseController",
    "key_down",
    "key_up",
    "key_press",
    "get_window_rect"
]