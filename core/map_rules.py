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
