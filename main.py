import logging
from screenshot import take_screenshot
from llm_client import send_screenshot_to_llm
from input_controller import execute_actions
import time
import os
import json  # Added for saving planning paths
import io
from PIL import Image
import shutil  # Import for file copying
import datetime
import glob
import config

# ANSI color codes for OODA steps
CYAN = '\033[96m'
YELLOW = '\033[93m'
GREEN = '\033[92m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

WAIT_TIMEOUT_SECONDS = 10  # Increased timeout to allow more time for pygame signal

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log(msg, level="INFO"):
    if level == "ERROR":
        logging.error(msg)
    elif level == "WARNING":
        logging.warning(msg)
    elif level == "DEBUG":
        logging.debug(msg)
    else:
        logging.info(msg)

def normalize_action_type(action_type):
    """Map synonyms and variants to canonical action type names."""
    mapping = {
        'press_key': 'key_press',
        'release_key': 'key_release',
        'keydown': 'key_press',
        'keyup': 'key_release',
        'mouse_down': 'mouse_press',
        'mouse_up': 'mouse_release',
        'drag': 'mouse_drag',
        # Add more synonyms if needed
    }
    if not action_type:
        return None
    action_type = action_type.lower()
    return mapping.get(action_type, action_type)

def main():
    state = None  # Holds the last state/analysis
    analysis = None
    plan = None
    loop_count = 0
    history = []  # Rolling history of last 5 states
    screenshot_history = []  # Rolling list of last 5 screenshot paths
    pinned_screenshot = None

    JOURNAL_DIR = "journals"
    if not os.path.exists(JOURNAL_DIR):
        os.makedirs(JOURNAL_DIR)
        log(f"Created {JOURNAL_DIR} directory for journals", "DEBUG")

    # countdown for 3 seconds before starting
    log(f"[OODA: OBSERVE] Starting in 3 seconds...", "OODA")
    for i in range(3, 0, -1):
        log(f"[OODA: OBSERVE] {i}...", "OODA")
        time.sleep(1)
    log(f"[OODA: OBSERVE] Starting now!", "OODA")

    recent_journals = []
    latest_journal_content = ""

    while True:
        screenshot_path = f"screenshot_{int(time.time())}.png"
        # Retry logic for screenshot validity
        max_retries = 3
        for attempt in range(max_retries):
            try:
                take_screenshot(screenshot_path)
                # Validate PNG
                with open(screenshot_path, "rb") as f:
                    img_bytes = f.read()
                    img = Image.open(io.BytesIO(img_bytes))
                    img.verify()  # Will raise if not a valid PNG
                break  # Valid screenshot, exit retry loop
            except Exception as e:
                log(f"Screenshot validation failed (attempt {attempt+1}/{max_retries}): {e}", "ERROR")
                if attempt == max_retries - 1:
                    log(f"Could not produce a valid screenshot after {max_retries} attempts. Proceeding anyway.", "ERROR")
                else:
                    time.sleep(0.2)  # Small delay before retry
        log(f"Screenshot saved to {screenshot_path}", "OODA")

        # Update screenshot history with the original paths (not the overlay versions)
        screenshot_history.append(screenshot_path)
        if len(screenshot_history) > 5:
            screenshot_history = screenshot_history[-5:]

        # Read memory file if exists
        try:
            with open('memory.md', 'r') as f:
                memory_content = f.read()
        except FileNotFoundError:
            memory_content = ''
        except Exception as e:
            log(f"Failed to read memory.md: {e}", "ERROR")
            memory_content = ''

        # Prepare rolling history (last 5 states)
        history.append({
            "state": state,
            "plan": plan,
            "analysis": analysis
        })
        if len(history) > 5:
            history = history[-5:]

        # Load recent journals for context
        journal_files = sorted(glob.glob(os.path.join(JOURNAL_DIR, "journal_*.md")), reverse=True)
        recent_journals = []
        for jf in journal_files[:3]:
            try:
                with open(jf, 'r') as f:
                    recent_journals.append(f.read())
            except Exception as e:
                log(f"Failed to read journal {jf}: {e}", "ERROR")
        latest_journal_content = recent_journals[0] if recent_journals else ""

        # Send screenshots to LLM using the original screenshot paths
        try:
            response = send_screenshot_to_llm(
                screenshot_history,  # Use original screenshots for LLM
                state=state,
                analysis=analysis,
                plan=plan,
                history=history,
                memory=memory_content,
                pinned_screenshot=pinned_screenshot,
                latest_journal=latest_journal_content
            )
        except Exception as e:
            log(f"Exception during LLM call: {e}", "ERROR")
            response = {"narrative": "", "plan": "", "actions": [], "analysis": f"Exception during LLM call: {e}"}
        # Expecting response to have: 'narrative', 'plan', 'actions', 'analysis', (optional) 'pinned_screenshot'
        narrative = response.get("narrative", "")
        plan = response.get("plan", "")
        actions = response.get("actions", [])
        analysis = response.get("analysis", "")
        new_pinned = response.get("pinned_screenshot", None)
        # If LLM returns a new pinned screenshot, update pinned_screenshot
        if new_pinned:
            # If index, resolve to filename
            if isinstance(new_pinned, int) and 0 <= new_pinned < len(screenshot_history):
                pinned_screenshot = screenshot_history[new_pinned]
            elif isinstance(new_pinned, str) and new_pinned in screenshot_history:
                pinned_screenshot = new_pinned
            else:
                # If string but not in list, try to match by basename
                for img in screenshot_history:
                    if os.path.basename(img) == new_pinned:
                        pinned_screenshot = img
                        break

        log(f"Narrative: {narrative}", "OODA-ORIENT")
        log(f"Plan: {plan}", "OODA-ORIENT")
        log(f"Actions: {actions}", "OODA-DECIDE")
        log(f"Analysis: {analysis}", "OODA-ORIENT")

        # Execute actions
        if actions:
            execute_actions(actions)
            log(f"Executed actions: {actions}", "OODA-ACT")

        loop_count += 1

        # Every 10 loops, generate a journal entry
        if loop_count % 10 == 0:
            journal_text = f"# Journal Entry {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            journal_text += f"## Narrative\n{narrative}\n\n"
            journal_text += f"## Plan\n{plan}\n\n"
            journal_text += f"## Analysis\n{analysis}\n\n"
            journal_text += f"## Actions\n{actions}\n\n"
            if journal_text:
                journal_filename = os.path.join(JOURNAL_DIR, f"journal_{int(time.time())}.md")
                try:
                    with open(journal_filename, 'w') as jf:
                        jf.write(journal_text)
                    log(f"Saved new journal entry: {journal_filename}", "JOURNAL")
                except Exception as e:
                    log(f"Failed to save journal entry: {e}", "ERROR")

        # --- Update manual and run log summary at the end of each run ---
        try:
            # Gather insights from the latest journal and plan
            manual_update = f"\n## Run on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            if latest_journal_content:
                manual_update += f"\n### Journal Excerpt\n{latest_journal_content}\n"
            if plan:
                manual_update += f"\n### Plan\n{plan}\n"
            # Append a short run log
            run_log = f"\n---\n**Run Summary ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})**\n- Last plan: {plan}\n- Last analysis: {analysis}\n---\n"
            # Read existing manual (if any)
            try:
                manual_path = config.MANUAL_PATH
                if os.path.exists(manual_path):
                    with open(manual_path, 'r') as mf:
                        manual_content = mf.read()
                else:
                    manual_content = ''
                # Append updates
                manual_content += manual_update
                manual_content += run_log
                with open(manual_path, 'w') as mf:
                    mf.write(manual_content)
                log(f"Manual updated at {manual_path}", "MANUAL")
            except Exception as e:
                log(f"Failed to update manual: {e}", "ERROR")
        except Exception as e:
            log(f"Error in manual/run log update: {e}", "ERROR")

if __name__ == "__main__":
    main()