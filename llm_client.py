"""
llm_client.py
-------------
This module provides the interface for sending screenshots and context to the OpenRouter LLM API.
It handles image encoding, prompt construction, schema definition, and robust error handling for network and parsing issues.
"""
import os
import base64
import json
import requests
import time
import logging
from requests.exceptions import ConnectionError, ChunkedEncodingError
import urllib3
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_screenshot_to_llm(image_paths, state=None, analysis=None, plan=None, screen_resolution=None, history=None, memory=None, pinned_screenshot=None, latest_journal=None) -> dict:
    """Send multiple screenshots and context to OpenRouter LLM and return the response as a dict."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY environment variable not set.")
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set.")

    # Accept image_paths as a list
    if isinstance(image_paths, str):
        image_paths = [image_paths]
    # Always include pinned screenshot if not already in the list
    if pinned_screenshot and pinned_screenshot not in image_paths:
        image_paths = [pinned_screenshot] + image_paths
    # Only keep the last 3 (plus pinned)
    image_paths = image_paths[-3:] if len(image_paths) > 3 else image_paths

    # Prepare image data
    images_content = []
    for path in image_paths:
        try:
            with open(path, "rb") as img_file:
                img_bytes = img_file.read()
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                img_data_url = f"data:image/png;base64,{img_b64}"
                images_content.append({"type": "image_url", "image_url": {"url": img_data_url}})
        except Exception as e:
            logger.warning(f"Failed to process screenshot {path}: {e}")

    # Auto-detect screen resolution from the most recent screenshot if not provided
    if screen_resolution is None and image_paths:
        try:
            with Image.open(image_paths[-1]) as img:
                screen_resolution = {'width': img.width, 'height': img.height}
        except Exception as e:
            logger.warning(f"Failed to determine screen resolution: {e}")
            screen_resolution = {'width': 0, 'height': 0}

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Generic, tool-agnostic context for the LLM
    context = """
You are an automation agent operating in a perception-action loop. Your job is to observe the environment, analyze the situation, plan, and act. You receive screenshots and context, and you must:
- Provide a brief narrative of your intent and reasoning.
- Propose a concise, step-by-step plan.
- Output a list of timed actions to execute within the next 2 seconds (2000ms). Each action should specify type, parameters, and a start time offset in milliseconds.
- Analyze the outcome after acting and describe the new state.

You have access to a 'remember' tool. Use it to record important facts, discoveries, or strategies that should be retained for future context. When you want to remember something, add an entry to the journal with the key 'remember' and a short description of the fact or insight. These will be included in your system prompt as memory notes.

Always use your journal to record relevant information, especially when you learn something new, encounter a novel situation, or need to track long-term goals or facts.

You are provided with up to 5 prior screenshots (plus a pinned screenshot if present), recent plans, analyses, and memory notes from your journal.

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
    # Updated schema without planning_paths
    schema = {
        "type": "object",
        "properties": {
            "narrative": {"type": "string", "description": "Narrative plan for this loop."},
            "plan": {"type": "string", "description": "Step-by-step plan for this loop."},
            "actions": {
                "type": "array",
                "description": "Timed actions to execute within 2000ms.",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["key_press", "key_release", "mouse_move", "mouse_press", "mouse_release", "mouse_drag"],
                            "description": "The type of input action."
                        },
                        "key": {"type": "string", "description": "Key identifier (e.g., 'w', 'a', 'enter', 'shift'). Required for key actions."},
                        "x": {"type": "integer", "description": "X coordinate. Required for mouse actions."},
                        "y": {"type": "integer", "description": "Y coordinate. Required for mouse actions."},
                        "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button. Required for mouse press/release/drag."},
                        "time_offset_ms": {
                            "type": "integer",
                            "description": "Start time in milliseconds relative to the beginning of the action sequence (0-2000)."
                        },
                        "duration_ms": {
                            "type": "integer",
                            "description": "Duration for holding a key or mouse button (used with key_press or mouse_press if release is not separate)."
                        }
                    },
                    "required": ["type", "key", "x", "y", "button", "time_offset_ms", "duration_ms"],
                    "additionalProperties": False
                }
            },
            "analysis": {"type": "string", "description": "Analysis of the outcome and current state."},
            "pinned_screenshot": {"type": ["string", "integer"], "description": "Filename or index of screenshot to pin.", "nullable": True}
        },
        "required": ["narrative", "plan", "actions", "analysis", "pinned_screenshot"],
        "additionalProperties": False
    }
    data = {
        "model": "anthropic/claude-3.7-sonnet",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *images_content
                ]
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "ooda_response_timed",
                "strict": True,
                "schema": schema
            }
        }
    }
    max_retries = 5
    backoff = 1
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            break
        except (ConnectionError, ChunkedEncodingError, urllib3.exceptions.ProtocolError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error: {type(e).__name__}: {e}. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
            else:
                logger.error(f"Max retries reached. Network failure: {type(e).__name__}: {e}")
                raise
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    try:
        ooda_response = json.loads(content)
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw response content: {content}")
        ooda_response = {"narrative": "", "plan": "", "actions": [], "analysis": "Error parsing LLM response."}

    return ooda_response