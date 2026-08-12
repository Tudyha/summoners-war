"""OCR observation and display geometry primitives."""

from ascript.android.screen import Ocr, capture_cv as device_capture_cv
from ascript.android.system import Device

from .. import config


_NO_IMAGE = object()
_frame_image = _NO_IMAGE


def begin_visual_frame():
    """Invalidate the lazy screenshot cache at the start of a decision tick."""
    global _frame_image
    _frame_image = _NO_IMAGE


def capture_frame_image():
    """Return one shared screenshot for all visual detectors in this tick."""
    global _frame_image
    if _frame_image is _NO_IMAGE:
        _frame_image = device_capture_cv()
    return _frame_image


def capture_fresh_image():
    """Capture a new image for detectors that explicitly compare animation frames."""
    return device_capture_cv()

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
    """Return independent X/Y scales from the 1080x720 reference frame."""
    if width is None or height is None:
        width, height = display_size()
    return (
        width / float(config.REFERENCE_WIDTH),
        height / float(config.REFERENCE_HEIGHT),
    )
