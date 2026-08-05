"""Visual detectors for chat and friend flows."""

import cv2
import numpy as np
from .core import capture_frame_image as capture_cv

def find_chat_open():
    """Find the movable self-drawn chat bubble with three aligned dark dots."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale = min(width / 1080.0, height / 720.0)
    maximum = np.max(image, axis=2)
    minimum = np.min(image, axis=2)
    bubble_mask = (
        (minimum >= 130)
        & ((maximum - minimum) <= 70)
    ).astype(np.uint8) * 255
    bubble_mask[int(height * 0.25):, :] = 0

    candidates = []
    contours = cv2.findContours(
        bubble_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    for contour in contours:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            350 * scale * scale <= area <= 1500 * scale * scale
            and 28 * scale <= box_width <= 60 * scale
            and 22 * scale <= box_height <= 48 * scale
        ):
            continue
        fill = area / float(box_width * box_height)
        if not 0.45 <= fill <= 0.85:
            continue

        gray = cv2.cvtColor(
            image[y:y + box_height, x:x + box_width],
            cv2.COLOR_BGR2GRAY,
        )
        dark_mask = (gray <= 85).astype(np.uint8) * 255
        dots = []
        for dark_contour in cv2.findContours(
            dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )[-2]:
            dot_area = float(cv2.contourArea(dark_contour))
            dot_x, dot_y, dot_width, dot_height = cv2.boundingRect(dark_contour)
            center_x = dot_x + dot_width / 2.0
            center_y = dot_y + dot_height / 2.0
            if not (
                4 * scale * scale <= dot_area <= 30 * scale * scale
                and 3 * scale <= dot_width <= 8 * scale
                and 3 * scale <= dot_height <= 8 * scale
                and box_width * 0.15 <= center_x <= box_width * 0.85
                and box_height * 0.30 <= center_y <= box_height * 0.70
            ):
                continue
            dots.append((center_x, center_y))

        dots.sort()
        if len(dots) != 3:
            continue
        y_spread = max(dot[1] for dot in dots) - min(dot[1] for dot in dots)
        gaps = [dots[index + 1][0] - dots[index][0] for index in range(2)]
        if (
            y_spread <= 3 * scale
            and all(5 * scale <= gap <= 14 * scale for gap in gaps)
        ):
            candidates.append((area, x, y, box_width, box_height))

    if len(candidates) != 1:
        return None
    _, x, y, box_width, box_height = candidates[0]
    return int(x + box_width / 2), int(y + box_height / 2)
