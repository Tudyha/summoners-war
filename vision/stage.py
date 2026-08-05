"""Stage selection, team, and battle-control detectors."""

import cv2
import numpy as np
from ascript.android.screen import FindColors, FindImages
from ascript.android.system import R

from .. import config
from .core import capture_frame_image as capture_cv, display_scales, scale_point

def find_stage_battle_button_with_locked_next(observation, allow_last=False):
    """Find the active stage before a lock, or the bright final stage.

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

    # Stage 7 has no following locked row. Only enable this after the caller
    # has scrolled the list fully to the bottom; otherwise a clipped stage 4
    # on the initial view could be mistaken for the final stage.
    if allow_last and buttons:
        last = buttons[-1]
        if bright_ratio(last) >= 0.45:
            return (
                int(last["x"] + last["width"] / 2),
                int(last["y"] + last["height"] / 2),
            )
    return None

def battle_lower_left_controls_visible():
    """Confirm battle state from the three aligned lower-left control frames.

    Active battle screens expose three adjacent rounded-square buttons in the
    lower-left corner: settings, speed, and pause/play. Checking the complete
    three-button structure avoids treating the same chat bubble on home or
    preparation screens as permission to enter the friend fallback.
    """
    image = capture_cv()
    if image is None:
        return False
    height, width = image.shape[:2]
    scale = min(width / 1080.0, height / 720.0)
    if scale <= 0:
        return False

    # The verified 1080x720 frames occupy roughly x=10..235, y=648..710.
    region_top = max(0, int(height - 105 * scale))
    region_right = min(width, int(270 * scale))
    region = image[region_top:height, 0:region_right]
    if region.size == 0:
        return False

    maximum = np.max(region, axis=2)
    minimum = np.min(region, axis=2)
    neutral_bright = (
        (minimum >= 145)
        & ((maximum - minimum) <= 65)
    ).astype(np.uint8) * 255
    kernel_size = max(1, int(round(3 * scale)))
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    neutral_bright = cv2.morphologyEx(
        neutral_bright,
        cv2.MORPH_CLOSE,
        kernel,
    )

    frames = []
    contours = cv2.findContours(
        neutral_bright,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )[-2]
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area = float(cv2.contourArea(contour))
        if not (
            45 * scale <= box_width <= 78 * scale
            and 45 * scale <= box_height <= 78 * scale
        ):
            continue
        if area < 1200 * scale * scale:
            continue
        aspect = box_width / float(max(box_height, 1))
        if not 0.78 <= aspect <= 1.28:
            continue
        frames.append(
            (
                x + box_width / 2.0,
                region_top + y + box_height / 2.0,
            )
        )

    frames.sort(key=lambda point: point[0])
    for index in range(len(frames) - 2):
        trio = frames[index:index + 3]
        center_ys = [point[1] for point in trio]
        if max(center_ys) - min(center_ys) > 10 * scale:
            continue
        first_gap = trio[1][0] - trio[0][0]
        second_gap = trio[2][0] - trio[1][0]
        if not (
            58 * scale <= first_gap <= 100 * scale
            and 58 * scale <= second_gap <= 100 * scale
        ):
            continue
        if trio[0][0] <= 65 * scale and trio[2][0] <= 245 * scale:
            return True
    return False

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

def find_selected_team_members(observation):
    """Return occupied friendly formation cards on battle preparation."""
    if (
        observation.contains("好友魔灵")
        or not observation.contains("对战")
        or not observation.contains("开始战")
    ):
        return []

    image = capture_cv()
    if image is None:
        return []
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 130)
    contours = cv2.findContours(
        edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
    )[-2]

    centers = []
    for contour in contours:
        box_x, box_y, box_width, box_height = cv2.boundingRect(contour)
        if not (
            int(width * 0.065) <= box_width <= int(width * 0.11)
            and int(height * 0.10) <= box_height <= int(height * 0.16)
            and int(width * 0.05) <= box_x <= int(width * 0.48)
            and int(height * 0.14) <= box_y <= int(height * 0.56)
        ):
            continue
        aspect = box_width / float(max(1, box_height))
        if not 0.72 <= aspect <= 1.35:
            continue
        # The outer portrait frame is almost a filled rectangular contour.
        # Internal artwork contours can have the same bounding size but only
        # a small area, so exclude them before clustering duplicate borders.
        if cv2.contourArea(contour) < box_width * box_height * 0.75:
            continue

        card_roi = gray[
            box_y + int(box_height * 0.10):box_y + int(box_height * 0.90),
            box_x + int(box_width * 0.10):box_x + int(box_width * 0.90),
        ]
        if card_roi.size == 0:
            continue
        card_edges = cv2.Canny(card_roi, 60, 140)
        edge_density = (
            float(np.count_nonzero(card_edges)) / float(card_edges.size)
        )
        # Empty formation slots keep the same outer frame, but their gray
        # silhouette is nearly flat. On Android-125 the verified empty slot is
        # std=6.2/edge=0.005, versus std>=51/edge>=0.18 for real portraits.
        if float(card_roi.std()) < 18.0 or edge_density < 0.08:
            continue

        center = (
            int(box_x + box_width / 2.0),
            int(box_y + box_height / 2.0),
        )
        if any(
            abs(center[0] - old[0]) <= int(width * 0.008)
            and abs(center[1] - old[1]) <= int(height * 0.012)
            for old in centers
        ):
            continue
        centers.append(center)

    centers.sort(key=lambda point: (point[0], point[1]))
    return centers

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
