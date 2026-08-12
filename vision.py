"""Small visual-observation layer built from APIs verified through AScript MCP."""

import re
import time

import cv2
import numpy as np

from ascript.android.screen import capture_cv
from ascript.android.screen import FindColors
from ascript.android.screen import Ocr
from ascript.android.system import Device
from ascript.android.screen import FindImages
from ascript.android.system import R

from . import config


def _value(item, name, default=None):
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _center(item):
    x = _value(item, "center_x")
    y = _value(item, "center_y")
    if x is not None and y is not None:
        return int(x), int(y)

    rect = _value(item, "rect")
    if rect is not None and len(rect) == 4:
        return int((rect[0] + rect[2]) / 2), int((rect[1] + rect[3]) / 2)
    return 0, 0


class Observation(object):
    def __init__(self, items):
        self.items = items
        self.rows = []
        for item in items:
            text = str(_value(item, "text", "") or "").strip()
            if not text:
                continue
            x, y = _center(item)
            self.rows.append({"text": text, "x": x, "y": y, "raw": item})
        self.texts = [row["text"] for row in self.rows]

    def contains(self, fragment):
        return any(fragment in text for text in self.texts)

    def contains_all(self, *fragments):
        return all(self.contains(fragment) for fragment in fragments)

    def exact(self, text):
        return [row for row in self.rows if row["text"] == text]

    def matching(self, predicate):
        return [row for row in self.rows if predicate(row)]

    def compact_text(self):
        return " | ".join(text.replace("\n", " / ") for text in self.texts)


def observe():
    # mlkitocr_v2 was verified on the real game UI. The new Ocr.find helpers use
    # a different default engine on this device and missed the guest-login text.
    return Observation(Ocr.mlkitocr_v2() or [])


def display_size():
    display = Device.display()
    return int(display.widthPixels), int(display.heightPixels)


def scale_point(point):
    width, height = display_size()
    return (
        int(point[0] * width / float(config.REFERENCE_WIDTH)),
        int(point[1] * height / float(config.REFERENCE_HEIGHT)),
    )


def display_scales(width=None, height=None):
    """Return independent X/Y scales from the 1600x900 reference frame."""
    if width is None or height is None:
        width, height = display_size()
    return (
        width / float(config.REFERENCE_WIDTH),
        height / float(config.REFERENCE_HEIGHT),
    )


def find_world_map_in_progress_area(observation):
    """Return the visible world-map area with no completed-star marker."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    story_names = (
        "加仑从林",
        "西泽山",
        "拉古恩雪山",
        "卡菲勒遗址",
        "特拉恩丛林",
        "夏依德尼遗址",
        "帕伊摩恩火山",
        "塔摩勒沙漠",
        "海登尼森林",
        "佩伦古城",
        "里纳德山",
        "泽罗卡遗址",
    )
    non_story_names = (
        "竞技场",
        "试炼之塔",
        "卡伊洛斯地下城",
        "异界的缝隙",
        "次元裂缝",
    )
    rows = []
    for row in observation.rows:
        text = row["text"]
        if any(name in text for name in non_story_names):
            continue
        if not any(name in text for name in story_names):
            continue
        if row["x"] < scale_point((180, 0))[0] or row["x"] > scale_point((1450, 0))[0]:
            continue
        if row["y"] < scale_point((0, 80))[1] or row["y"] > scale_point((0, 760))[1]:
            continue
        rows.append(row)

    candidates = []
    for row in rows:
        star_rect = [
            max(0, int(row["x"] - 75 * scale_x)),
            max(0, int(row["y"] + 28 * scale_y)),
            min(width, int(row["x"] + 75 * scale_x)),
            min(height, int(row["y"] + 72 * scale_y)),
        ]
        if star_rect[0] >= star_rect[2] or star_rect[1] >= star_rect[3]:
            continue
        roi = hsv[star_rect[1]:star_rect[3], star_rect[0]:star_rect[2]]
        yellow = cv2.inRange(
            roi,
            np.array([18, 120, 140], dtype=np.uint8),
            np.array([38, 255, 255], dtype=np.uint8),
        )
        contours = cv2.findContours(
            yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )[-2]
        star_blobs = 0
        for contour in contours:
            area = float(cv2.contourArea(contour))
            _, _, box_width, box_height = cv2.boundingRect(contour)
            if (
                40.0 * scale_x * scale_y <= area <= 450.0 * scale_x * scale_y
                and 8 * scale_x <= box_width <= 32 * scale_x
                and 8 * scale_y <= box_height <= 32 * scale_y
            ):
                star_blobs += 1
        if star_blobs == 0:
            candidates.append(row)

    if len(candidates) != 1:
        return None

    row = candidates[0]
    return row["x"], row["y"] + int(45 * scale_y)


def find_world_map_in_progress_area(observation):
    """Return the visible story area whose first star is not bright yellow."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # Calibrated from the live 1080x720 world-map screen. Only story areas are
    # listed; non-story entrances such as Arena, Cairos, ToA, and Rift stay out.
    story_slots = (
        {"click": (326, 392), "first_star": (300, 426)},
        {"click": (530, 290), "first_star": (504, 325)},
        {"click": (803, 118), "first_star": (775, 153)},
        {"click": (747, 337), "first_star": (720, 369)},
    )
    candidates = []
    for slot in story_slots:
        star_x = int(slot["first_star"][0] * scale_x)
        star_y = int(slot["first_star"][1] * scale_y)
        star_rect = [
            max(0, int(star_x - 16 * scale_x)),
            max(0, int(star_y - 16 * scale_y)),
            min(width, int(star_x + 17 * scale_x)),
            min(height, int(star_y + 17 * scale_y)),
        ]
        roi = hsv[star_rect[1]:star_rect[3], star_rect[0]:star_rect[2]]
        yellow = cv2.inRange(
            roi,
            np.array([18, 135, 150], dtype=np.uint8),
            np.array([38, 255, 255], dtype=np.uint8),
        )
        threshold = int(150 * scale_x * scale_y)
        if int(np.count_nonzero(yellow)) < threshold:
            candidates.append(slot)

    if len(candidates) != 1:
        return None

    slot = candidates[0]
    return (
        int(slot["click"][0] * scale_x),
        int(slot["click"][1] * scale_y),
    )


def find_world_map_new_area(observation, map_names):
    """Return the orange `新` glyph that has three story-stage stars below."""
    image = capture_cv()
    if image is None:
        return None

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    area_scale = scale_x * scale_y
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(
        hsv,
        np.array([8, 160, 150], dtype=np.uint8),
        np.array([32, 255, 255], dtype=np.uint8),
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    candidates = []
    count, _, stats, centroids = cv2.connectedComponentsWithStats(orange, 8)
    for index in range(1, count):
        _, _, box_width, box_height, area = [
            int(value) for value in stats[index]
        ]
        normalized_width = box_width / scale_x
        normalized_height = box_height / scale_y
        normalized_area = area / area_scale
        fill_ratio = area / float(max(1, box_width * box_height))
        center_x = float(centroids[index][0])
        center_y = float(centroids[index][1])

        if not (
            12 <= normalized_width <= 32
            and 8 <= normalized_height <= 24
            and 80 <= normalized_area <= 400
            and 1.1 <= normalized_width / normalized_height <= 2.4
            and 0.35 <= fill_ratio <= 0.8
            and 100 * scale_x <= center_x <= 980 * scale_x
            and 45 * scale_y <= center_y <= 630 * scale_y
        ):
            continue

        # Story areas place three 23x23 star badges about 70px below `新`.
        # Event entrances such as Cairos may also show `新`, but have no stars.
        star_checks = []
        for offset_x in (-25, 0, 25):
            star_x = int(center_x + offset_x * scale_x)
            star_y = int(center_y + 70 * scale_y)
            left = max(0, int(star_x - 11 * scale_x))
            top = max(0, int(star_y - 11 * scale_y))
            right = min(width, int(star_x + 12 * scale_x))
            bottom = min(height, int(star_y + 12 * scale_y))
            roi = gray[top:bottom, left:right]
            if roi.size == 0:
                star_checks.append(False)
                continue

            dark_pixels = int(np.count_nonzero(roi < 100))
            edge_pixels = int(np.count_nonzero(cv2.Canny(roi, 30, 90)))
            star_checks.append(
                dark_pixels >= 240 * area_scale
                and edge_pixels >= 90 * (scale_x + scale_y) / 2.0
            )

        if not all(star_checks):
            continue

        nearby_maps = [
            row for row in observation.rows
            if any(name in row["text"] for name in map_names)
            and abs(row["x"] - center_x) <= 100 * scale_x
            and 15 * scale_y <= row["y"] - center_y <= 90 * scale_y
        ]
        nearby_maps.sort(
            key=lambda row: abs(row["x"] - center_x) + abs(row["y"] - center_y)
        )
        candidates.append({
            "point": (
                int(round(center_x)),
                int(round(center_y + 35 * scale_y)),
            ),
            "text": nearby_maps[0]["text"] if nearby_maps else "",
        })

    if len(candidates) != 1:
        return None
    return candidates[0]


def find_home_magic_circle_candidates(excluded_points=None):
    """Return visible blue/purple magic circles that may be the Summonhenge.

    The home island is movable, so this intentionally returns several visual
    candidates. The caller clicks a candidate and verifies the contextual menu
    contains `召唤`/`召喚`, `信息`, and `编辑` before entering it.
    """
    image = capture_cv()
    if image is None:
        return []

    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    area_scale = scale_x * scale_y
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    cyan = cv2.inRange(
        hsv,
        np.array([78, 85, 105], dtype=np.uint8),
        np.array([118, 255, 255], dtype=np.uint8),
    )
    purple = cv2.inRange(
        hsv,
        np.array([119, 55, 75], dtype=np.uint8),
        np.array([172, 255, 255], dtype=np.uint8),
    )
    glow = cv2.bitwise_or(cyan, purple)
    glow = cv2.morphologyEx(
        glow,
        cv2.MORPH_CLOSE,
        np.ones((7, 7), dtype=np.uint8),
    )
    glow = cv2.morphologyEx(
        glow,
        cv2.MORPH_OPEN,
        np.ones((3, 3), dtype=np.uint8),
    )

    contours = cv2.findContours(
        glow,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )[-2]
    excluded_points = excluded_points or []
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        center_x = int(x + box_width / 2)
        center_y = int(y + box_height / 2)
        if not (
            120 * scale_x <= center_x <= 960 * scale_x
            and 90 * scale_y <= center_y <= 590 * scale_y
            and 100 * scale_x <= box_width <= 150 * scale_x
            and 70 * scale_y <= box_height <= 145 * scale_y
            and 4500 * area_scale <= area <= 10000 * area_scale
        ):
            continue

        aspect = box_width / float(max(1, box_height))
        fill_ratio = area / float(max(1, box_width * box_height))
        # Across live 1080x720 views the Summonhenge core measured 129-133px
        # wide, 93-102px high, area 6867-8993, and aspect 1.30-1.43.
        # The dimensional portal is nearly round (aspect 0.95), while castle
        # roof highlights are wider (aspect 1.62) and much smaller. The mana
        # pool false hit is also larger (177x129, area 12388).
        if not 1.15 <= aspect <= 1.5 or not 0.45 <= fill_ratio <= 0.9:
            continue
        if any(
            abs(center_x - point[0]) <= 65 * scale_x
            and abs(center_y - point[1]) <= 65 * scale_y
            for point in excluded_points
        ):
            continue

        candidates.append({
            "point": (center_x, center_y),
            "score": area,
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)
    deduplicated = []
    for candidate in candidates:
        if any(
            abs(candidate["point"][0] - old["point"][0]) <= 55 * scale_x
            and abs(candidate["point"][1] - old["point"][1]) <= 55 * scale_y
            for old in deduplicated
        ):
            continue
        deduplicated.append(candidate)
    return [item["point"] for item in deduplicated]


def find_guest_login(observation):
    """Tolerate the verified ML Kit result `游窖登录`."""
    _, height = display_size()
    return observation.matching(
        lambda row: row["text"].startswith("游")
        and row["text"].endswith("登录")
        and row["y"] > 0.45 * height
    )


def find_yellow_arrow():
    """Return the target point below a tutorial's yellow downward arrow.

    The detector uses the current forced tutorial arrow silhouette: a bright
    yellow/gold down arrow with a full-width middle head and a narrower lower
    tip. Skill icons and UI borders may share the color, so color is only the
    first pass; the click requires the arrow-like row projection below.
    """
    width, height = display_size()
    scale_x, scale_y = display_scales(width, height)
    area_scale = scale_x * scale_y

    image = capture_cv()
    if image is None:
        return None
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv,
        np.array([20, 145, 175], dtype=np.uint8),
        np.array([34, 255, 255], dtype=np.uint8),
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contour_result = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = contour_result[-2]
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if not (800.0 * area_scale <= area <= 4200.0 * area_scale):
            continue
        if not (
            55 * scale_x <= box_width <= 85 * scale_x
            and 52 * scale_y <= box_height <= 75 * scale_y
        ):
            continue
        fill = area / float(box_width * box_height)
        if not 0.48 <= fill <= 0.68:
            continue

        row_counts = [
            int(np.count_nonzero(mask[y + row, x:x + box_width]))
            for row in range(box_height)
        ]
        top_rows = row_counts[:max(1, box_height // 3)]
        middle_rows = row_counts[box_height // 3:max(1, 2 * box_height // 3)]
        bottom_rows = row_counts[2 * box_height // 3:]
        top_mean = float(np.mean(top_rows))
        middle_mean = float(np.mean(middle_rows))
        bottom_mean = float(np.mean(bottom_rows))
        wide_rows = [count for count in row_counts if count >= box_width * 0.86]
        first_wide_row = next(
            (index for index, count in enumerate(row_counts)
             if count >= box_width * 0.86),
            -1,
        )
        if (
            not wide_rows
            or first_wide_row < box_height * 0.30
            or first_wide_row > box_height * 0.55
            or middle_mean < top_mean * 1.20
            or middle_mean < bottom_mean * 1.08
            or row_counts[-1] > box_width * 0.46
        ):
            continue
        candidates.append((area, x, y, box_width, box_height))

    if len(candidates) != 1:
        return None
    _, x, y, box_width, box_height = candidates[0]
    target_x = int(x + box_width / 2)
    target_y = min(
        int(y + box_height + config.YELLOW_ARROW_CLICK_OFFSET_Y * scale_y),
        int(height * 0.94),
    )
    # Battle-preparation enemy portraits and yellow stars can form one bright
    # blob that resembles the tutorial arrow silhouette. A real tutorial arrow
    # for this page points at the lower-right buttons, not the enemy card area.
    # if (
    #     int(width * 0.56) <= target_x <= int(width * 0.93)
    #     and int(height * 0.24) <= target_y <= int(height * 0.58)
    # ):
    #     return None
    return target_x, target_y


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


def find_tutorial_highlight():
    """Find the concentric ripple centered on a guided tutorial control."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    # HoughCircles accepts one radius, so use the area-equivalent scale instead
    # of the smaller axis. On 1080x720 this is sqrt(0.675 * 0.8), not 0.675.
    scale = (scale_x * scale_y) ** 0.5
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 1.5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(40, int(70 * scale)),
        param1=85,
        param2=18,
        minRadius=max(18, int(24 * scale)),
        maxRadius=max(35, int(105 * scale)),
    )
    if circles is None:
        return None

    maximum = np.max(image, axis=2)
    minimum = np.min(image, axis=2)
    neutral_light = (minimum >= 88) & ((maximum - minimum) <= 90)
    yy, xx = np.ogrid[:height, :width]
    candidates = []
    for circle in circles[0]:
        center_x, center_y, radius = [int(value) for value in circle]
        if center_x >= int(width * 0.97) or center_y <= int(height * 0.06):
            continue
        distance_sq = (xx - center_x) ** 2 + (yy - center_y) ** 2
        best_ring = 0.0
        for delta in (-10, -5, 0, 5, 10):
            sample_radius = radius + int(delta * scale)
            if sample_radius <= 8:
                continue
            inner = max(1, sample_radius - max(2, int(3 * scale)))
            outer = sample_radius + max(2, int(3 * scale))
            annulus = (distance_sq >= inner * inner) & (distance_sq <= outer * outer)
            count = int(np.count_nonzero(annulus))
            if count:
                ratio = float(np.count_nonzero(neutral_light & annulus)) / float(count)
                best_ring = max(best_ring, ratio)
        if best_ring >= 0.08:
            candidates.append((best_ring, center_x, center_y))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    best = candidates[0]
    if len(candidates) > 1 and best[0] - candidates[1][0] < 0.025:
        # Multiple equally strong rings are ambiguous; wait for another frame.
        if abs(best[1] - candidates[1][1]) > 45 * scale or abs(best[2] - candidates[1][2]) > 45 * scale:
            return None
    return int(best[1]), int(best[2])


def find_tutorial_text_overlay():
    """Return the center of a generic dimmed tutorial text overlay.

    These overlays can contain changing copy, but consistently dim the entire
    scene and draw a wide, shallow, closed gold/brown instruction frame.
    """
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]

    dark_ratio = float(np.count_nonzero(value <= 70)) / float(value.size)
    if np.median(value) > 45 or dark_ratio < 0.75:
        return None

    border_mask = cv2.inRange(
        hsv,
        np.array([12, 60, 50], dtype=np.uint8),
        np.array([30, 220, 230], dtype=np.uint8),
    )
    border_mask = cv2.morphologyEx(
        border_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)),
    )
    contours = cv2.findContours(
        border_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    candidates = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            width * 0.38 <= box_width <= width * 0.70
            and height * 0.12 <= box_height <= height * 0.30
        ):
            continue
        aspect = box_width / float(box_height)
        if not 2.2 <= aspect <= 7.0:
            continue

        area = float(cv2.contourArea(contour))
        fill = area / float(box_width * box_height)
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if fill < 0.78 or not 4 <= len(polygon) <= 12:
            continue
        candidates.append((fill, box_width, x, y, box_height))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    _, box_width, x, y, box_height = candidates[0]
    ripple_target = _find_tutorial_ripple_motion(
        image,
        (x, y, box_width, box_height),
    )
    if ripple_target is not None:
        return ripple_target
    return int(x + box_width / 2), int(y + box_height / 2)


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


def _find_tutorial_ripple_motion(first_image, overlay_box):
    """Locate the animated concentric ripple from a short frame sequence."""
    gray_frames = [cv2.cvtColor(first_image, cv2.COLOR_BGR2GRAY)]
    for _ in range(4):
        time.sleep(0.12)
        frame = capture_cv()
        if frame is None:
            continue
        gray_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    if len(gray_frames) < 3:
        return None

    stack = np.stack(gray_frames, axis=0).astype(np.int16)
    motion = np.max(stack, axis=0) - np.min(stack, axis=0)
    motion_mask = (motion >= 18).astype(np.uint8) * 255

    # The instruction panel itself is not the click target. Removing it also
    # prevents animated/antialiased text from competing with the ripple.
    x, y, box_width, box_height = overlay_box
    motion_mask[y:y + box_height, x:x + box_width] = 0
    motion_mask = cv2.morphologyEx(
        motion_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)),
    )
    motion_mask = cv2.dilate(
        motion_mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
    )

    height, width = motion_mask.shape[:2]
    candidates = []
    contours = cv2.findContours(
        motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    for contour in contours:
        area = float(cv2.contourArea(contour))
        box_x, box_y, moving_width, moving_height = cv2.boundingRect(contour)
        if not (
            area >= 300
            and 20 <= moving_width <= width * 0.28
            and 20 <= moving_height <= height * 0.32
        ):
            continue

        component_mask = np.zeros_like(motion_mask)
        cv2.drawContours(component_mask, [contour], -1, 255, -1)
        selected = component_mask > 0
        weights = motion * selected
        total_weight = float(np.sum(weights))
        if total_weight <= 0:
            continue
        yy, xx = np.indices(motion.shape)
        center_x = int(round(float(np.sum(xx * weights)) / total_weight))
        center_y = int(round(float(np.sum(yy * weights)) / total_weight))
        candidates.append((area, center_x, center_y))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1], candidates[0][2]

def find_stage_battle_button_with_locked_next(observation):
    """Find an unlocked stage button only when the next stage is locked.

    The stage list is self-drawn and ML Kit can read ``战斗`` as ``战头``.
    Use the stable menu headings to establish the page, then identify the
    bright action button followed immediately by the dim locked-stage button.
    """
    if not (
        observation.contains("掉落信息")
        and (observation.contains("难度") or observation.contains("普通"))
    ):
        return None

    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 120)
    contours = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )[-2]

    buttons = []
    for contour in contours:
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            box_x >= int(width * 0.84)
            and int(height * 0.25) <= box_y <= int(height * 0.88)
            and int(width * 0.06) <= box_width <= int(width * 0.11)
            and int(height * 0.09) <= box_height <= int(height * 0.15)
        ):
            continue
        ratio = box_width / float(box_height)
        if not 0.75 <= ratio <= 1.30:
            continue

        # Canny produces several nested outlines for one framed button.
        duplicate = False
        for old in buttons:
            if abs(old["x"] - box_x) <= 6 and abs(old["y"] - box_y) <= 6:
                if box_width * box_height > old["width"] * old["height"]:
                    old.update(
                        {
                            "x": box_x,
                            "y": box_y,
                            "width": box_width,
                            "height": box_height,
                        }
                    )
                duplicate = True
                break
        if not duplicate:
            buttons.append(
                {
                    "x": box_x,
                    "y": box_y,
                    "width": box_width,
                    "height": box_height,
                }
            )

    buttons.sort(key=lambda item: item["y"])
    for index in range(len(buttons) - 1):
        battle = buttons[index]
        locked = buttons[index + 1]
        center_gap = (
            locked["y"] + locked["height"] / 2.0
            - battle["y"] - battle["height"] / 2.0
        )
        if not int(height * 0.12) <= center_gap <= int(height * 0.20):
            continue
        if abs(locked["x"] - battle["x"]) > int(width * 0.02):
            continue

        def bright_ratio(button):
            inset_x = max(3, int(button["width"] * 0.14))
            inset_y = max(3, int(button["height"] * 0.14))
            roi = image[
                button["y"] + inset_y:
                button["y"] + button["height"] - inset_y,
                button["x"] + inset_x:
                button["x"] + button["width"] - inset_x,
            ]
            if roi.size == 0:
                return 0.0
            value = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 2]
            return float(np.mean(value > 190))

        battle_brightness = bright_ratio(battle)
        locked_brightness = bright_ratio(locked)
        if (
            battle_brightness >= 0.45
            and locked_brightness <= 0.38
            and battle_brightness - locked_brightness >= 0.18
        ):
            return (
                int(battle["x"] + battle["width"] / 2),
                int(battle["y"] + battle["height"] / 2),
            )
    return None


def battle_start_is_disabled(observation, image=None):
    """Return True only when the preparation-page Start Battle button is dim."""
    if not observation.contains_all("领队", "对战", "开始战"):
        return False
    start_rows = observation.matching(
        lambda row: row["text"] == "开始战斗" or row["text"] == "开始战"
    )
    if len(start_rows) != 1:
        return False
    if image is None:
        image = capture_cv()
    if image is None:
        return False
    height, width = image.shape[:2]
    start = start_rows[0]
    half_width = int(width * 0.095)
    half_height = int(height * 0.065)
    x0 = max(0, start["x"] - half_width)
    x1 = min(width, start["x"] + half_width)
    y0 = max(0, start["y"] - half_height)
    y1 = min(height, start["y"] + half_height)
    roi = image[y0:y1, x0:x1]
    if roi.size == 0:
        return False
    value = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 2]
    return float(np.mean(value > 190)) <= 0.20


def find_highest_star_team_members(observation, limit=4):
    """Return selectable monster cards ordered by descending star count.

    This preparation screen is self-drawn.  Card frames establish the dynamic
    grid, while yellow and awakened-magenta star shapes provide the ranking.
    Candidates are returned only while the Start Battle button is visibly dim.
    """
    # `结束战斗` was observed as `東战斗` on this exact screen, so it is not
    # stable enough to use as a required page anchor.
    if not observation.contains_all("领队", "对战", "开始战"):
        return []

    image = capture_cv()
    if image is None:
        return []
    height, width = image.shape[:2]
    if not battle_start_is_disabled(observation, image):
        return []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 130)
    contours = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    frame_centers = []
    frame_widths = []
    frame_heights = []
    for contour in contours:
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            int(width * 0.055) <= box_width <= int(width * 0.095)
            and int(height * 0.09) <= box_height <= int(height * 0.14)
            and int(width * 0.06) <= box_x <= int(width * 0.72)
            and int(height * 0.62) <= box_y <= int(height * 0.90)
        ):
            continue
        frame_centers.append(
            (box_x + box_width / 2.0, box_y + box_height / 2.0)
        )
        frame_widths.append(box_width)
        frame_heights.append(box_height)
    if len(frame_centers) < 4:
        return []

    def clustered(values, distance):
        groups = []
        for value in sorted(values):
            if not groups or value - np.mean(groups[-1]) > distance:
                groups.append([value])
            else:
                groups[-1].append(value)
        return [int(round(float(np.median(group)))) for group in groups]

    columns = clustered(
        [point[0] for point in frame_centers], width * 0.02
    )
    rows = clustered(
        [point[1] for point in frame_centers], height * 0.035
    )
    if not columns or not rows:
        return []

    card_width = int(round(float(np.median(frame_widths))))
    card_height = int(round(float(np.median(frame_heights))))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    monsters = []
    for center_y in rows:
        for center_x in columns:
            left = int(center_x - card_width / 2.0)
            top = int(center_y - card_height / 2.0)
            star_roi = hsv[
                top + 3:top + 28,
                left + 3:left + int(card_width * 0.72),
            ]
            if star_roi.size == 0:
                continue
            yellow = cv2.inRange(
                star_roi,
                np.array([18, 120, 150], dtype=np.uint8),
                np.array([38, 255, 255], dtype=np.uint8),
            )
            awakened = cv2.inRange(
                star_roi,
                np.array([140, 90, 110], dtype=np.uint8),
                np.array([179, 255, 255], dtype=np.uint8),
            )
            star_mask = cv2.bitwise_or(yellow, awakened)
            star_contours = cv2.findContours(
                star_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )[-2]
            star_count = 0
            for star in star_contours:
                star_x, star_y, star_width, star_height = cv2.boundingRect(star)
                area = float(cv2.contourArea(star))
                if (
                    star_y <= 6
                    and 10 <= star_width <= 20
                    and 14 <= star_height <= 20
                    and 50 <= area <= 140
                ):
                    star_count += 1
            if star_count:
                monsters.append(
                    {
                        "point": (center_x, center_y),
                        "stars": star_count,
                    }
                )

    monsters.sort(
        key=lambda item: (
            -item["stars"],
            item["point"][1],
            item["point"][0],
        )
    )
    return monsters[:limit]


def find_support_monsters(observation):
    """Return selectable friend-support monsters from the support popup."""
    if not observation.contains("好友魔灵"):
        return []

    image = capture_cv()
    if image is None:
        return []
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    ocr_slot_monsters = _find_support_monsters_by_ocr_slots(observation, width, height)
    occupied_slot_monsters = _find_support_monsters_by_slot_occupancy(image)
    dynamic_monsters = _find_support_monsters_by_frames(image, hsv)

    # Friend support popup is a fixed self-drawn grid. Count cards by checking
    # for real star colors in each slot; empty slots have the frame but no stars.
    columns = [360, 488, 616, 744, 872, 1000, 1128, 1256]
    rows = [294, 446, 598]
    monsters = []
    for ref_y in rows:
        for ref_x in columns:
            center_x = int(ref_x * scale_x)
            center_y = int(ref_y * scale_y)
            left = int((ref_x - 58) * scale_x)
            top = int((ref_y - 55) * scale_y)
            right = int((ref_x + 58) * scale_x)
            bottom = int((ref_y - 18) * scale_y)
            left = max(0, left)
            top = max(0, top)
            right = min(width, right)
            bottom = min(height, bottom)
            star_roi = hsv[top:bottom, left:right]
            if star_roi.size == 0:
                continue
            yellow = cv2.inRange(
                star_roi,
                np.array([18, 110, 130], dtype=np.uint8),
                np.array([40, 255, 255], dtype=np.uint8),
            )
            awakened = cv2.inRange(
                star_roi,
                np.array([135, 70, 100], dtype=np.uint8),
                np.array([179, 255, 255], dtype=np.uint8),
            )
            orange = cv2.inRange(
                star_roi,
                np.array([5, 120, 120], dtype=np.uint8),
                np.array([18, 255, 255], dtype=np.uint8),
            )
            star_mask = cv2.bitwise_or(cv2.bitwise_or(yellow, awakened), orange)
            star_mask = cv2.morphologyEx(
                star_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)
            )
            contours = cv2.findContours(
                star_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )[-2]
            star_count = 0
            for contour in contours:
                area = float(cv2.contourArea(contour))
                _, _, box_width, box_height = cv2.boundingRect(contour)
                if (
                    45.0 * scale_x * scale_y <= area <= 260.0 * scale_x * scale_y
                    and 8 * scale_x <= box_width <= 25 * scale_x
                    and 8 * scale_y <= box_height <= 25 * scale_y
                ):
                    star_count += 1
            if star_count:
                monsters.append(
                    {
                        "point": (center_x, center_y),
                        "stars": star_count,
                    }
                )

    detector_results = (
        ocr_slot_monsters,
        occupied_slot_monsters,
        dynamic_monsters,
        monsters,
    )
    best_result = max(detector_results, key=len)
    best_result.sort(key=lambda item: (item["point"][1], item["point"][0]))
    return best_result


def _find_support_monsters_by_ocr_slots(observation, width, height):
    """Return occupied support slots using the real 1080x720 popup grid."""
    scale_x = width / 1080.0
    scale_y = height / 720.0
    columns = [237, 324, 411, 498, 585, 672, 759, 846]
    rows = [254, 357, 460]
    monsters = []

    for ref_y in rows:
        center_y = int(ref_y * scale_y)
        for ref_x in columns:
            center_x = int(ref_x * scale_x)
            occupied = False
            for row in observation.rows:
                text = row["text"]
                if not text:
                    continue
                if abs(row["x"] - center_x) > int(50 * scale_x):
                    continue
                if not (
                    center_y + int(8 * scale_y)
                    <= row["y"]
                    <= center_y + int(64 * scale_y)
                ):
                    continue
                if any(ch.isdigit() for ch in text) or len(text) >= 3:
                    occupied = True
                    break

            if occupied:
                monsters.append(
                    {
                        "point": (center_x, center_y),
                        "stars": 0,
                    }
                )

    monsters.sort(key=lambda item: (item["point"][1], item["point"][0]))
    return monsters


def _find_support_monsters_by_slot_occupancy(image):
    """Count occupied cards from image detail inside each fixed support slot."""
    height, width = image.shape[:2]
    scale_x = width / 1080.0
    scale_y = height / 720.0
    columns = [237, 324, 411, 498, 585, 672, 759, 846]
    rows = [254, 357, 460]
    monsters = []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    for ref_y in rows:
        center_y = int(ref_y * scale_y)
        for ref_x in columns:
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
            if float(card_roi.std()) >= 18.0 and edge_density >= 0.08:
                monsters.append(
                    {
                        "point": (center_x, center_y),
                        "stars": 0,
                    }
                )

    return monsters


def _find_support_monsters_by_frames(image, hsv):
    """Find support cards from visible frame geometry, then verify stars."""
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    area_scale = scale_x * scale_y

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 45, 130)
    contours = cv2.findContours(
        edges,
        cv2.RETR_LIST,
        cv2.CHAIN_APPROX_SIMPLE,
    )[-2]

    frames = []
    for contour in contours:
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            int(width * 0.14) <= box_x <= int(width * 0.88)
            and int(height * 0.18) <= box_y <= int(height * 0.86)
            and int(70 * scale_x) <= box_width <= int(150 * scale_x)
            and int(85 * scale_y) <= box_height <= int(170 * scale_y)
        ):
            continue
        aspect = box_width / float(box_height)
        if not 0.62 <= aspect <= 1.10:
            continue

        duplicate = False
        for old in frames:
            if (
                abs(old["x"] - box_x) <= max(4, int(10 * scale_x))
                and abs(old["y"] - box_y) <= max(4, int(10 * scale_y))
            ):
                if box_width * box_height > old["width"] * old["height"]:
                    old.update(
                        {
                            "x": box_x,
                            "y": box_y,
                            "width": box_width,
                            "height": box_height,
                        }
                    )
                duplicate = True
                break
        if not duplicate:
            frames.append(
                {
                    "x": box_x,
                    "y": box_y,
                    "width": box_width,
                    "height": box_height,
                }
            )

    monsters = []
    for frame in frames:
        star_left = frame["x"] + int(frame["width"] * 0.05)
        star_top = frame["y"] + int(frame["height"] * 0.04)
        star_right = frame["x"] + int(frame["width"] * 0.80)
        star_bottom = frame["y"] + int(frame["height"] * 0.28)
        star_left = max(0, star_left)
        star_top = max(0, star_top)
        star_right = min(width, star_right)
        star_bottom = min(height, star_bottom)
        star_roi = hsv[star_top:star_bottom, star_left:star_right]
        if star_roi.size == 0:
            continue

        yellow = cv2.inRange(
            star_roi,
            np.array([18, 110, 130], dtype=np.uint8),
            np.array([40, 255, 255], dtype=np.uint8),
        )
        awakened = cv2.inRange(
            star_roi,
            np.array([135, 70, 100], dtype=np.uint8),
            np.array([179, 255, 255], dtype=np.uint8),
        )
        orange = cv2.inRange(
            star_roi,
            np.array([5, 120, 120], dtype=np.uint8),
            np.array([18, 255, 255], dtype=np.uint8),
        )
        star_mask = cv2.bitwise_or(cv2.bitwise_or(yellow, awakened), orange)
        star_mask = cv2.morphologyEx(
            star_mask,
            cv2.MORPH_OPEN,
            np.ones((2, 2), np.uint8),
        )
        star_contours = cv2.findContours(
            star_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )[-2]

        star_count = 0
        for star in star_contours:
            area = float(cv2.contourArea(star))
            _, _, star_width, star_height = cv2.boundingRect(star)
            if (
                35.0 * area_scale <= area <= 300.0 * area_scale
                and 6 * scale_x <= star_width <= 28 * scale_x
                and 6 * scale_y <= star_height <= 28 * scale_y
            ):
                star_count += 1
        if not star_count:
            continue

        monsters.append(
            {
                "point": (
                    int(frame["x"] + frame["width"] / 2),
                    int(frame["y"] + frame["height"] / 2),
                ),
                "stars": star_count,
            }
        )

    monsters.sort(key=lambda item: (item["point"][1], item["point"][0]))
    return monsters


def auto_battle_is_off():
    """Detect the lower-left play triangle without matching pause bars."""
    image = capture_cv()
    if image is None:
        return False
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    area_scale = scale_x * scale_y
    x0, y0 = scale_point((260, 805))
    x1, y1 = scale_point((330, 875))
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
        if not (350 * area_scale <= area <= 1500 * area_scale):
            continue
        if not (
            25 * scale_x <= box_width <= 55 * scale_x
            and 30 * scale_y <= box_height <= 60 * scale_y
        ):
            continue
        fill = area / float(box_width * box_height)
        if not 0.35 <= fill <= 0.72:
            continue
        center_x = box_x + box_width / 2.0
        center_y = box_y + box_height / 2.0
        if not (
            22 * scale_x <= center_x <= 48 * scale_x
            and 20 * scale_y <= center_y <= 50 * scale_y
        ):
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.06 * perimeter, True)
        if 3 <= len(polygon) <= 5:
            return True
    return False


def dialogue_present(observation):
    """Detect the game's bottom dialogue panel without treating menus as dialogue.

    Verified dialogue layouts place a short speaker label near an outer edge at
    y=620..760 and one or more sentences below y=735. Both anchors are required.
    """
    width, height = display_size()

    # MLKit sometimes merges the speaker plaque and all dialogue lines into one
    # tall block (verified with `奇怪的少女` plus two sentences).  In that
    # layout the block starts at the speaker height and extends into the body.
    def looks_like_combined_dialogue(row):
        if not (
            # Post-battle dialogue may merge a low speaker plaque and both
            # lines into one block (verified `丛林之声`: center y=622/720).
            int(height * 0.68) <= row["y"] <= int(height * 0.90)
            and row["x"] <= int(width * 0.45)
            and len(re.sub(r"\s+", "", row["text"])) >= 15
            and (
                "\n" in row["text"]
                or re.search(r"[，。！？~,.!?]", row["text"]) is not None
            )
        ):
            return False

        # A genuinely merged dialogue block starts around the speaker plaque
        # and extends down into the bottom dialogue body. Reward descriptions
        # on map menus can also be long and multiline, but end much higher
        # (verified false hit: rect bottom 518 on a 720px screen).
        rect = _value(row["raw"], "rect")
        if rect is None:
            return False
        if isinstance(rect, dict):
            top = rect.get("top")
            bottom = rect.get("bottom")
        else:
            # Android AScript returns java.jarray('I'), which is indexable but
            # is not an instance of Python list/tuple.
            try:
                if len(rect) == 4:
                    top = rect[1]
                    bottom = rect[3]
                else:
                    top = _value(rect, "top")
                    bottom = _value(rect, "bottom")
            except (TypeError, AttributeError):
                top = _value(rect, "top")
                bottom = _value(rect, "bottom")
        if top is None or bottom is None:
            # Without real bounds we cannot prove that this is one tall OCR
            # block spanning speaker and dialogue body.
            return False
        return (
            int(bottom) >= int(height * 0.84)
            and int(bottom) - int(top) >= int(height * 0.10)
        )

    combined_rows = observation.matching(looks_like_combined_dialogue)
    if combined_rows:
        return True

    def looks_like_speaker(row):
        chinese = re.sub(r"[^\u4e00-\u9fff]", "", row["text"])
        compact = re.sub(r"\s+", "", row["text"])
        return (
            int(height * 0.68) <= row["y"] <= int(height * 0.83)
            and (row["x"] <= int(width * 0.24) or row["x"] >= int(width * 0.76))
            and 2 <= len(chinese) <= 6
            # Decorative diamonds around the speaker plaque are sometimes
            # recognized as digits or punctuation (verified: `-4艾琳4`).
            # Position + short Chinese name remain the primary anchors.
            and len(compact) <= 12
        )

    speaker_rows = observation.matching(
        looks_like_speaker
    )
    def looks_like_dialogue_body(row):
        compact = re.sub(r"\s+", "", row["text"])
        if not (
            row["y"] >= int(height * 0.80)
            # Dialogue copy is centered in the main bottom panel. Right-side
            # event menus place their promotional line farther to the right.
            and row["x"] <= int(width * 0.70)
            # Some cinematic lines are intentionally short (verified:
            # `小心啊!`). The speaker-label anchor remains independently
            # required.
            and len(compact) >= 3
            and (
                len(compact) >= 12
                or re.search(r"[，。！？…~,.!?]", row["text"])
            )
        ):
            return False

        rect = _value(row["raw"], "rect")
        if rect is None:
            return False
        if isinstance(rect, dict):
            left = rect.get("left")
            right = rect.get("right")
        else:
            try:
                if len(rect) == 4:
                    left = rect[0]
                    right = rect[2]
                else:
                    left = _value(rect, "left")
                    right = _value(rect, "right")
            except (TypeError, AttributeError):
                left = _value(rect, "left")
                right = _value(rect, "right")
        if left is None or right is None:
            return False

        # OCR fragments cut from large map labels can contain only a few
        # characters while their rectangle spans a very wide graphical area
        # (verified false hit: `异界。`, 209px for 3 chars at 1080px). Normal
        # dialogue glyphs remain within this generous per-character width.
        average_character_width = (int(right) - int(left)) / float(len(compact))
        return average_character_width <= width * 0.05

    body_rows = observation.matching(looks_like_dialogue_body)
    return bool(speaker_rows and body_rows)
