"""Pure rules used by the collaboration activity detectors."""


COLLABORATION_ACTIVITY_GUIDE_FRAGMENTS = (
    "全新活动地下城",
    "每次通关关卡",
    "联动角色一起挑战",
    "全新小游戏召唤",
    "桌游风格小游戏",
    "参与小游戏",
)


def is_collaboration_activity_guide(texts):
    """Recognize every observed page of the first-entry activity guide."""
    return any(
        fragment in str(text)
        for text in texts
        for fragment in COLLABORATION_ACTIVITY_GUIDE_FRAGMENTS
    )


def is_minigame_entrance_icon(teal_ratio, cream_ratio, dark_pip_count):
    """Recognize the dice medallion immediately left of the minigame entry.

    The check deliberately combines three independent features so the red
    notification badge, button text, or another round event icon cannot open
    the minigame by itself.
    """
    return (
        0.20 <= teal_ratio <= 0.72
        and 0.10 <= cream_ratio <= 0.42
        and 1 <= dark_pip_count <= 16
    )


def parse_achievement_count(texts):
    """Return the largest ``current/37`` collection counter exposed by OCR."""
    import re

    counts = []
    for text in texts:
        for current, total in re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})", str(text)):
            current = int(current)
            total = int(total)
            if total == 37 and 0 <= current <= total:
                counts.append(current)
    return max(counts) if counts else None


def parse_fraction(text):
    """Parse a small OCR fraction, accepting the common ``O`` for zero."""
    import re

    normalized = str(text).upper().replace("O", "0")
    match = re.search(r"(\d+)\s*/\s*(\d+)", normalized)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def parse_integer(text):
    """Parse an OCR row that consists only of one non-negative integer."""
    import re

    normalized = str(text).strip().replace(",", "")
    if not re.fullmatch(r"\d+", normalized):
        return None
    return int(normalized)


def is_shop_upgrade_confirmation(texts):
    """Match the shop prompt across simplified/traditional OCR output."""
    values = [str(text) for text in texts]

    def contains(fragment):
        return any(fragment in text for text in values)

    return contains("是否升") and contains("所选道具")


def is_shop_purchase_confirmation(texts):
    """Recognize the shop prompt for buying a not-yet-owned item."""
    values = [str(text) for text in texts]
    return (
        any("是否购买" in text for text in values)
        and any("所选道具" in text for text in values)
    )


def is_shop_insufficient_funds(texts):
    """Recognize the minigame shop's insufficient-coin modal."""
    values = [str(text) for text in texts]
    currency_words = ("铜", "銅", "硬币", "硬幣")
    return (
        any("持有" in text for text in values)
        and any(
            word in text
            for text in values
            for word in currency_words
        )
        and any("不足" in text for text in values)
    )


def choose_skill_candidate(priority, maxed_skill_indices=()):
    """Choose the first priority not already proven max-level."""
    maxed = set(maxed_skill_indices)
    for skill_index in priority:
        if skill_index not in maxed:
            return skill_index
    return None


def is_skill_max_badge(yellow_ratio):
    """Return whether the selected skill icon shows the yellow max badge."""
    return yellow_ratio >= 0.025


def is_gameplay_screen(texts):
    """Distinguish an active dice run from the minigame landing page."""
    values = [str(text) for text in texts]

    def contains(fragment):
        return any(fragment in text for text in values)

    # The landing page says both "关卡2" and "召唤骰子", which previously
    # satisfied the loose gameplay rule.  Its prepare button and three footer
    # tabs are stable negative evidence for an active run.
    if contains("游戏准备") or all(
        contains(fragment) for fragment in ("技能", "收集", "帮助")
    ):
        return False
    return contains("关卡") and any(
        contains(fragment) for fragment in ("体力", "护盾", "骰子")
    )


def is_collaboration_internal_screen(texts):
    """Recognize strong anchors for resuming inside the dice minigame.

    This is intentionally stricter than :func:`is_gameplay_screen`: regular
    story progression must retain ownership until the collaboration entrance
    appears, while a script restarted halfway through the minigame must be able
    to recover without seeing that entrance again.
    """
    values = [str(text) for text in texts]

    def contains(fragment):
        return any(fragment in text for text in values)

    if contains("刷取模式") and contains("请选择本次脚本目标"):
        return False

    if is_collaboration_activity_guide(values):
        return True

    # Story battle preparation and results reuse generic words such as 关卡,
    # 胜利 and 任务完成. They must retain normal tutorial/story ownership.
    if any(
        contains(fragment)
        for fragment in (
            "开始战斗", "结束战斗", "领袖技能", "对战",
            "[普通]", "[困难]", "[地狱]",
        )
    ):
        return False

    if contains("收集进度") or contains("技能升级") or contains("初始道具"):
        return True
    if contains("商店") and contains("道具"):
        return True
    if all(contains(fragment) for fragment in ("技能", "收集", "帮助")):
        return True
    if contains("召唤骰子") and contains("游戏准备"):
        return True

    gameplay_markers = sum(
        1 for fragment in ("体力", "护盾", "骰子") if contains(fragment)
    )
    if contains("关卡") and gameplay_markers >= 2:
        return True
    return False
