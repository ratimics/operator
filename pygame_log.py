"""
pygame_log.py
-------------
This module provides a simple Pygame-based viewer for displaying the latest screenshot in the workspace.
It continuously updates to show the most recent screenshot and logs errors robustly.
"""
import pygame
import sys
import os
from glob import glob
import time
from PIL import Image
import logging

WINDOW_SIZE = (800, 600)
BG_COLOR = (30, 30, 30)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_latest_screenshot():
    screenshots = sorted(glob("screenshot_*.png"))
    if screenshots:
        return screenshots[-1]
    return None

def main():
    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Pygame Screenshot Viewer")
    logger.info("Pygame window launched.")

    running = True
    latest_img_surface = None
    latest_img_path = None

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Always show the latest screenshot
        latest_img_path = get_latest_screenshot()
        if latest_img_path:
            try:
                img = Image.open(latest_img_path)
                img_surface = pygame.image.load(latest_img_path)
                img_surface = pygame.transform.scale(img_surface, WINDOW_SIZE)
                latest_img_surface = img_surface
            except Exception as e:
                logger.error(f"Failed to load screenshot {latest_img_path}: {e}")
                latest_img_surface = None

        screen.fill(BG_COLOR)
        if latest_img_surface:
            screen.blit(latest_img_surface, (0, 0))
        pygame.display.flip()
        time.sleep(0.05)

    pygame.quit()
    logger.info("Pygame window closed.")
    sys.exit()

if __name__ == "__main__":
    main()
