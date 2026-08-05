"""Idle chat friend-request fallback flow."""

import time

from .. import config
from ..vision.core import begin_visual_frame, observe, scale_point
from ..vision.friend import find_chat_open


class FriendFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def _handle_friend_limit_popup(self, obs):
        # The failure text names the selected player, for example:
        # "因玩家Falco-502的好友数已达上限，无法继续添加好友。"
        # It does not contain the older "邀请好友" anchor, and ML Kit may
        # split the sentence across two rows, so match the stable fragments.
        selected_player_is_full = (
            obs.contains("好友数已达上限")
            or obs.contains_all("好友数", "上限")
            or obs.contains_all("添加好友", "上限")
        )
        own_invitation_limit = obs.contains_all("邀请好友", "上限")
        friend_limit_reached = selected_player_is_full or own_invitation_limit
        if not friend_limit_reached:
            return False
        confirms = obs.matching(
            # The verified screen was recognized as "确趴". Restrict this
            # fuzzy match to the already-confirmed friend-limit modal.
            lambda row: row["text"].startswith("确")
        )
        if len(confirms) == 1:
            self.actions.click_row(confirms[0], "confirm friend invitation limit")
        else:
            self.actions.click_xy(
                "friend_request_confirm",
                "confirm friend invitation limit",
            )
        if own_invitation_limit and not selected_player_is_full:
            self.state.friend.requests_disabled = True
            print("[friend] own invitation limit reached; disable friend fallback")
        else:
            print("[friend] selected player's friend list is full; try another player later")
        return True

    def _handle_friend_request_success_popup(self, obs):
        # Verified result variants include "申请好友完毕" (often OCR'd as
        # "申靖好友完毕") and "已发送过好友申请消息". Match stable semantic
        # fragments within one OCR row so the underlying profile's separate
        # "好友申请" button cannot be mistaken for the result modal.
        success_rows = obs.matching(
            lambda row: (
                "好友" in row["text"]
                and (
                    "完毕" in row["text"]
                    or (
                        "申请" in row["text"]
                        and (
                            "已发送" in row["text"]
                            or "发送过" in row["text"]
                        )
                    )
                )
            )
        )
        if not success_rows:
            return False
        confirms = obs.matching(
            lambda row: row["text"].startswith("确")
        )
        if len(confirms) == 1:
            self.actions.click_row(confirms[0], "confirm successful friend request")
        else:
            self.actions.click_xy(
                "friend_request_confirm",
                "confirm successful friend request",
            )
        print("[friend] successful friend-request popup confirmed")
        return True

    def _handle_chat_blocking_popup(self, obs):
        if obs.contains("网络连接延迟") or obs.contains("M:234"):
            confirms = obs.matching(
                lambda row: row["text"].startswith("确")
            )
            if len(confirms) == 1:
                self.actions.click_row(confirms[0], "dismiss delayed network popup")
            else:
                self.actions.click_xy(
                    "friend_request_confirm",
                    "dismiss delayed network popup",
                )
            print("[friend] network delay interrupted player-profile opening")
            return True

        if (
            obs.contains("重新发送战斗结果")
            and obs.contains("视为战败")
        ):
            yes_rows = obs.exact("是")
            if len(yes_rows) == 1:
                self.actions.click_row(
                    yes_rows[0],
                    "confirm battle-result resend",
                )
            else:
                self.actions.click_xy(
                    "battle_result_resend_yes",
                    "confirm battle-result resend",
                )
            print("[friend] battle-result resend confirmed")
            return True

        if obs.contains("无法找到战斗信息"):
            confirms = obs.matching(
                lambda row: row["text"].startswith("确")
            )
            if len(confirms) == 1:
                self.actions.click_row(
                    confirms[0],
                    "dismiss unavailable battle-result popup",
                )
            else:
                self.actions.click_xy(
                    "friend_request_confirm",
                    "dismiss unavailable battle-result popup",
                )
            print("[friend] unavailable battle-result popup dismissed")
            return True
        return False

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

    def _transition_popup_visible(self, obs):
        return (
            obs.contains("网络连接延迟")
            or obs.contains("M:234")
            or obs.contains("重新发送战斗结果")
            or obs.contains("无法找到战斗信息")
            or obs.contains("好友数已达上限")
            or obs.contains_all("好友数", "上限")
            or obs.contains_all("邀请好友", "上限")
        )

    def _request_result_visible(self, obs):
        success = obs.matching(
            lambda row: (
                "好友" in row["text"]
                and (
                    "完毕" in row["text"]
                    or "已发送" in row["text"]
                    or "发送过" in row["text"]
                )
            )
        )
        return bool(success) or self._transition_popup_visible(obs) or (
            obs.contains_all("好友", "申请", "成功")
            or obs.contains_all("好友", "申请", "发送")
        )

    def _wait_observation(self, predicate):
        """Poll until a target screen appears, bounded by a short timeout."""
        deadline = time.time() + config.FRIEND_UI_TIMEOUT_SECONDS
        current = observe()
        while not predicate(current) and time.time() < deadline:
            time.sleep(config.FRIEND_UI_POLL_SECONDS)
            current = observe()
        return current

    def _close_chat_monster_modal(self, obs):
        if not obs.contains_all("最大等级", "入场邀请"):
            return False
        confirms = obs.matching(
            lambda row: row["text"].startswith("确")
        )
        if len(confirms) == 1:
            self.actions.click_row(
                confirms[0],
                "close monster detail opened from chat",
            )
        else:
            # The game canvas exposes no accessibility nodes. This fallback
            # point was verified on the 1080x720 self-drawn modal.
            self.actions.click_point(
                (631, 528),
                "close monster detail opened from chat",
            )
        return True

    def handle_stray_chat_layers(self, obs):
        if self._handle_friend_limit_popup(obs):
            return True
        if self._handle_friend_request_success_popup(obs):
            return True
        if self._handle_chat_blocking_popup(obs):
            return True
        if self._close_chat_monster_modal(obs):
            return True
        if self._player_profile_visible(obs):
            self.actions.click_xy("player_profile_close", "close stray profile overlay")
            return True
        if self._chat_overlay_visible(obs):
            self.actions.click_xy("chat_close", "close stray chat overlay")
            return True
        return False

    def _close_chat_layers(self, profile_open=False):
        if profile_open:
            current = observe()
            if self._handle_friend_request_success_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                current = observe()
            if self._handle_chat_blocking_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                current = observe()
            if self._close_chat_monster_modal(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
            elif self._player_profile_visible(current):
                self.actions.click_xy(
                    "player_profile_close",
                    "close player profile after friend request",
                )
                time.sleep(config.FRIEND_PROFILE_CLOSE_SECONDS)

        for attempt in range(1, 4):
            current = observe()
            if self._handle_friend_request_success_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._handle_chat_blocking_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._close_chat_monster_modal(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if not self._chat_overlay_visible(current):
                print("[friend] chat overlay closed")
                return True

            if self._player_profile_visible(current):
                self.actions.click_xy(
                    "player_profile_close",
                    "retry closing player profile",
                )
            else:
                self.actions.click_xy(
                    "chat_close",
                    "close chat after friend request: attempt {}".format(
                        attempt
                    ),
                )
            time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)

        print("[friend] chat overlay still visible after close retries")
        return False

    def _chat_player_candidates(self, obs):
        candidates = []
        max_name_left = scale_point((220, 0))[0]
        min_chat_y = scale_point((0, 130))[1]
        max_chat_y = scale_point((0, 800))[1]
        for row in obs.rows:
            text = row["text"]
            open_index = text.find("[")
            close_index = text.find("]", open_index + 1)
            # A real chat sender starts at the far-left name column. Ignore
            # brackets later in message bodies and badly merged OCR rows.
            if open_index < 0 or open_index > 2 or close_index <= open_index + 1:
                continue
            raw = row.get("raw")
            if isinstance(raw, dict):
                rect = raw.get("rect")
            else:
                rect = getattr(raw, "rect", None)
            if rect is None or len(rect) != 4:
                # Without a row rectangle there is no safe way to distinguish
                # the sender name from adjacent chat action icons.
                continue
            left, top, _right, bottom = [int(value) for value in rect]
            if left > max_name_left:
                continue
            if bottom < min_chat_y or top > max_chat_y:
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
        raw = row.get("raw")
        if isinstance(raw, dict):
            rect = raw.get("rect")
        else:
            rect = getattr(raw, "rect", None)

        if rect is not None and len(rect) == 4:
            left, top, _right, bottom = [int(value) for value in rect]
            # The sender name always occupies the far-left column, while its
            # speaker/battle-result icon starts immediately to the right.
            # OCR often merges the whole message into one very wide rect, so
            # proportional character-width estimation can drift onto that
            # icon. Use a small verified inset from the row's left edge and
            # cap it inside the sender-name column instead.
            safe_inset_x = scale_point((36, 0))[0]
            name_column_right = scale_point((150, 0))[0]
            return (
                max(left + 4, min(left + safe_inset_x, name_column_right)),
                int((top + bottom) / 2.0),
            )

        # Candidates without a rect are normally rejected. Keep this fallback
        # in the same safe left-side name column; never use the row centre,
        # which may land on a battle-result or speaker icon.
        return scale_point((105, 0))[0], row["y"]

    def _chat_player_name(self, row):
        """Return the bracketed sender name used to avoid duplicate requests."""
        text = row["text"]
        open_index = text.find("[")
        close_index = text.find("]", open_index + 1)
        if open_index < 0 or close_index <= open_index + 1:
            return ""
        return text[open_index + 1:close_index].strip()

    def _return_to_open_chat(self):
        """Close result/profile layers while keeping the chat overlay open."""
        for _attempt in range(4):
            current = observe()
            if self._handle_friend_request_success_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._handle_friend_limit_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._handle_chat_blocking_popup(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._close_chat_monster_modal(current):
                time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
                continue
            if self._player_profile_visible(current):
                self.actions.click_xy(
                    "player_profile_close",
                    "close player profile and keep chat open",
                )
                time.sleep(config.FRIEND_PROFILE_CLOSE_SECONDS)
                continue
            if self._chat_overlay_visible(current):
                return True
            return False
        return False

    def _request_one_chat_player(self, chat_obs, attempted_names, request_number):
        """Initiate one request while reusing the already-open chat overlay."""

        candidates = self._chat_player_candidates(chat_obs)
        if not candidates:
            print("[friend] no player candidate in chat")
            return False, False

        player = None
        player_name = ""
        start_index = self.state.friend.candidate_cursor % len(candidates)
        for offset in range(len(candidates)):
            index = (start_index + offset) % len(candidates)
            candidate = candidates[index]
            candidate_name = self._chat_player_name(candidate)
            if not candidate_name or candidate_name in attempted_names:
                continue
            player = candidate
            player_name = candidate_name
            self.state.friend.candidate_cursor = index + 1
            break

        if player is None:
            print("[friend] fewer than {} distinct chat players available".format(
                config.FRIEND_REQUESTS_PER_ROUND
            ))
            return False, False

        # Mark the player before opening the profile so a broken profile cannot
        # cause the same nickname to be retried repeatedly in this round.
        attempted_names.add(player_name)
        self.actions.click_point(
            self._chat_player_click_point(player),
            "open chat player profile {}/{}: {}".format(
                request_number,
                config.FRIEND_REQUESTS_PER_ROUND,
                player_name,
            ),
        )
        profile_obs = self._wait_observation(
            lambda current: (
                self._player_profile_visible(current)
                or self._transition_popup_visible(current)
            )
        )
        if self._handle_chat_blocking_popup(profile_obs):
            time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
            return False, self._return_to_open_chat()
        if not self._player_profile_visible(profile_obs):
            print("[friend] player profile did not open: {}".format(player_name))
            return False, self._return_to_open_chat()

        friend_buttons = profile_obs.matching(
            lambda row: (
                "好友申请" in row["text"]
                or ("好友" in row["text"] and "申请" in row["text"])
            )
        )
        if len(friend_buttons) == 1:
            self.actions.click_row(
                friend_buttons[0],
                "send friend request to {}".format(player_name),
            )
        else:
            print("[friend] friend request text missed; use calibrated profile button")
            self.actions.click_xy(
                "friend_request",
                "send friend request to {}".format(player_name),
            )
        request_result = self._wait_observation(self._request_result_visible)
        if self._handle_friend_request_success_popup(request_result):
            pass
        elif self._handle_chat_blocking_popup(request_result):
            time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)
        elif self._handle_friend_limit_popup(request_result):
            pass
        elif (
            request_result.contains("申请好友完毕")
            or request_result.contains_all("好友", "申请", "成功")
            or request_result.contains_all("好友", "申请", "发送")
        ):
            self.actions.click_xy("friend_request_confirm", "confirm friend request result")
        else:
            print("[friend] friend request result not confirmed for {}".format(player_name))
        time.sleep(config.FRIEND_ACTION_SETTLE_SECONDS)

        returned_to_chat = self._return_to_open_chat()
        print("[friend] initiated friend request to {}".format(player_name))
        return True, returned_to_chat

    def try_request_friend_for_sparse_support(self, obs=None):
        if not self.state.friend.should_request_for_support(self.state.battle):
            return False

        # Sparse support is measured on the battle-preparation page. The old
        # guard looked for settings/speed/pause controls from an active battle,
        # so it could never pass here. Use the same unique right-side Start
        # Battle evidence accepted by BattleFlow; requiring every surrounding
        # label would make one harmless OCR miss skip the friend request.
        start_battles = [] if obs is None else obs.matching(
            lambda row: (
                ("开始战斗" in row["text"] or "开始战" in row["text"])
                and row["x"] >= scale_point((1100, 0))[0]
            )
        )
        if len(start_battles) != 1:
            return False

        # One attempt per measured battle-preparation screen, regardless of
        # whether chat/profile OCR succeeds. This prevents repeated chat opens
        # on every engine tick while the support count remains sparse.
        self.state.friend.attempted_for_preparation = True
        self.state.friend.last_request_at = time.time()
        print(
            "[friend] support count {} < 6; request {} friends".format(
                self.state.battle.support_monster_count,
                config.FRIEND_REQUESTS_PER_ROUND,
            )
        )
        begin_visual_frame()
        chat_point = find_chat_open()
        if chat_point is None:
            print("[friend] movable chat bubble not found")
            return True
        self.actions.click_point(
            chat_point,
            "open movable chat bubble for {} friend requests".format(
                config.FRIEND_REQUESTS_PER_ROUND
            ),
        )
        chat_obs = self._wait_observation(self._chat_overlay_visible)
        if not self._chat_overlay_visible(chat_obs):
            self.actions.click_xy("chat_close", "close chat after missing chat overlay")
            return True

        attempted_names = set()
        initiated_count = 0
        max_attempts = config.FRIEND_REQUESTS_PER_ROUND * 2
        for _attempt in range(max_attempts):
            if initiated_count >= config.FRIEND_REQUESTS_PER_ROUND:
                break
            chat_obs = observe()
            if not self._chat_overlay_visible(chat_obs):
                break
            initiated, can_continue = self._request_one_chat_player(
                chat_obs,
                attempted_names,
                initiated_count + 1,
            )
            if initiated:
                initiated_count += 1
            if self.state.friend.requests_disabled or not can_continue:
                break

        # Close the chat only once, after all three profile/request cycles.
        self._close_chat_layers(profile_open=True)

        print("[friend] friend request round finished: {}/{} players".format(
            initiated_count,
            config.FRIEND_REQUESTS_PER_ROUND,
        ))
        # This handler may have opened and closed several UI layers. Own the
        # tick even when fewer than three candidates succeeded, so BattleFlow
        # cannot act on the stale preparation observation afterward.
        return True

    def try_request_friend_from_chat(self):
        """Compatibility alias for older callers."""
        return self.try_request_friend_for_sparse_support()
