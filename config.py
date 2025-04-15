"""
config.py
---------
Central configuration for the automation agent. Stores game title, manual path, and ensures required folders exist for logs and tools.
"""
import os

# Game configuration
GAME_TITLE = "Darkest Dungeon"
LLM_MODEL="openai/gpt-4.1"

# Manual (AI-generated)
MANUALS_DIR = "manuals"
MANUAL_PATH = os.path.join(MANUALS_DIR, f"{GAME_TITLE.replace(' ', '_')}_manual.md")
RUN_SUMMARIES_DIR = os.path.join(MANUALS_DIR, "run_summaries")

# Logs and tools directories
RUN_LOGS_DIR = os.path.join("logs", "runs")
TOOLS_DIR = "tools"

# Ensure required directories exist
for folder in [MANUALS_DIR, RUN_SUMMARIES_DIR, RUN_LOGS_DIR, TOOLS_DIR]:
    os.makedirs(folder, exist_ok=True)
