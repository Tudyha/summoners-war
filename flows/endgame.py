"""Mailbox, light/dark summon, and reroll-reset flow after volcano clear."""

import time
import re

from .. import config
from ..core.run_state import EndgamePhase
from ..core.scene_recognizer import (
    home_visible,
    message_center_match,
    summon_ui_match,
)
from ..integrations.feishu import send_summon_result
from ..vision.core import scale_point
from ..vision.map import find_home_magic_circle_candidates
from ..vision.summon import find_light_dark_scroll_icon
from ..vision.tutorial import dialogue_present


class EndgameFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def _lower_confirm_rows(self, obs):
        return obs.matching(
            lambda row: row["text"].startswith("确认")
            and row["y"] >= scale_point((0, 500))[1]
        )

    def _claim_rows(self, obs):
        return obs.matching(
            lambda row: ("领取" in row["text"] or "收取" in row["text"])
            and row["x"] >= scale_point((900, 0))[0]
        )

    def _summon_result_is_five_star(self, obs):
        if obs.contains("5星") or obs.contains("五星"):
            return True
        return any("★★★★★" in text or "★5" in text for text in obs.texts)

    def _summon_result_visible(self, obs):
        return (
            obs.contains("最大等级")
            or obs.contains("类型")
            or obs.contains("攻击速度")
            or obs.contains("召唤成功")
            or obs.contains("获得")
        )

    def _summon_ui_visible(self, obs):
        return summon_ui_match(obs) is not None

    def _reset_code(self, obs):
        for text in obs.texts:
            matches = re.findall(r"\b\d{6}\b", text)
            if matches:
                return matches[0]
        return None

    def enter(self, reason):
        self.state.endgame.phase = EndgamePhase.SUMMON
        self.state.endgame.inbox_claimed = False
        self.state.endgame.light_dark_selected = False
        self._reset_summon_search()
        print("[endgame] {}; switch to mailbox/summon flow".format(reason))

    def _reset_summon_search(self):
        self.state.endgame.summon_started = False
        self.state.endgame.entering_summon_circle = False
        self.state.endgame.summon_search_step = 0
        self.state.endgame.summon_rejected_points = []
        self.state.endgame.summon_probe_point = None

    def _summon_search_swipes(self):
        # These are 1600x900 reference coordinates. Use short drags so a
        # visible Summonhenge is not swept past between observations.
        # Drag the island up-right to move the viewport toward its lower-left,
        # where the live castle-start test reached the Summonhenge fastest.
        toward_lower_left = ((500, 600), (800, 420))
        left = ((1050, 500), (700, 500))
        right = (left[1], left[0])
        up = ((800, 650), (800, 450))
        return (
            [toward_lower_left] * 3
            + [right] * 2
            + [left] * 3 + [up]
            + [right] * 3 + [up]
            + [left] * 3 + [up]
            + [right] * 3
        )

    def _pan_for_summon_circle(self):
        swipes = self._summon_search_swipes()
        index = self.state.endgame.summon_search_step % len(swipes)
        start, end = swipes[index]
        start_x, start_y = scale_point(start)
        end_x, end_y = scale_point(end)
        self.actions.swipe_points(
            (start_x, start_y),
            (end_x, end_y),
            "pan home map to find summon circle",
            600,
        )
        self.state.endgame.summon_search_step += 1
        self.state.endgame.summon_rejected_points = []
        self.state.runtime.last_action_at = time.time()
        print(
            "[endgame] pan home map to find summon circle: step {}".format(
                self.state.endgame.summon_search_step
            )
        )

    def _open_settings_tab(self, obs):
        options = obs.exact("选项")
        if len(options) == 1:
            self.actions.click_row(options[0], "open settings options tab")
        else:
            self.actions.click_xy("game_settings_options_tab", "open settings options tab")

    def _open_game_initialization(self, obs):
        initialization = obs.exact("游戏初始化")
        if len(initialization) == 1:
            self.actions.click_row(initialization[0], "open game initialization dialog")
        else:
            self.actions.click_xy("game_init_open", "open game initialization dialog")

    def handle(self, obs):
        if obs.contains("召唤书不足") and obs.contains("商店购买"):
            decline_rows = obs.exact("否")
            if len(decline_rows) == 1:
                self.actions.click_row(
                    decline_rows[0],
                    "decline purchasing an insufficient summon scroll",
                )
            else:
                self.actions.click_xy(
                    "summon_scroll_purchase_decline",
                    "decline purchasing an insufficient summon scroll",
                )
            return True

        # Endgame owns the router in blocking mode. Forced NPC dialogue can
        # still appear while entering the Summonhenge or immediately after an
        # account reset; advance it here so ownership does not starve the
        # lower-priority dialogue handler.
        if self.state.endgame.is_active and dialogue_present(obs):
            self.actions.click_xy("dialogue", "advance NPC dialogue during endgame")
            return True

        if self.state.endgame.phase in (
            EndgamePhase.RESET,
            EndgamePhase.RESET_CONFIRM,
        ):
            if message_center_match(obs) is not None:
                self.actions.click_xy(
                    "message_center_close",
                    "close message/activity center before reset",
                )
                return True

            if obs.contains("初始化游戏吗") and obs.contains("删除"):
                yes_rows = obs.exact("是")
                if len(yes_rows) == 1:
                    self.actions.click_row(yes_rows[0], "confirm final game initialization")
                else:
                    return False
                self.state.endgame.phase = EndgamePhase.INACTIVE
                self.state.endgame.inbox_claimed = False
                self.state.endgame.light_dark_selected = False
                self._reset_summon_search()
                self.state.nickname.reset()
                self.state.battle.needs_team_selection = False
                self.state.battle.needs_support_selection = False
                return True

            if obs.contains("输入下一个") and obs.contains("初始化"):
                if self.state.endgame.phase == EndgamePhase.RESET_CONFIRM:
                    if time.time() - self.state.runtime.last_action_at < 1.5:
                        return True
                    self.actions.click_xy(
                        "game_init_confirm",
                        "retry game initialization confirmation",
                    )
                    return True

                code = self._reset_code(obs)
                if code is None:
                    print("[reset] game initialization code not found")
                    return False
                self.actions.click_xy("game_init_code_input", "focus game initialization code input")
                time.sleep(0.6)
                self.actions.ime_clear()
                field_selector, field = self.actions.find_node_by_id(
                    config.NICKNAME_FIELD_ID
                )
                if field is not None:
                    self.actions.input_text(code, selector=field_selector)
                    time.sleep(0.5)
                    _, done = self.actions.find_node_by_id(
                        config.NICKNAME_DONE_ID
                    )
                    if done is None:
                        print("[reset] system Done button is missing")
                        return True
                    self.actions.click_node(done, "commit initialization code")
                else:
                    self.actions.input_text(code)
                    time.sleep(0.5)
                    self.actions.click_xy(
                        "game_init_keyboard_done",
                        "commit game initialization code",
                    )

                self.state.endgame.phase = EndgamePhase.RESET_CONFIRM
                for _ in range(6):
                    _, done = self.actions.find_node_by_id(
                        config.NICKNAME_DONE_ID
                    )
                    if done is None:
                        break
                    time.sleep(0.2)
                if done is not None:
                    print("[reset] waiting for system input bar to close")
                    return True
                time.sleep(0.3)
                self.actions.click_xy("game_init_confirm", "confirm game initialization")
                return True

            if obs.contains("游戏初始化") and obs.contains("语言设置"):
                self._open_game_initialization(obs)
                return True

            if obs.contains("游戏设置") and obs.contains("选项"):
                self._open_settings_tab(obs)
                return True

            if self._summon_ui_visible(obs):
                self.actions.click_xy("summon_close", "close summon UI before reset")
                return True

            if home_visible(obs):
                self.actions.click_xy("game_settings_open", "open in-game settings for reset")
                return True

            return False

        if not self.state.endgame.is_active:
            return False

        if self._summon_ui_visible(obs):
            self.state.endgame.entering_summon_circle = False
        elif self.state.endgame.entering_summon_circle:
            if time.time() - self.state.runtime.last_action_at < 5.0:
                return True
            self.state.endgame.entering_summon_circle = False
            print(
                "[endgame] summon UI entry timed out; allow one retry: {}".format(
                    obs.compact_text()
                )
            )

        # Recover from any lost probe state. This contextual menu uniquely
        # identifies the selected Summonhenge and must always take priority.
        summon_menu_rows = obs.matching(
            lambda row: row["text"] in ("召唤", "召喚")
        )
        if summon_menu_rows and (obs.contains("信息") or obs.contains("编辑")):
            self.actions.click_row(
                summon_menu_rows[0],
                "enter selected summon circle",
            )
            self.state.endgame.entering_summon_circle = True
            self.state.endgame.summon_probe_point = None
            self.state.endgame.light_dark_selected = False
            return True

        confirms = self._lower_confirm_rows(obs)
        if obs.contains("申请好友完毕") and len(confirms) == 1:
            self.actions.click_row(confirms[0], "confirm friend request popup")
            return True

        if obs.contains("可以领取以下"):
            collect_rows = obs.matching(
                lambda row: row["text"] in ("收取", "领取")
                and row["y"] >= scale_point((0, 600))[1]
            )
            if collect_rows:
                self.actions.click_row(
                    collect_rows[0],
                    "confirm claim-all inbox rewards",
                )
            else:
                self.actions.click_xy(
                    "inbox_claim_confirm",
                    "confirm claim-all inbox rewards",
                )
            self.state.endgame.inbox_claimed = True
            return True

        if (
            obs.contains("没有可一键领取")
            or obs.contains_all("没有", "一键领取", "内容")
        ):
            empty_confirms = obs.exact("确认")
            if len(empty_confirms) == 1:
                self.actions.click_row(
                    empty_confirms[0],
                    "confirm empty claim-all inbox popup",
                )
            else:
                self.actions.click_xy(
                    "inbox_empty_claim_confirm",
                    "confirm empty claim-all inbox popup",
                )
            self.state.endgame.inbox_claimed = True
            return True

        if obs.contains("礼物箱") and self.state.endgame.inbox_claimed:
            self.actions.click_xy("inbox_close", "close inbox after claiming rewards")
            return True

        if obs.contains("礼物箱") and not self.state.endgame.inbox_claimed:
            claim_all_rows = obs.matching(
                lambda row: "键领取" in row["text"]
                and row["x"] >= scale_point((1050, 0))[0]
            )
            if claim_all_rows:
                self.actions.click_row(
                    claim_all_rows[0],
                    "open claim-all inbox reward confirmation",
                )
            else:
                self.actions.click_xy(
                    "inbox_claim_all",
                    "open claim-all inbox reward confirmation",
                )
            return True

        if obs.contains("消息") and obs.contains("活动"):
            if self.state.endgame.summon_probe_point is not None:
                self.state.endgame.summon_rejected_points.append(
                    self.state.endgame.summon_probe_point
                )
                self.state.endgame.summon_probe_point = None
            self.actions.click_xy(
                "event_close",
                "close Activity screen opened during summon-circle search",
            )
            return True

        if self.state.endgame.summon_probe_point is not None:
            if (
                not self.state.endgame.summon_started
                and self._summon_result_visible(obs)
            ):
                self.state.endgame.summon_rejected_points.append(
                    self.state.endgame.summon_probe_point
                )
                self.state.endgame.summon_probe_point = None
                false_result_confirms = self._lower_confirm_rows(obs)
                if false_result_confirms:
                    self.actions.click_row(
                        false_result_confirms[0],
                        "close monster panel opened by summon-circle probe",
                    )
                else:
                    self.actions.click_xy(
                        "summon_result_confirm",
                        "close monster panel opened by summon-circle probe",
                    )
                return True
            if obs.contains("信息") or obs.contains("编辑"):
                self.state.endgame.summon_rejected_points.append(
                    self.state.endgame.summon_probe_point
                )
                self.state.endgame.summon_probe_point = None
                # Keep the contextual menu open. Clicking the next candidate
                # switches the selection directly; Android Back opens the
                # game's exit confirmation instead of dismissing this menu.
                return True
            if time.time() - self.state.runtime.last_action_at < 4.0:
                # OCR may need several seconds to expose the contextual menu.
                # Keep ownership of the screen while it is loading.
                return True
            self.state.endgame.summon_rejected_points.append(
                self.state.endgame.summon_probe_point
            )
            self.state.endgame.summon_probe_point = None
            print("[endgame] reject summon-circle probe after menu timeout")
            return True

        if home_visible(obs) and not self.state.endgame.inbox_claimed:
            inbox_rows = obs.matching(
                lambda row: "收件" in row["text"]
                and row["x"] <= scale_point((200, 0))[0]
                and scale_point((0, 350))[1]
                <= row["y"]
                <= scale_point((0, 580))[1]
            )
            if len(inbox_rows) == 1:
                self.actions.click_row(
                    inbox_rows[0],
                    "open inbox for light-dark scroll",
                )
            else:
                self.actions.click_xy("inbox", "open inbox for light-dark scroll")
            return True

        if home_visible(obs) and self.state.endgame.inbox_claimed:
            candidates = find_home_magic_circle_candidates(
                self.state.endgame.summon_rejected_points
            )
            if candidates:
                self.state.endgame.summon_probe_point = candidates[0]
                self.actions.click_point(
                    candidates[0],
                    "probe visible home magic circle",
                )
            else:
                self._pan_for_summon_circle()
            return True

        if self._summon_ui_visible(obs) and not self.state.endgame.light_dark_selected:
            light_dark_icon = find_light_dark_scroll_icon()
            if light_dark_icon is not None:
                self.actions.click_point(
                    light_dark_icon,
                    "select light-dark scroll by visual book icon",
                )
                self.state.endgame.light_dark_selected = True
            else:
                print(
                    "[endgame] light-dark scroll icon not found; "
                    "wait for visual retry without summoning"
                )
            return True

        if (
            obs.contains("新魔灵概率提升")
            and not obs.contains("特别召唤")
            and not obs.contains("特別召唤")
        ):
            self.actions.click_xy("new_monster_rate_checkbox", "enable new monster rate up")
            return True

        if self.state.endgame.light_dark_selected and self._summon_ui_visible(obs):
            if (
                time.time() - self.state.runtime.last_action_at
                < config.SUMMON_SELECTION_SETTLE_SECONDS
            ):
                return True
            special_summon_rows = obs.matching(
                lambda row: (
                    "特别召唤" in row["text"]
                    or "特別召唤" in row["text"]
                )
                and row["x"] <= scale_point((900, 0))[0]
                and row["y"] >= scale_point((0, 620))[1]
            )
            if special_summon_rows:
                self.actions.click_row(
                    special_summon_rows[0],
                    "summon light-dark scroll with rate up",
                )
            else:
                self.actions.click_xy(
                    "special_summon_button",
                    "summon light-dark scroll with rate up",
                )
            self.state.endgame.summon_started = True
            return True

        if self.state.endgame.summon_started and self._summon_result_visible(obs):
            is_five_star = self._summon_result_is_five_star(obs)
            notified, notification_detail = send_summon_result(is_five_star)
            if notified:
                print(
                    "[feishu] summon result notification sent: {}".format(
                        notification_detail
                    )
                )
            else:
                print(
                    "[feishu] summon result notification failed: {}".format(
                        notification_detail
                    )
                )
            if is_five_star:
                self.state.stop.for_five_star = True
                print("[result] five-star monster found; stopping reroll loop")
                return True
            print(
                "[result] non-five-star summon observation: {}".format(
                    obs.compact_text()
                )
            )
            confirms = self._lower_confirm_rows(obs)
            if len(confirms) >= 1:
                self.actions.click_row(confirms[0], "confirm non-five-star summon result")
            else:
                self.actions.click_xy(
                    "summon_result_confirm",
                    "confirm non-five-star summon result",
                )
            time.sleep(1.0)
            if config.AUTO_RESET_AFTER_NON_FIVE_STAR:
                self.state.endgame.phase = EndgamePhase.RESET
                print("[reset] non-five-star monster; use in-game initialization")
            else:
                self.state.stop.before_reset = True
                print("[result] non-five-star monster; stopped before unverified data reset")
            self.state.endgame.inbox_claimed = False
            self.state.endgame.light_dark_selected = False
            self._reset_summon_search()
            self.state.battle.needs_team_selection = False
            self.state.battle.needs_support_selection = False
            self.state.runtime.last_action_at = time.time()
            return True

        return False
