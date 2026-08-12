"""Idle chat friend-request fallback flow."""

import time

from . import config
from .vision import find_chat_open, observe


class FriendFlowMixin(object):
    def _handle_friend_limit_popup(self, obs):
        if not obs.contains_all("邀请好友", "上限"):
            return False
        confirms = obs.matching(
            lambda row: row["text"].startswith("确认")
        )
        if len(confirms) == 1:
            self.click_row(confirms[0], "confirm friend invitation limit")
        else:
            self.click_xy(
                "friend_request_confirm",
                "confirm friend invitation limit",
            )
        self.friend_requests_disabled = True
        print("[friend] invitation limit reached; disable friend fallback")
        return True

    def _chat_overlay_visible(self, obs):
        return (
            obs.contains("频道")
            or obs.contains_all("普通", "私聊")
        )

    def _player_profile_visible(self, obs):
        anchors = ("战斗支援", "好友申请", "屏蔽/举报", "访问")
        return (
            sum(1 for text in anchors if obs.contains(text)) >= 2
            or obs.contains("公会信息")
            or obs.contains("申请公会")
        )

    def _close_chat_monster_modal(self, obs):
        if not obs.contains_all("最大等级", "入场邀请"):
            return False
        confirms = obs.matching(
            lambda row: row["text"].startswith("确")
        )
        if len(confirms) == 1:
            self.click_row(
                confirms[0],
                "close monster detail opened from chat",
            )
        else:
            # The game canvas exposes no accessibility nodes. This fallback
            # point was verified on the 1080x720 self-drawn modal.
            self.click_point(
                (631, 528),
                "close monster detail opened from chat",
            )
        return True

    def handle_stray_chat_layers(self, obs):
        if self._handle_friend_limit_popup(obs):
            return True
        if self._close_chat_monster_modal(obs):
            return True
        if self._player_profile_visible(obs):
            self.click_xy("player_profile_close", "close stray profile overlay")
            return True
        if self._chat_overlay_visible(obs):
            self.click_xy("chat_close", "close stray chat overlay")
            return True
        return False

    def _close_chat_layers(self, profile_open=False):
        if profile_open:
            current = observe()
            if not self._close_chat_monster_modal(current):
                self.click_xy(
                    "player_profile_close",
                    "close player profile after friend request",
                )
            time.sleep(1.5)

        for attempt in range(1, 4):
            current = observe()
            if self._close_chat_monster_modal(current):
                time.sleep(1.0)
                continue
            if not self._chat_overlay_visible(current):
                print("[friend] chat overlay closed")
                return True

            if self._player_profile_visible(current):
                self.click_xy(
                    "player_profile_close",
                    "retry closing player profile",
                )
            else:
                self.click_xy(
                    "chat_close",
                    "close chat after friend request: attempt {}".format(
                        attempt
                    ),
                )
            time.sleep(1.0)

        print("[friend] chat overlay still visible after close retries")
        return False

    def _chat_player_candidates(self, obs):
        candidates = []
        for row in obs.rows:
            text = row["text"]
            if "[" not in text or "]" not in text:
                continue
            if "通知" in text:
                continue
            if (
                "开启了" in text
                or "秘密地下城" in text
                or "召唤出" in text
            ):
                continue
            candidates.append(row)
        return candidates

    def _chat_player_click_point(self, row):
        text = row["text"]
        open_index = text.find("[")
        close_index = text.find("]", open_index + 1)
        raw = row.get("raw")
        if isinstance(raw, dict):
            rect = raw.get("rect")
        else:
            rect = getattr(raw, "rect", None)

        if (
            open_index >= 0
            and close_index > open_index + 1
            and rect is not None
            and len(rect) == 4
        ):
            left, top, right, bottom = [int(value) for value in rect]
            text_width = max(1, right - left)
            char_width = text_width / float(max(len(text), 1))
            name_left = left + (open_index + 1) * char_width
            name_right = left + close_index * char_width
            # Click the middle of the player name enclosed by [ and ]. This
            # stays inside the bracketed area instead of drifting into the
            # following chat message.
            return (
                int((name_left + name_right) / 2.0),
                int((top + bottom) / 2.0),
            )

        # OCR normally provides rect. If it does not, the row center is the
        # only coordinate known to be inside the recognized text.
        return row["x"], row["y"]

    def try_request_friend_from_chat(self):
        if self.friend_requests_disabled:
            return False
        if self.support_monster_count > 6:
            return False

        # now = time.time()
        # if now - self.last_friend_request_at < config.FRIEND_REQUEST_IDLE_SECONDS:
        #     return False

        # self.last_friend_request_at = now
        print("[friend] idle fallback: open chat")
        chat_point = find_chat_open()
        if chat_point is None:
            print("[friend] movable chat bubble not found")
            return False
        self.click_point(chat_point, "open movable chat bubble for friend request")
        time.sleep(1.0)

        chat_obs = observe()
        if not chat_obs.contains("频道") and not chat_obs.contains_all("普通", "私聊"):
            self.click_xy("chat_close", "close chat after missing chat overlay")
            return False

        candidates = self._chat_player_candidates(chat_obs)
        if not candidates:
            print("[friend] no player candidate in chat")
            self._close_chat_layers()
            return False

        player = candidates[0]
        self.click_point(
            self._chat_player_click_point(player),
            "open chat player profile",
        )
        time.sleep(3.0)

        profile_obs = observe()
        friend_buttons = profile_obs.matching(
            lambda row: (
                "好友申请" in row["text"]
                or ("好友" in row["text"] and "申请" in row["text"])
            )
        )
        if len(friend_buttons) == 1:
            self.click_row(friend_buttons[0], "send friend request")
        else:
            # The profile was opened through the verified bracketed player
            # name. ML Kit intermittently misses the self-drawn button text;
            # the button point was calibrated on this 1080x720 profile layout.
            print(
                "[friend] friend request text missed; use calibrated profile button"
            )
            self.click_xy("friend_request", "send friend request")
        time.sleep(3.0)

        request_result = observe()
        if not self._handle_friend_limit_popup(request_result):
            self.click_xy("friend_request_confirm", "confirm friend request result")
        time.sleep(1.0)

        closed = self._close_chat_layers(profile_open=True)
        if not closed:
            return False
        print("[friend] friend request flow finished")
        return True
