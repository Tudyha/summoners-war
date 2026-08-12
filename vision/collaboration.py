"""Visual detectors for the Frieren collaboration activity."""

import cv2
import numpy as np

from ..core.collaboration_rules import (
    is_minigame_entrance_icon,
    is_skill_max_badge,
)
from .core import capture_frame_image


def find_minigame_entrance_icon():
    """Return the center of the dice icon left of the minigame entrance."""
    image = capture_frame_image()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    left, right = int(716 * scale_x), int(816 * scale_x)
    top, bottom = int(506 * scale_y), int(609 * scale_y)
    roi = image[top:bottom, left:right]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    teal = cv2.inRange(
        hsv,
        np.array([70, 45, 35], dtype=np.uint8),
        np.array([110, 255, 230], dtype=np.uint8),
    )
    cream = cv2.inRange(
        hsv,
        np.array([7, 20, 135], dtype=np.uint8),
        np.array([42, 190, 255], dtype=np.uint8),
    )
    dark = cv2.inRange(
        hsv,
        np.array([0, 0, 0], dtype=np.uint8),
        np.array([179, 255, 105], dtype=np.uint8),
    )
    # Pips are small dark islands surrounded by the light dice body.
    pip_count = 0
    # Dice pips are holes/internal islands inside the dark outlined artwork.
    # RETR_EXTERNAL drops them and made the live activity page report zero
    # pips even though both dice were visible; RETR_LIST preserves them.
    for contour in cv2.findContours(
        dark, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )[-2]:
        area = cv2.contourArea(contour) / max(0.01, scale_x * scale_y)
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if 3 <= area <= 90 and box_width <= 14 * scale_x and box_height <= 14 * scale_y:
            cx = min(cream.shape[1] - 1, x + box_width // 2)
            cy = min(cream.shape[0] - 1, y + box_height // 2)
            radius = max(2, int(8 * min(scale_x, scale_y)))
            nearby = cream[
                max(0, cy - radius):min(cream.shape[0], cy + radius + 1),
                max(0, cx - radius):min(cream.shape[1], cx + radius + 1),
            ]
            if nearby.size and np.count_nonzero(nearby) / float(nearby.size) >= 0.08:
                pip_count += 1

    pixel_count = float(roi.shape[0] * roi.shape[1])
    if not is_minigame_entrance_icon(
        np.count_nonzero(teal) / pixel_count,
        np.count_nonzero(cream) / pixel_count,
        pip_count,
    ):
        return None
    return int(766 * scale_x), int(558 * scale_y)


def selected_skill_is_maxed(skill_point):
    """Detect the yellow max-level badge on the selected skill icon."""
    image = capture_frame_image()
    if image is None:
        return False
    height, width = image.shape[:2]
    center_x = skill_point[0] * width / 1080.0
    center_y = skill_point[1] * height / 720.0
    left, right = int(center_x - 25 * width / 1080.0), int(center_x + 30 * width / 1080.0)
    top, bottom = int(center_y + 8 * height / 720.0), int(center_y + 35 * height / 720.0)
    roi = image[top:bottom, left:right]
    if roi.size == 0:
        return False
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    yellow = cv2.inRange(
        hsv,
        np.array([18, 110, 120], dtype=np.uint8),
        np.array([38, 255, 255], dtype=np.uint8),
    )
    yellow_ratio = np.count_nonzero(yellow) / float(yellow.size)
    return is_skill_max_badge(yellow_ratio)
