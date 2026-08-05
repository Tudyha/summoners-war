"""Visual detectors for the Summonhenge scroll list."""

import cv2
import numpy as np

from ..core.summon_rules import is_light_dark_scroll_icon_component
from .core import capture_frame_image


def find_light_dark_scroll_icon():
    """Return the light-dark scroll icon center without using OCR text."""
    image = capture_frame_image()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    left = int(width * 0.60)
    right = int(width * 0.78)
    top = int(height * 0.15)
    bottom = int(height * 0.85)
    hsv = cv2.cvtColor(image[top:bottom, left:right], cv2.COLOR_BGR2HSV)

    # The light-dark book has one large magenta scroll body. On the live
    # 1080x720 UI it measured 73x81, area 4021.5 and fill ratio 0.68. Other
    # visible books only produced small fragmented magenta components.
    magenta = cv2.inRange(
        hsv,
        np.array([135, 70, 45], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8),
    )
    magenta = cv2.morphologyEx(
        magenta,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
    )

    candidates = []
    for contour in cv2.findContours(
        magenta, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        fill_ratio = area / float(max(1, box_width * box_height))
        if not is_light_dark_scroll_icon_component(
            area,
            box_width,
            box_height,
            fill_ratio,
            scale_x,
            scale_y,
        ):
            continue
        candidates.append((
            int(left + x + box_width / 2),
            int(top + y + box_height / 2),
        ))

    if len(candidates) != 1:
        return None
    return candidates[0]
