"""Startup, login, and server-selection flow."""

import time

from ..vision.core import observe
from ..vision.startup import find_guest_login


class StartupFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def handle(self, obs):
        if obs.contains("游戏使用条款") or obs.contains("使用条款"):
            self.actions.click_xy("terms_select_all", "select all game terms")
            time.sleep(0.6)
            self.actions.click_xy("terms_agree_start", "agree to game terms and start")
            return True

        if obs.contains("选择服务器") or obs.contains("选择服务") or obs.contains("Global"):
            global_rows = obs.exact("Global")
            if len(global_rows) == 1:
                self.actions.click_row(global_rows[0], "select Global server from OCR")
            else:
                self.actions.click_xy("server_global", "select Global server")
            time.sleep(0.5)

            # Re-observe after selecting the server so the decisive click uses
            # the current 1080 x 720 layout instead of a reference coordinate.
            current = observe()
            confirms = current.matching(
                lambda row: row["text"] in ("确认", "确队")
            )
            if len(confirms) == 1:
                self.actions.click_row(confirms[0], "confirm Global server from OCR")
            else:
                self.actions.click_xy("server_confirm", "confirm Global server")
            return True

        guests = find_guest_login(obs)
        if obs.contains_all("Google登录", "Hive登录") and len(guests) == 1:
            self.actions.click_row(guests[0], "guest login")
            return True

        yes = obs.exact("是")
        if obs.contains("Hive登录游戏") and len(yes) == 1:
            self.actions.click_row(yes[0], "confirm guest warning")
            return True

        if (obs.contains("数据资源") or obs.contains("MB")) and len(yes) == 1:
            self.actions.click_row(yes[0], "confirm resource download")
            return True

        starts = [row for row in obs.rows if "点击开始" in row["text"]]
        if len(starts) == 1:
            self.actions.click_row(starts[0], "start game")
            return True

        skips = obs.exact("省略")
        if len(skips) == 1:
            self.actions.click_row(skips[0], "skip opening cutscene")
            return True

        skips = obs.exact("SKIP")
        if len(skips) == 1:
            self.actions.click_row(skips[0], "skip opening cutscene")
            return True

        return False
