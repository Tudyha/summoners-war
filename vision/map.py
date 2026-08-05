"""World-map and home-island visual detectors."""

import cv2
import numpy as np
from ..core.map_rules import is_bright_world_map_star
from .core import capture_frame_image as capture_cv
from .core import display_scales, scale_point

def find_world_map_in_progress_area(observation):
    """Return the only unlocked visible story area with zero bright stars."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    story_names = (
        "加仑",
        "加仑从林",
        "西泽山",
        "卡菲勒",
        "拉古恩雪山",
        "卡菲勒遗址",
        "年勒遗址",
        "年勃遗址",
        "特拉恩",
        "特拉恩丛林",
        "夏依德尼",
        "夏依德尼遗址",
        "保罗帕",
        "帕伊摩恩",
        "帕伊摩恩火山",
        "塔摩勒沙",
        "塔摩勒沙漠",
        "艾登",
        "佩伦",
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
    # OCR often corrupts the first half of an area name (卡菲勒遗址 has
    # appeared as 年勒遗址 and 一勒遗址). The stable suffix identifies the
    # label; the star and padlock checks below determine its actual state.
    story_suffixes = ("遗址", "丛林", "雪山", "沙漠", "火山", "古城")
    rows = []
    for row in observation.rows:
        text = row["text"]
        if any(name in text for name in non_story_names):
            continue
        if not (
            any(name in text for name in story_names)
            or any(suffix in text for suffix in story_suffixes)
        ):
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
        star_scale = min(width / 1080.0, height / 720.0)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            _, _, box_width, box_height = cv2.boundingRect(contour)
            if is_bright_world_map_star(
                area, box_width, box_height, star_scale
            ):
                star_blobs += 1
        # A locked future area also has zero stars. Its stable beige padlock is
        # a 30x36 component on 1080x720, immediately above the area label.
        lock_rect = [
            max(0, int(row["x"] - 80 * width / 1080.0)),
            max(0, int(row["y"] - 90 * height / 720.0)),
            min(width, int(row["x"] + 80 * width / 1080.0)),
            max(0, int(row["y"] - 15 * height / 720.0)),
        ]
        lock_roi = hsv[
            lock_rect[1]:lock_rect[3], lock_rect[0]:lock_rect[2]
        ]
        neutral_bright = cv2.inRange(
            lock_roi,
            np.array([0, 0, 120], dtype=np.uint8),
            np.array([179, 140, 255], dtype=np.uint8),
        )
        neutral_bright = cv2.morphologyEx(
            neutral_bright,
            cv2.MORPH_CLOSE,
            np.ones((3, 3), dtype=np.uint8),
        )
        locked = False
        lock_scale_x = width / 1080.0
        lock_scale_y = height / 720.0
        for contour in cv2.findContours(
            neutral_bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )[-2]:
            area = float(cv2.contourArea(contour))
            _, _, box_width, box_height = cv2.boundingRect(contour)
            fill = area / float(max(1, box_width * box_height))
            if (
                24 * lock_scale_x <= box_width <= 38 * lock_scale_x
                and 30 * lock_scale_y <= box_height <= 44 * lock_scale_y
                and 600 * lock_scale_x * lock_scale_y
                <= area
                <= 1200 * lock_scale_x * lock_scale_y
                and 0.65 <= fill <= 0.90
            ):
                locked = True
                break

        # Story semantics verified on the live map: one or more stars means
        # completed; zero stars without the padlock is the active area.
        if star_blobs == 0 and not locked:
            candidates.append(row)

    if len(candidates) != 1:
        return None

    row = candidates[0]
    return row["x"], row["y"]

def world_map_area_star_count(observation, name_fragments):
    """Return the bright-star count below one named visible world-map area."""
    rows = observation.matching(
        lambda row: any(
            fragment in row["text"] for fragment in name_fragments
        )
    )
    if len(rows) != 1:
        return None

    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    row = rows[0]
    star_rect = [
        max(0, int(row["x"] - 75 * scale_x)),
        max(0, int(row["y"] + 28 * scale_y)),
        min(width, int(row["x"] + 75 * scale_x)),
        min(height, int(row["y"] + 72 * scale_y)),
    ]
    if star_rect[0] >= star_rect[2] or star_rect[1] >= star_rect[3]:
        return None

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    roi = hsv[star_rect[1]:star_rect[3], star_rect[0]:star_rect[2]]
    yellow = cv2.inRange(
        roi,
        np.array([18, 120, 140], dtype=np.uint8),
        np.array([38, 255, 255], dtype=np.uint8),
    )
    star_count = 0
    star_scale = min(width / 1080.0, height / 720.0)
    for contour in cv2.findContours(
        yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]:
        area = float(cv2.contourArea(contour))
        _, _, box_width, box_height = cv2.boundingRect(contour)
        if is_bright_world_map_star(
            area, box_width, box_height, star_scale
        ):
            star_count += 1
    return star_count

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
