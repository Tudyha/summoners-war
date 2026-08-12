"""Battle targeting and auto-battle visual detectors."""

import cv2
import numpy as np
from ascript.android.screen import FindColors, FindImages
from ascript.android.system import R

from .. import config
from .core import capture_frame_image as capture_cv, display_scales, scale_point

def _battle_arrow_candidates(mask, scale):
    """Return arrow-like color blobs, strongest silhouette match first."""
    contours = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            260.0 * scale * scale <= area <= 1500.0 * scale * scale
            and 24 * scale <= box_width <= 52 * scale
            and 30 * scale <= box_height <= 58 * scale
        ):
            continue

        fill = area / float(box_width * box_height)
        if not 0.40 <= fill <= 0.72:
            continue

        row_counts = [
            int(np.count_nonzero(mask[y + row, x:x + box_width]))
            for row in range(box_height)
        ]
        quarter = max(1, box_height // 4)
        upper = float(np.mean(row_counts[:quarter]))
        middle = float(np.mean(row_counts[quarter:quarter * 2]))
        head = float(np.mean(row_counts[quarter * 2:quarter * 3]))
        lower = float(np.mean(row_counts[quarter * 3:]))
        maximum = float(max(row_counts))
        if not (
            head > 0
            and upper >= box_width * 0.28
            and upper <= head * 0.72
            and middle >= upper
            and head >= box_width * 0.68
            and lower <= head * 0.55
            and maximum >= box_width * 0.85
            and row_counts[-1] <= box_width * 0.25
        ):
            continue

        # Real arrows have a narrow shaft, a wide third-quarter head, and a
        # sharply tapering tip. This score rejects similarly colored wings,
        # HP bars, and skill icons observed in the same battle frames.
        score = (
            fill
            + maximum / float(box_width)
            + head / float(box_width)
            - upper / head
            - lower / head
        )
        if score >= 1.10:
            candidates.append((score, x, y, box_width, box_height))

    candidates.sort(reverse=True)
    return candidates

def find_battle_target():
    """Find an attack target by its green/yellow/red downward arrow.

    Green (elemental advantage) is preferred over yellow (neutral), with red
    (elemental disadvantage) as the final fallback. The game is a self-drawn
    View, so the click point is derived from the arrow silhouette instead of an
    accessibility control.
    """
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale = min(width / 1080.0, height / 720.0)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Restrict recognition to the enemy half of the battle scene. Skill icons
    # and most buff/debuff icons live below this area.
    search_bottom = int(height * 0.50)
    color_ranges = (
        ("green", (((45, 120, 100), (90, 255, 255)),)),
        ("yellow", (((18, 140, 150), (38, 255, 255)),)),
        # Red wraps around the ends of OpenCV's 0..179 hue interval.
        ("red", (
            ((0, 140, 120), (12, 255, 255)),
            ((168, 140, 120), (179, 255, 255)),
        )),
    )
    for color_name, hsv_ranges in color_ranges:
        mask = np.zeros((height, width), dtype=np.uint8)
        for lower, upper in hsv_ranges:
            color_mask = cv2.inRange(
                hsv,
                np.array(lower, dtype=np.uint8),
                np.array(upper, dtype=np.uint8),
            )
            mask = cv2.bitwise_or(mask, color_mask)
        mask[search_bottom:, :] = 0
        candidates = _battle_arrow_candidates(mask, scale)
        if not candidates:
            continue

        _, x, y, box_width, box_height = candidates[0]
        arrow_x = int(x + box_width / 2)
        arrow_y = int(y + box_height / 2)
        target_y = min(
            int(arrow_y + 100 * height / 720.0),
            int(height * 0.68),
        )
        return {
            "point": (arrow_x, target_y),
            "color": color_name,
        }
    return None

def auto_battle_is_off():
    """Detect the lower-left play triangle without matching pause bars."""
    image = capture_cv()
    if image is None:
        return False
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    area_scale = scale_x * scale_y
    x0, y0 = scale_point((175, 644))
    x1, y1 = scale_point((222, 700))
    button = image[y0:y1, x0:x1]
    if button.size == 0:
        return False

    maximum = np.max(button, axis=2)
    minimum = np.min(button, axis=2)
    mask = ((minimum >= 165) & ((maximum - minimum) <= 70)).astype(np.uint8)
    mask *= 255
    contours = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    for contour in contours:
        area = float(cv2.contourArea(contour))
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        if not (189 * area_scale <= area <= 810 * area_scale):
            continue
        if not (
            16.875 * scale_x <= box_width <= 37.125 * scale_x
            and 24 * scale_y <= box_height <= 48 * scale_y
        ):
            continue
        fill = area / float(box_width * box_height)
        if not 0.35 <= fill <= 0.72:
            continue
        center_x = box_x + box_width / 2.0
        center_y = box_y + box_height / 2.0
        if not (
            14.85 * scale_x <= center_x <= 32.4 * scale_x
            and 16 * scale_y <= center_y <= 40 * scale_y
        ):
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.06 * perimeter, True)
        if 3 <= len(polygon) <= 5:
            return True
    return False
