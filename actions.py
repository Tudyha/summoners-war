"""Reusable device actions for the Summoners War runner."""

import time

from ascript.android import action
from ascript.android.screen import Ocr
from . import config
from .vision import observe, scale_point


class ActionsMixin(object):
    def click_xy(self, point_name, reason):
        x, y = scale_point(config.POINTS[point_name])
        action.click(x, y)
        self.last_action_at = time.time()
        print("[action] {} at ({}, {})".format(reason, x, y))

    def click_row(self, row, reason):
        action.click(row["x"], row["y"])
        self.last_action_at = time.time()
        print("[action] {}: {} at ({}, {})".format(
            reason, row["text"], row["x"], row["y"]
        ))

    def find_and_click(self, text):
        res = Ocr.find_all(text)
        if res:
            for r in res:
                action.click(r["center_x"], r["center_y"])
                print("[action] find_and_click: {} at ({}, {})".format(
                    text, r["center_x"], r["center_y"]
                ))
            self.last_action_at = time.time()
            # print("[action] {}: {} at ({}, {})".format(
            #     "find_and_click", text, res["center_x"], res["center_y"]
            # ))
            return True
        return False

    def click_point(self, point, reason):
        action.click(point[0], point[1])
        self.last_action_at = time.time()
        print("[action] {} at ({}, {})".format(reason, point[0], point[1]))

    def press_back(self, reason):
        action.Key.back()
        self.last_action_at = time.time()
        print("[action] {} with device Back".format(reason))

    def swipe_xy(self, start_name, end_name, reason, dur=300):
        start_x, start_y = scale_point(config.POINTS[start_name])
        end_x, end_y = scale_point(config.POINTS[end_name])
        action.swipe(start_x, start_y, end_x, end_y, dur)
        self.last_action_at = time.time()
        print("[action] {} from ({}, {}) to ({}, {})".format(
            reason, start_x, start_y, end_x, end_y
        ))

    def select_four_team_members(self):
        for index in range(1, 5):
            self.click_xy(
                "team_member_{}".format(index),
                "select story team member {}".format(index),
            )
            time.sleep(0.35)
        self.needs_team_selection = False

    def select_first_support_monster(self):
        self.click_xy("support_tab", "open support monster list")
        time.sleep(0.7)
        support_obs = observe()
        if self._support_popup_visible(support_obs):
            self._update_support_monster_count(support_obs)
        self.click_xy("support_first", "select first support monster")
        time.sleep(0.5)
        self.click_xy("support_confirm", "confirm support monster")
        self.needs_support_selection = False
        time.sleep(0.8)
