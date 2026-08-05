"""Support-monster list visual detectors."""

import cv2
import numpy as np

from ..core.support_rules import is_occupied_support_slot
from .core import capture_frame_image as capture_cv


# Only the three fully visible rows are selectable. The fourth row is partly
# covered by the confirm button and must not be used for counting or clicking.
_SUPPORT_COLUMNS = (237, 324, 411, 498, 585, 672, 759, 846)
_SUPPORT_ROWS = (254, 357, 460)


def find_support_monsters(observation):
    """Return fully visible, occupied friend-support slots in display order."""
    if not observation.contains("好友魔灵"):
        return []

    image = capture_cv()
    if image is None:
        return []

    # This popup is a fixed self-drawn grid. Slot occupancy is authoritative:
    # OCR misses portrait-only cards, while free-form frame/star detection can
    # see the empty placeholders and the formation cards behind the popup.
    monsters = _find_support_monsters_by_slot_occupancy(image)
    monsters.sort(key=lambda item: (item["point"][1], item["point"][0]))
    return monsters


def _find_support_monsters_by_slot_occupancy(image):
    """Count real cards by visual detail inside each fully visible grid slot."""
    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    monsters = []

    for ref_y in _SUPPORT_ROWS:
        center_y = int(ref_y * scale_y)
        for ref_x in _SUPPORT_COLUMNS:
            center_x = int(ref_x * scale_x)
            left = max(0, int((ref_x - 35) * scale_x))
            top = max(0, int((ref_y - 42) * scale_y))
            right = min(width, int((ref_x + 35) * scale_x))
            bottom = min(height, int((ref_y + 36) * scale_y))
            card_roi = gray[top:bottom, left:right]
            if card_roi.size == 0:
                continue

            edges = cv2.Canny(card_roi, 60, 140)
            edge_density = float(np.count_nonzero(edges)) / float(edges.size)

            # Empty placeholders are a flat monster silhouette (on the
            # observed 1080x720 screen: std~=8.5 and edge_density=0). Real
            # portraits contain stars, artwork and status icons (std~=32 and
            # edge_density~=0.29), leaving a wide safety margin here.
            if not is_occupied_support_slot(float(card_roi.std()), edge_density):
                continue

            monsters.append(
                {
                    "point": (center_x, center_y),
                    "stars": 0,
                }
            )

    return monsters
