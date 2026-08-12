"""Pure visual-shape rules used by world-map detectors."""


def is_bright_world_map_star(area, width, height, scale):
    """Return whether one yellow contour has the geometry of a map star."""
    if scale <= 0:
        return False
    aspect = width / float(max(1, height))
    return (
        110.0 * scale * scale <= area <= 400.0 * scale * scale
        and 16.0 * scale <= width <= 28.0 * scale
        and 16.0 * scale <= height <= 28.0 * scale
        and 0.75 <= aspect <= 1.30
    )


def is_home_summon_circle_component(
    area, width, height, fill_ratio, scale_x, scale_y
):
    """Return whether a cyan/purple component can be the Summonhenge core."""
    if scale_x <= 0 or scale_y <= 0:
        return False
    normalized_width = width / float(scale_x)
    normalized_height = height / float(scale_y)
    normalized_area = area / float(scale_x * scale_y)
    aspect = normalized_width / float(max(1.0, normalized_height))
    return (
        100 <= normalized_width <= 180
        and 70 <= normalized_height <= 115
        and 4500 <= normalized_area <= 12000
        and 1.25 <= aspect <= 1.75
        and 0.45 <= fill_ratio <= 0.90
    )
