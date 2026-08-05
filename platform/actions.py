"""Device-side effects isolated from workflow decisions."""

import time

from ascript.android import action
from ascript.android.node import Selector

from .. import config
from ..vision.core import scale_point


class DeviceActions(object):
    """Execute one low-level device action and record its timestamp."""

    def __init__(self, state):
        self.state = state

    def _record(self):
        self.state.runtime.last_action_at = time.time()

    def click_xy(self, point_name, reason):
        x, y = scale_point(config.POINTS[point_name])
        action.click(x, y)
        self._record()
        print("[action] {} at ({}, {})".format(reason, x, y))

    def click_row(self, row, reason):
        action.click(row["x"], row["y"])
        self._record()
        print("[action] {}: {} at ({}, {})".format(
            reason, row["text"], row["x"], row["y"]
        ))

    def click_point(self, point, reason):
        action.click(point[0], point[1])
        self._record()
        print("[action] {} at ({}, {})".format(reason, point[0], point[1]))

    def press_back(self, reason):
        action.Key.back()
        self._record()
        print("[action] {} with device Back".format(reason))

    def swipe_xy(self, start_name, end_name, reason, dur=300):
        start = scale_point(config.POINTS[start_name])
        end = scale_point(config.POINTS[end_name])
        self.swipe_points(start, end, reason, dur)

    def swipe_points(self, start, end, reason, dur=300):
        action.swipe(start[0], start[1], end[0], end[1], dur)
        self._record()
        print("[action] {} from ({}, {}) to ({}, {})".format(
            reason, start[0], start[1], end[0], end[1]
        ))

    def find_node_by_id(self, resource_id):
        selector = Selector(mode=config.SELECTOR_MODE).id(resource_id)
        return selector, selector.find()

    def input_node(self, node, text):
        node.input(text)
        self._record()

    def input_text(self, text, selector=None):
        action.input(text, selector=selector)
        self._record()

    def ime_clear(self):
        action.Ime.input_clear()

    def ime_input(self, text):
        action.Ime.input(text)
        self._record()

    def click_node(self, node, reason):
        node.click()
        self._record()
        print("[action] {} with accessibility node".format(reason))
