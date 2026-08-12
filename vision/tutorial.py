"""Tutorial arrow, highlight, overlay, and dialogue detectors."""

import re

from ..core.collaboration_rules import is_gameplay_screen
from ..core.summon_rules import is_summon_ui_title
import time

import cv2
import numpy as np
from ascript.android.screen import FindColors
from ascript.android.system import R

from .. import config
from .core import (
    _value,
    capture_fresh_image,
    capture_frame_image as capture_cv,
    display_scales,
    display_size,
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
        if not (432.0 * area_scale <= area <= 2268.0 * area_scale):
            continue
        if not (
            37.125 * scale_x <= box_width <= 57.375 * scale_x
            and 41.6 * scale_y <= box_height <= 60 * scale_y
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

def find_tutorial_highlight():
    """Find the concentric ripple centered on a guided tutorial control."""
    image = capture_cv()
    if image is None:
        return None
    height, width = image.shape[:2]
    scale_x, scale_y = display_scales(width, height)
    # HoughCircles accepts one radius, so use the area-equivalent scale.
    scale = (scale_x * scale_y) ** 0.5
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 1.5)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(40, int(51.43 * scale)),
        param1=85,
        param2=18,
        minRadius=max(18, int(17.64 * scale)),
        maxRadius=max(35, int(77.15 * scale)),
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
        for delta in (-7, -4, 0, 4, 7):
            sample_radius = radius + int(delta * scale)
            if sample_radius <= 8:
                continue
            inner = max(1, sample_radius - max(2, int(2.2 * scale)))
            outer = sample_radius + max(2, int(2.2 * scale))
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
        if abs(best[1] - candidates[1][1]) > 33 * scale or abs(best[2] - candidates[1][2]) > 33 * scale:
            return None
    return int(best[1]), int(best[2])

def find_tutorial_text_overlay():
    """Return the next safe target for a generic tutorial text overlay.

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
    # Story guides use a very dark mask, while the collaboration minigame
    # keeps the board readable beneath a substantially lighter one.  The real
    # minigame guide measured median V=69 and dark_ratio=0.515.  The closed
    # instruction-frame test below remains required, so these relaxed mask
    # limits do not turn an ordinary dim battle scene into a tutorial.
    if np.median(value) > 75 or dark_ratio < 0.48:
        return None

    # A dimmed business modal can also contain several gold/brown frames. The
    # item-replacement page is visually distinct because a large neutral-light
    # window remains undimmed (verified component: 27.1% of the frame,
    # 526x404 at 1080x720). Generic tutorial cards never expose such a large
    # bright window, so leave this screen to its owning flow even when OCR
    # transiently misses the modal title.
    bright_modal_mask = (
        (value >= 140) & (hsv[:, :, 1] <= 110)
    ).astype(np.uint8) * 255
    bright_modal_mask = cv2.morphologyEx(
        bright_modal_mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15)),
    )
    bright_contours = cv2.findContours(
        bright_modal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[-2]
    for bright_contour in bright_contours:
        bright_x, bright_y, bright_width, bright_height = cv2.boundingRect(
            bright_contour
        )
        bright_area = float(cv2.contourArea(bright_contour))
        if (
            bright_area >= width * height * 0.14
            and bright_width >= width * 0.40
            and bright_height >= height * 0.35
        ):
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
        center_y = y + box_height / 2.0
        # Footer/navigation panels can have the same gold rectangular border,
        # but verified tutorial instruction cards remain in the middle 60%.
        if not height * 0.16 <= center_y <= height * 0.76:
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
    # Some collaboration guides are static and have no animated ripple at all
    # (five fresh real-device frames were pixel-identical).  They advance when
    # the framed explanation itself is tapped.  Keeping the fallback inside
    # the already-proven frame avoids clicking arbitrary dim parts of battle.
    return int(x + box_width / 2), int(y + box_height / 2)

def _find_tutorial_ripple_motion(first_image, overlay_box):
    """Locate the animated concentric ripple from a short frame sequence."""
    gray_frames = [cv2.cvtColor(first_image, cv2.COLOR_BGR2GRAY)]
    for _ in range(4):
        time.sleep(0.12)
        # Motion detection must bypass the one-image-per-tick cache; otherwise
        # every frame is identical and the ripple can never be found.
        frame = capture_fresh_image()
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

def dialogue_present(observation):
    """Detect the game's bottom dialogue panel without treating menus as dialogue.

    Verified 1080x720 dialogue layouts place a short speaker label near an
    outer edge and one or more sentences in the bottom panel. Both anchors are
    required.
    """
    width, height = display_size()

    # Dice results place several short item values along the bottom and a
    # right-side confirmation button at dialogue height. Those fragments can
    # satisfy the generic speaker/body geometry, but the stable gameplay
    # anchors (关卡 plus 体力/护盾/骰子) prove CollaborationFlow ownership.
    if is_gameplay_screen(observation.texts):
        return False

    # Summon-result monster names and the bottom crystal price can satisfy the
    # loose speaker/body geometry. The result title is a definitive veto.
    if observation.contains("召唤结果"):
        return False

    # Summon buttons can satisfy the dialogue geometry: `特别召唤` looks like
    # a short speaker label and the `50,000` price looks like punctuated body
    # copy. The Summonhenge title is a definitive foreground veto.
    if any(is_summon_ui_title(text) for text in observation.texts):
        return False

    # Story stage lists can place a short map label near an outer edge and a
    # long reward description across the lower half, which accidentally fits
    # the speaker/body geometry. These anchors identify the stage menu and
    # must leave ownership to BattleFlow instead of tapping the dialogue point.
    if observation.contains("掉落信息") and (
        observation.contains("难度") or observation.contains("普通")
    ):
        return False

    # Battle preparation places the short `开始战斗` label at the lower-right
    # speaker-plaque height. A transient punctuated OCR fragment from monster
    # cards can then satisfy the body rule. These independent page anchors
    # establish battle ownership even when `结束战斗` is misread (`结東战!`).
    if observation.contains("开始战") and (
        observation.contains("对战") or observation.contains("领袖技能")
    ):
        return False

    # Home-island side labels and bottom navigation can accidentally satisfy
    # the loose speaker/body geometry, especially when a tree/building is
    # selected and its contextual menu replaces part of the bottom bar.
    # These anchors uniquely identify home and must veto dialogue detection.
    home_nav_hits = sum(
        1
        for text in ("战斗", "魔灵", "任务", "社交", "商店")
        if observation.contains(text)
    )
    home_account = any(text.startswith("LD") for text in observation.texts)
    if (
        observation.contains_all("召唤师之路", "收件箱")
        and (home_account or home_nav_hits >= 3)
    ):
        return False

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
        # Full-width activity/page footers terminate almost at the screen edge
        # (verified collaboration footer: right=1037/1080). Dialogue copy is
        # inset inside its bottom panel and does not reach that edge.
        return (
            average_character_width <= width * 0.05
            and int(right) <= int(width * 0.94)
        )

    body_rows = observation.matching(looks_like_dialogue_body)
    return bool(speaker_rows and body_rows)
