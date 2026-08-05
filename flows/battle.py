"""Battle preparation, result, support, and runtime flow."""

import time

from .. import config
from ..core.overlay_recognizer import (
    leader_skill_warning_visible,
    used_support_warning_text_visible,
)
from ..vision.battle_runtime import auto_battle_is_off, find_battle_target
from ..vision.core import begin_visual_frame, observe, scale_point
from ..vision.stage import (
    battle_start_is_disabled,
    find_highest_star_team_members,
    find_selected_team_members,
    find_stage_battle_button_with_locked_next,
)
from ..vision.support import find_support_monsters


class BattleFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def select_first_support_monster(self):
        self.actions.click_xy("support_tab", "open support monster list")
        time.sleep(0.7)
        # The click changes the screen inside the current engine tick. Discard
        # the battle-preparation screenshot so support detection cannot reuse
        # it while OCR is already observing the newly opened popup.
        begin_visual_frame()
        support_obs = observe()
        if not self.support_popup_visible(support_obs):
            print("[support] forced support list did not open; retry next tick")
            return False
        self._handle_counted_support_list(support_obs)
        return True

    def support_popup_visible(self, obs):
        return (
            obs.contains("好友魔灵")
        )

    def _used_support_warning_visible(self, obs):
        if used_support_warning_text_visible(obs):
            return True
        upper_confirms = obs.matching(
            lambda row: row["text"].startswith("确")
            and scale_point((0, 400))[1]
            <= row["y"]
            <= scale_point((0, 570))[1]
        )
        return self.support_popup_visible(obs) and bool(upper_confirms)

    def _leader_skill_warning_visible(self, obs):
        return leader_skill_warning_visible(obs)

    def _update_support_monster_count(self, obs):
        self.state.battle.support_monster_count = len(find_support_monsters(obs))
        self.state.battle.support_count_checked_for_preparation = True
        print("[support] visible selectable support monsters: {}".format(
            self.state.battle.support_monster_count
        ))
        return self.state.battle.support_monster_count

    def _handle_counted_support_list(self, obs):
        """Apply the shared normal/failed-battle support-count policy."""
        support_monster_count = self._update_support_monster_count(obs)
        failed_battle_requires_support = (
            self.state.battle.needs_support_selection
            and support_monster_count > 0
        )
        if support_monster_count >= 6 or failed_battle_requires_support:
            if failed_battle_requires_support and support_monster_count < 6:
                reason = "select first available support after failed battle"
            else:
                reason = "select first support monster from rich support list"
            self.actions.click_xy(
                "support_first",
                reason,
            )
            time.sleep(0.5)
            self.actions.click_xy("support_confirm", "confirm support monster")
        else:
            self.actions.press_back("close sparse support monster list")

        self.state.battle.needs_support_selection = False
        self.state.battle.checking_support_selection = False
        self.state.battle.support_checked = True
        return support_monster_count

    def handle_battle_preparation(self, obs):
        if self._leader_skill_warning_visible(obs):
            yes_rows = obs.exact("是")
            if len(yes_rows) == 1:
                self.actions.click_row(
                    yes_rows[0],
                    "continue battle without a usable leader skill",
                )
            else:
                # The game canvas exposes no accessibility button nodes.
                self.actions.click_xy(
                    "leader_skill_continue_yes",
                    "continue battle without a usable leader skill",
                )
            return True

        if self._used_support_warning_visible(obs):
            confirms = obs.matching(
                lambda row: row["text"].startswith("确")
            )
            if confirms:
                self.actions.click_row(
                    min(confirms, key=lambda row: row["y"]),
                    "close already-used support monster warning",
                )
            else:
                # The game canvas has no accessibility nodes. This fallback
                # was verified on the 1080x720 self-drawn warning dialog.
                self.actions.click_xy(
                    "used_support_warning_confirm",
                    "close already-used support monster warning",
                )
            self.state.battle.support_first_unavailable = True
            self.state.battle.needs_support_selection = False
            self.state.battle.checking_support_selection = False
            return True

        if self.state.battle.support_first_unavailable and self.support_popup_visible(obs):
            self.actions.press_back("close support list after first monster is unavailable")
            self.state.battle.support_first_unavailable = False
            self.state.battle.support_checked = True
            return True

        selected_team = find_selected_team_members(obs)
        preparing_support = (
            self.state.battle.needs_support_selection
            or self.state.battle.checking_support_selection
            or not self.state.battle.support_checked
        )
        if preparing_support and len(selected_team) == 4:
            # A support monster occupies the fourth formation slot. Remove the
            # current rightmost member before opening the support list; clicking
            # a support while all four slots are occupied otherwise has no
            # effect. This applies equally to normal and failed-battle retries.
            fourth_member = max(selected_team, key=lambda point: point[0])
            self.actions.click_point(
                fourth_member,
                "remove fourth team monster before support selection",
            )
            self.state.battle.support_checked = False
            self.state.battle.support_count_checked_for_preparation = False
            self.state.friend.attempted_for_preparation = False
            time.sleep(0.4)
            return True

        stage_list_visible = (
            obs.contains("掉落信息")
            and (obs.contains("难度") or obs.contains("普通"))
        )
        if not stage_list_visible:
            self.state.battle.stage_list_scroll_count = 0

        stage_battle = find_stage_battle_button_with_locked_next(
            obs,
            allow_last=(
                self.state.battle.stage_list_scroll_count
                >= config.STAGE_LIST_MAX_SWIPES
            ),
        )
        if stage_battle is not None:
            self.state.battle.stage_list_scroll_count = 0
            self.state.battle.needs_support_selection = False
            self.state.battle.checking_support_selection = False
            self.state.battle.support_checked = False
            self.state.battle.support_first_unavailable = False
            self.state.battle.support_count_checked_for_preparation = False
            self.state.friend.attempted_for_preparation = False
            self.actions.click_point(
                stage_battle,
                "enter detected in-progress story stage",
            )
            return True

        if (
            stage_list_visible
            and self.state.battle.stage_list_scroll_count < config.STAGE_LIST_MAX_SWIPES
        ):
            self.state.battle.stage_list_scroll_count += 1
            self.actions.swipe_xy(
                "stage_list_scroll_start",
                "stage_list_scroll_end",
                "scroll down story stage list to find in-progress stage ({}/{})".format(
                    self.state.battle.stage_list_scroll_count,
                    config.STAGE_LIST_MAX_SWIPES,
                ),
                dur=500,
            )
            return True

        start_battle_disabled = battle_start_is_disabled(obs)
        if start_battle_disabled:
            team_members = find_highest_star_team_members(obs, 3)
            if team_members:
                for member in team_members:
                    self.actions.click_point(
                        member["point"],
                        "select {}-star story team member".format(member["stars"]),
                    )
                    time.sleep(0.35)
            else:
                print(
                    "[battle] Start Battle disabled but no ranked monster cards found"
                )
            return True

        if self.state.battle.needs_support_selection and self.support_popup_visible(obs):
            self._handle_counted_support_list(obs)
            return True

        if self.state.battle.checking_support_selection and self.support_popup_visible(obs):
            self._handle_counted_support_list(obs)
            return True

        if self.state.battle.needs_support_selection and obs.contains_all("好友", "魔灵", "支援"):
            self.select_first_support_monster()
            return True

        if self.state.battle.needs_support_selection and obs.contains_all("领队", "开始战斗", "结束战斗"):
            self.select_first_support_monster()
            return True

        start_battles = obs.matching(
            lambda row: (
                "开始战斗" in row["text"] or "开始战" in row["text"]
            )
            and row["x"] >= scale_point((1100, 0))[0]
        )
        if self.state.battle.needs_support_selection and len(start_battles) == 1:
            self.select_first_support_monster()
            return True

        if (
            not self.state.battle.needs_support_selection
            and not self.state.battle.checking_support_selection
            and not self.state.battle.support_checked
            and len(start_battles) == 1
        ):
            filter_maps = [
                "拉古恩雪山",
                "拉古息雪",
                "粒古息雪",
                "拉古恩雪",
                "拉古思",
                "物古思",
                "新E雪",
                "拉古雪",
                "物恩雪山",
                "新思雪山",
                "特拉恩丛林",
                "特拉恩从林",
                "特拉恩队林",
                "特拉恩N林",
                "特拉思丛林",
                "特拉恩A林",
                "夏依德尼遗址",
                "厦依德尼遗址",
                "复依德尼遗址",
                "區依德遗址",
                "區依德尼遗址",
                "回依德尼遗址",
                "阿依德尼遗址",
                "菜出遗址",
                "塔摩勒沙漠",
                "塔摩勂沙漠",
                "塔摩勒沙膜",
                "令塔摩勒沙漠",
                "保罗帕库斯遗址",
                "保罗帕贵址",
                "保罗帕時址",
                "保罗帕库遗址",
                "保罗帕址",
                "保罗帕库斯贵址",
                "保罗帕市责址",
                "保罗帕斯遗址",
                "保罗帕市遗址",
                "保罗帕遗址",
                "帕伊摩恩",
                "帕伊劇恩火山",
                "伯伊摩恩火山",
                "帕伊度恩火山",
                "始伊摩恩火山",
                "帕伊摩图火山",
                "帕伊劇思火山",
                "始伊度恩火山",
            ]
            if any(obs.contains(map_name) for map_name in filter_maps):
                self.state.battle.checking_support_selection = True
                self.state.battle.support_first_unavailable = False
                self.actions.click_xy("support_tab", "open support list to count selectable monsters")
            else:
                print("[observe] no support_tab: {}".format(obs.compact_text()))
                self.state.battle.support_checked = True
            return True

        if (
            len(start_battles) == 1
            and self.state.battle.support_checked
            and not battle_start_is_disabled(obs)
        ):
            self.state.battle.needs_support_selection = False
            self.state.battle.checking_support_selection = False
            self.state.battle.support_count_checked_for_preparation = False
            self.state.friend.attempted_for_preparation = False
            self.actions.click_row(start_battles[0], "start next-stage battle")
            return True
        if self.support_popup_visible(obs):
            self._handle_counted_support_list(obs)
            return True

        return False

    def handle_battle_result(self, obs):
        if obs.contains_all("胜利", "等级提升"):
            self.actions.click_xy("victory_continue", "continue victory result")
            return True

        if obs.contains_all("首次达成", "获得"):
            self.actions.click_xy("victory_continue", "continue first max-level reward")
            return True

        if (obs.contains("胜利") or obs.contains("失败")) and obs.contains("奖励"):
            self.actions.click_xy("victory_continue", "continue battle result rewards")
            return True

        retry_battles = obs.matching(
            lambda row: "战斗准备" in row["text"]
        )
        if obs.contains("失败") and obs.contains("停止") and len(retry_battles) > 0:
            self.state.battle.needs_support_selection = True
            self.state.battle.checking_support_selection = False
            self.state.battle.support_checked = False
            self.state.battle.support_count_checked_for_preparation = False
            self.state.friend.attempted_for_preparation = False
            rect = retry_battles[0]['raw'].rect
            self.actions.click_point([rect[0], rect[1]], "retry failed story battle")
            return True

        if obs.contains_all("通关奖励", "奖励可在收件箱中领取"):
            self.actions.click_xy("victory_continue", "continue area-clear reward")
            return True

        next_stages = obs.matching(
            lambda row: "下个关卡" in row["text"]
        )
        if obs.contains("胜利") and len(next_stages) == 1:
            self.state.battle.needs_support_selection = False
            self.state.battle.checking_support_selection = False
            self.state.battle.support_checked = False
            self.state.battle.support_first_unavailable = False
            self.state.battle.support_count_checked_for_preparation = False
            self.state.friend.attempted_for_preparation = False
            self.actions.click_row(next_stages[0], "enter next stage")
            return True

        return False

    def handle_battle_runtime(self, obs):
        f = [
            "犬神",
            "回大神",
        ]
        if any(obs.contains(name) for name in f):
            return False
        battle_target = find_battle_target()
        if battle_target is not None:
            point = battle_target["point"]
            self.actions.click_point(
                point,
                "select {} battle target".format(battle_target["color"]),
            )
            return True

        if auto_battle_is_off():
            self.actions.click_xy("auto_battle", "enable auto battle")
            return True
        return False
