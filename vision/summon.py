"""Visual detectors for the Summonhenge scroll list."""

import cv2
import numpy as np

from ..core.summon_rules import (
    is_collaboration_scroll_icon_patch,
    is_light_dark_scroll_icon_component,
    is_summon_result_star_component,
)
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


def find_collaboration_scroll_icon():
    """Return the collaboration scroll icon center without relying on OCR."""
    image = capture_frame_image()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    # A freshly opened Summonhenge keeps the event scroll as the first list
    # entry. Restrict recognition to that one complete icon box. Scanning the
    # full column with overlapping windows can combine red from one row with
    # cyan from the next and produce a dangerous coordinate between cards.
    left, right = int(694 * scale_x), int(784 * scale_x)
    top, bottom = int(172 * scale_y), int(258 * scale_y)
    roi = image[top:bottom, left:right]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    cyan = cv2.inRange(
        hsv,
        np.array([75, 55, 55], dtype=np.uint8),
        np.array([110, 255, 255], dtype=np.uint8),
    )
    red_low = cv2.inRange(
        hsv,
        np.array([0, 100, 60], dtype=np.uint8),
        np.array([13, 255, 255], dtype=np.uint8),
    )
    red_high = cv2.inRange(
        hsv,
        np.array([165, 100, 60], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8),
    )
    red = cv2.bitwise_or(red_low, red_high)
    cream = cv2.inRange(
        hsv,
        np.array([5, 20, 130], dtype=np.uint8),
        np.array([45, 190, 255], dtype=np.uint8),
    )

    pixel_count = float(max(1, roi.shape[0] * roi.shape[1]))
    cyan_ratio = np.count_nonzero(cyan) / pixel_count
    red_ratio = np.count_nonzero(red) / pixel_count
    cream_ratio = np.count_nonzero(cream) / pixel_count
    if not is_collaboration_scroll_icon_patch(
        cyan_ratio, red_ratio, cream_ratio
    ):
        return None
    return int((left + right) / 2), int((top + bottom) / 2)


def find_summon_result_star_count():
    """Count the 3-5 gold or awakened-purple result-panel stars.

    OCR commonly omits decorative star glyphs.  Restricting the detector to
    the narrow row below the monster name avoids gold labels and buttons on
    the same panel.  ``None`` means the frame is not safe to classify.
    """
    image = capture_frame_image()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    left, right = int(770 * scale_x), int(970 * scale_x)
    top, bottom = int(207 * scale_y), int(250 * scale_y)
    roi = image[top:bottom, left:right]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gold = cv2.inRange(
        hsv,
        np.array([14, 95, 120], dtype=np.uint8),
        np.array([45, 255, 255], dtype=np.uint8),
    )
    # Android-125's live four-star awakened result measured four separate
    # 23-24px components in this magenta-purple hue range.
    purple = cv2.inRange(
        hsv,
        np.array([140, 70, 80], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8),
    )
    star_mask = cv2.bitwise_or(gold, purple)
    star_mask = cv2.morphologyEx(
        star_mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
    )

    centers = []
    for contour in cv2.findContours(
        star_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        fill_ratio = area / float(max(1, box_width * box_height))
        if not is_summon_result_star_component(
            area,
            box_width,
            box_height,
            fill_ratio,
            scale_x,
            scale_y,
        ):
            continue
        centers.append((x + box_width / 2.0, y + box_height / 2.0))

    centers.sort()
    if len(centers) not in (3, 4, 5):
        return None
    # The stars form one evenly spaced horizontal row. Reject unrelated color
    # components rather than turning an uncertain frame into a data reset.
    normalized_y_spread = (
        max(point[1] for point in centers)
        - min(point[1] for point in centers)
    ) / float(scale_y)
    normalized_gaps = [
        (centers[index + 1][0] - centers[index][0]) / float(scale_x)
        for index in range(len(centers) - 1)
    ]
    if normalized_y_spread > 9:
        return None
    if not all(22 <= gap <= 45 for gap in normalized_gaps):
        return None
    return len(centers)
