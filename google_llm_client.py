"""
google_llm_client.py
--------------------
This module provides the interface for sending screenshots and context to Google's Gemini LLM API.
It handles image loading, prompt construction, schema definition, and robust error handling for API and parsing issues.
"""
import os
import base64
import json
from PIL import Image
from google import genai
from google.genai import types
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the JSON schema for the expected response
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "narrative": {"type": "string", "description": "A short narrative plan.", "nullable": False},
        "plan": {"type": "string", "description": "A concise step-by-step plan.", "nullable": False},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Type of action (e.g., key_press, mouse_move).",
                        "nullable": False,
                        "enum": ["key_press", "key_release", "mouse_move", "mouse_press", "mouse_release", "mouse_drag", "mouse_move_direction", "mouse_click", "mouse_double_click"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters for the action.",
                        "nullable": False,
                        "properties": {
                            "key": {"type": "string", "description": "Key to press or release."},
                            "x": {"type": "integer", "description": "X coordinate for mouse actions."},
                            "y": {"type": "integer", "description": "Y coordinate for mouse actions."},
                            "button": {"type": "string", "description": "Mouse button (e.g., left, right).", "enum": ["left", "right", "middle"]},
                            "direction": {"type": "string", "description": "Direction for mouse_move_direction (w/a/s/d/up/down/left/right)."},
                            "duration_ms": {"type": "integer", "description": "Duration in milliseconds for the action."}
                        }
                    },
                    "time_offset_ms": {
                        "type": "integer",
                        "description": "Time offset in milliseconds.",
                        "nullable": False
                    }
                },
                "required": ["type", "parameters", "time_offset_ms"]
            },
            "description": "A list of timed actions.",
            "nullable": False
        },
        "analysis": {"type": "string", "description": "Analysis of the result.", "nullable": False},
        "pinned_screenshot": {"type": "string", "description": "Pinned screenshot filename.", "nullable": True}
    },
    "required": ["narrative", "plan", "actions", "analysis"],
    "propertyOrdering": ["narrative", "plan", "actions", "analysis", "pinned_screenshot"]
}

def send_screenshot_to_llm(image_paths, state=None, analysis=None, plan=None, screen_resolution=None, history=None, memory=None, pinned_screenshot=None, latest_journal=None) -> dict:
    """Send multiple screenshots and context to Google's Gemini LLM and return the response as a dict."""
    # Retrieve and validate API key
    api_key = os.getenv("GOOGLE_API_KEY")  # Ensure this matches your environment variable name
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        raise RuntimeError("GOOGLE_API_KEY environment variable not set.")

    # Initialize the Google GenAI client
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-pro-preview-03-25'

    # Accept image_paths as a list
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    # Always include pinned screenshot if not already in the list
    if pinned_screenshot and pinned_screenshot not in image_paths:
        image_paths = [pinned_screenshot] + image_paths
    # Only keep the last 3 (plus pinned)
    image_paths = image_paths[-3:] if len(image_paths) > 3 else image_paths

    # Prepare image data as PIL Image objects for the new SDK
    image_parts = []
    valid_image_paths = []
    for path in image_paths:
        if not os.path.exists(path):
            logger.warning(f"Screenshot not found: {path}")
            continue
        try:
            img = Image.open(path)
            image_parts.append(img)
            valid_image_paths.append(path)
        except Exception as e:
            logger.error(f"Failed to process screenshot {path}: {e}")

    # Auto-detect screen resolution from the most recent valid screenshot if not provided
    if screen_resolution is None and valid_image_paths:
        try:
            with Image.open(valid_image_paths[-1]) as img:
                screen_resolution = {'width': img.width, 'height': img.height}
        except Exception as e:
            logger.warning(f"Failed to determine screen resolution: {e}")

    # Define the context prompt (CoQ controls summary added and refined)
    context = """
You are an automation agent controlling the game \"CoQ\" (Caves of Qud) in an OODA loop (Observe, Orient, Decide, Act).

Most relevant controls:
Movement: Arrow keys/NumPad (↑, ↓, ←, →, NumPad8/2/4/6), diagonals (NumPad7/9/1/3 or Shift+Arrow), Wait (NumPad5), Auto-explore (NumPad0), Walk (W)
Adventure: Use/interact (Space), Get item (G), Open (O), Look (L), Talk (C), Use ability (A)
Combat: Melee (Shift+A), Fire (F), Throw (T), Reload (R), Force attack (\\)
Status: Inventory (I/Tab), Equipment (E), Character (X), Quests (Q)
System: Help (F1 for full controls), Save (F5), Load (F9), Quit (Ctrl+Q), Menu (Esc)

If you need the full list of controls, you can "press F1" to open the in-game help.

You are provided with up to 5 prior screenshots (plus a pinned screenshot if present).
Analyze the screenshots and context, then return a JSON object with these keys:
- narrative: What you intend to do and why (1-2 sentences)
- plan: Concise step-by-step plan
- actions: Array of timed actions to execute within the next 2 seconds (2000ms). Each action has a type, parameters, and a start time offset in milliseconds.
- analysis: After acting, analyze if the intended result was achieved and describe the new state.
- pinned_screenshot: (Optional) Filename or index of a screenshot to pin for future context.

# --- BEGIN: WASD-style mouse control instructions ---
# For mouse actions, use these types:
# - mouse_move_direction: Move the mouse in a direction ('w', 'a', 's', 'd', 'up', 'down', 'left', 'right') for a specified duration (ms). Example:
#   {"type": "mouse_move_direction", "direction": "d", "duration_ms": 200, "time_offset_ms": 0}
# - mouse_click: Click at the current mouse position for a specified duration (ms). Example:
#   {"type": "mouse_click", "button": "left", "duration_ms": 100, "time_offset_ms": 100}
# - mouse_double_click: Double-click at the current mouse position for a specified duration (ms) per click. Example:
#   {"type": "mouse_double_click", "button": "left", "duration_ms": 100, "time_offset_ms": 200}
# Do not use absolute pixel coordinates for mouse actions unless explicitly required for legacy compatibility.
# --- END: WASD-style mouse control instructions ---

Screen resolution: {screen_resolution}
Previous state: {state}
Previous analysis: {analysis}
Previous plan: {plan}
Recent history (last 5): {history}
Memory notes: {memory}
""".format(
        screen_resolution=json.dumps(screen_resolution),
        state=json.dumps(state),
        analysis=json.dumps(analysis),
        plan=json.dumps(plan),
        history=json.dumps(history),
        memory=memory or ""
    )
    if latest_journal:
        context += f"\nLatest journal entry: {latest_journal}\n"
    prompt = context + "\nRespond only with the JSON object as described above."

    # Combine text prompt and images into content for the API
    contents = [prompt] + image_parts

    # Send request to Google's Gemini API using the new SDK
    try:
        # Create config for the API call
        generation_config = {
            'response_schema': RESPONSE_SCHEMA,
            'response_mime_type': "application/json"
        }
        
        # Call generate_content with the client
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=generation_config
        )
        content_text = response.text  # Extract the response text
    except Exception as e:
        logger.error(f"Failed to get response from Gemini API: {e}")
        return {"narrative": "", "plan": "", "actions": [], "analysis": "Error contacting Google API."}

    # Filter and validate actions in the response
    def validate_action(action):
        required_keys = {"type", "parameters", "time_offset_ms"}
        if not isinstance(action, dict):
            return False
        if not required_keys.issubset(action.keys()):
            return False
        if not isinstance(action["parameters"], dict):
            return False
        return True

    # Parse the response into a JSON object
    try:
        # Find the start and end of the JSON object within the response text
        start_index = content_text.find("{")
        end_index = content_text.rfind("}")

        if start_index != -1 and end_index != -1 and end_index > start_index:
            json_string = content_text[start_index : end_index + 1]
            ooda_response = json.loads(json_string)

            # Validate actions if present
            if "actions" in ooda_response and isinstance(ooda_response["actions"], list):
                ooda_response["actions"] = [action for action in ooda_response["actions"] if validate_action(action)]
        else:
            logger.error(f"Could not find JSON object in LLM response.")
            logger.debug(f"Raw response content: {content_text}")
            ooda_response = {"narrative": "", "plan": "", "actions": [], "analysis": "Error parsing LLM response: JSON object not found."}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response (JSONDecodeError): {e}")
        logger.debug(f"Attempted to parse: {json_string if 'json_string' in locals() else 'N/A'}")
        logger.debug(f"Raw response content: {content_text}")
        ooda_response = {"narrative": "", "plan": "", "actions": [], "analysis": "Error parsing LLM response."}
    except Exception as e:
        logger.error(f"An unexpected error occurred during JSON parsing: {e}")
        logger.debug(f"Raw response content: {content_text}")
        ooda_response = {"narrative": "", "plan": "", "actions": [], "analysis": "Error parsing LLM response."}

    return ooda_response
