"""Visual detectors for blocking overlay controls."""

import cv2
import numpy as np
from .core import capture_frame_image as capture_cv

def find_top_right_close_button():
    """Find a neutral bright X used to close self-drawn promotion overlays.

    Activity artwork and titles change, and the game does not expose these
    controls through accessibility. Restrict the search to the overlay's
    top-right band and verify an actual crossed-stroke shape so resource text
    and the AScript floating button are not returned.
    """
    image = capture_cv()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale = min(width / 1080.0, height / 720.0)
    left = int(width * 0.72)
    right = int(width * 0.98)
    top = int(height * 0.04)
    # Verified promotion close buttons are in the upper band (roughly
    # y=88..151 at 720p). Extending this to 0.34 admitted the home-side
    # activity icon at y=235 as a false crossed-stroke candidate.
    bottom = int(height * 0.27)
    roi = image[top:bottom, left:right]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Some promotion themes tint the close glyph beige instead of pure white.
    # The verified July package X peaks around HSV V=177..180, so the previous
    # V>=185 threshold discarded it entirely. Keep saturation tight and rely
    # on crossed-stroke geometry below rather than requiring near-white pixels.
    bright = cv2.inRange(
        hsv,
        np.array([0, 0, 165], dtype=np.uint8),
        np.array([179, 100, 255], dtype=np.uint8),
    )
    bright = cv2.morphologyEx(
        bright,
        cv2.MORPH_CLOSE,
        np.ones((max(1, int(round(2 * scale))),) * 2, dtype=np.uint8),
    )

    template = np.zeros((25, 25), dtype=np.uint8)
    cv2.line(template, (3, 3), (21, 21), 255, 3)
    cv2.line(template, (21, 3), (3, 21), 255, 3)
    template_pixels = template > 0
    candidates = []
    for contour in cv2.findContours(
        bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            12 * scale <= box_width <= 40 * scale
            and 12 * scale <= box_height <= 40 * scale
            and 0.65 <= box_width / float(box_height) <= 1.45
        ):
            continue

        component = bright[y:y + box_height, x:x + box_width]
        normalized = cv2.resize(component, (25, 25), interpolation=cv2.INTER_AREA)
        normalized_pixels = normalized >= 90
        overlap = float(np.count_nonzero(normalized_pixels & template_pixels))
        template_coverage = overlap / float(np.count_nonzero(template_pixels))
        component_coverage = overlap / float(max(1, np.count_nonzero(normalized_pixels)))
        score = min(template_coverage, component_coverage)
        # A real close glyph may sit inside a larger glow/shadow component, so
        # it need not fill the normalized box. Demand strong coverage of the X
        # template instead. On the verified July package screen the real X is
        # 0.829/0.329, while the nearby artwork false hit is 0.456/0.341.
        if template_coverage < 0.70 or component_coverage < 0.28:
            continue

        center_x = left + x + box_width // 2
        center_y = top + y + box_height // 2
        candidates.append((center_x, score, center_y))

    if not candidates:
        return None
    # Promotion close controls sit at the outer edge of their panel. Ranking
    # by X after shape validation rejects crossed highlights inside artwork.
    candidates.sort(reverse=True)
    return candidates[0][0], candidates[0][2]
