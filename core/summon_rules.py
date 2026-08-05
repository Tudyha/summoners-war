"""Pure visual-shape rules for summon-scroll identification."""


SUMMON_UI_TITLES = (
    "魔灵召唤阵",
    "魔灵召喚阵",
    "召唤魔法阵",
    "召喚魔法陣",
)


def is_summon_ui_title(text):
    """Match only a standalone title, not dialogue mentioning the building."""
    normalized = str(text or "").strip(" |｜·")
    return normalized in SUMMON_UI_TITLES


def is_light_dark_scroll_icon_component(
    area, width, height, fill_ratio, scale_x, scale_y
):
    """Return whether one magenta component has the light-dark icon shape."""
    if scale_x <= 0 or scale_y <= 0:
        return False
    normalized_width = width / float(scale_x)
    normalized_height = height / float(scale_y)
    normalized_area = area / float(scale_x * scale_y)
    return (
        55 <= normalized_width <= 90
        and 65 <= normalized_height <= 100
        and 2500 <= normalized_area <= 6500
        and 0.45 <= fill_ratio <= 0.85
    )
