"""Visual detectors used during startup and login."""

from .core import display_size

def find_guest_login(observation):
    """Tolerate the verified ML Kit result `游窖登录`."""
    _, height = display_size()
    return observation.matching(
        lambda row: row["text"].startswith("游")
        and row["text"].endswith("登录")
        and row["y"] > 0.45 * height
    )
