"""Frieren collaboration dice-minigame achievement farming flow."""

from .. import config
from ..core.collaboration_rules import (
    choose_skill_candidate,
    is_collaboration_internal_screen,
    is_gameplay_screen,
    is_shop_insufficient_funds,
    is_shop_purchase_confirmation,
    is_shop_upgrade_confirmation,
    parse_achievement_count,
    parse_fraction,
    parse_integer,
)
from ..core.run_state import CollaborationPhase, SummonScrollKind
from ..core.scene_recognizer import home_visible
from ..vision.collaboration import (
    find_minigame_entrance_icon,
    selected_skill_is_maxed,
)
from ..vision.core import scale_point


class CollaborationFlow(object):
    TARGET_ACHIEVEMENTS = 15
    MAX_REWARD_CLICKS = 18
    # Gameplay value first: row 2 col 6 increases dice used in battle; row 2
    # col 4 increases starting stamina. Remaining skills are fallback upgrades.
    SKILL_PRIORITY = (11, 9, 0, 1, 2, 3, 4, 5, 6, 7, 12, 14, 15, 8, 16, 17, 13, 10)
    # Axe/book/armour/bow first: they differ from the initial sword-heavy set.
    ITEM_PRIORITY = (3, 5, 6, 4, 0, 1, 2)

    def __init__(self, state, actions, enter_endgame):
        self.state = state
        self.actions = actions
        self.enter_endgame = enter_endgame

    def entrance_visible(self, obs=None):
        if find_minigame_entrance_icon() is None:
            return False
        if obs is None:
            return True
        # The icon detector is intentionally visual, but it must be situated on
        # the collaboration activity page. Similar dice/medallion artwork can
        # appear during the new-account tutorial after initialization.
        return (
            self._event_page_visible(obs)
            or obs.contains_all("联动通行证", "活动期间")
        )

    def screen_visible(self, obs):
        return (
            is_collaboration_internal_screen(obs.texts)
            or self._activity_guide_row(obs) is not None
        )

    def resume_if_internal(self, obs):
        state = self.state.collaboration
        if (
            state.allow_internal_resume
            and not state.started
            and self.screen_visible(obs)
        ):
            state.started = True
            print("[collaboration] resumed ownership from an internal minigame screen")

    def _click_reference(self, point, reason):
        self.actions.click_point(scale_point(point), reason)

    def _activity_guide_row(self, obs):
        """Return an unvoiced long-text guide bubble on the activity page."""
        if not obs.contains_all("联动通行证", "活动期间"):
            return None
        top = scale_point((0, 340))[1]
        bottom = scale_point((0, 665))[1]
        candidates = obs.matching(
            lambda row: (
                top <= row["y"] <= bottom
                and len("".join(row["text"].split())) >= 10
            )
        )
        return max(candidates, key=lambda row: len(row["text"])) if candidates else None

    @staticmethod
    def _rows_in_reference_box(obs, left, top, right, bottom):
        x1, y1 = scale_point((left, top))
        x2, y2 = scale_point((right, bottom))
        return [
            row for row in obs.rows
            if x1 <= row["x"] <= x2 and y1 <= row["y"] <= y2
        ]

    def _collection_visible(self, obs):
        return obs.contains("收集进度") or (
            obs.contains("成就") and parse_achievement_count(obs.texts) is not None
        )

    def _minigame_home_visible(self, obs):
        return (
            obs.contains("召唤骰子")
            or obs.contains_all("最高记录", "游戏准备")
        )

    def _event_page_visible(self, obs):
        return obs.contains("联动任务") or obs.contains("围剿委托")

    def _prepare_visible(self, obs):
        return (
            obs.contains("初始道具")
            or obs.contains("请选择要更换的道具")
            or obs.contains_all("游戏准备", "更换")
            or obs.contains_all("游戏准备", "开始")
        )

    def _skill_visible(self, obs):
        return obs.contains("技能升级") and obs.contains("初始化")

    def _gameplay_visible(self, obs):
        return is_gameplay_screen(obs.texts)

    def _result_visible(self, obs):
        return (
            obs.contains("胜利")
            or obs.contains("失败")
            or obs.contains("已击败")
            or obs.contains("挑战结束")
        )

    def _shop_visible(self, obs):
        return obs.contains("商店") and obs.contains("道具")

    def _visible_integer(self, obs, box):
        values = []
        for row in self._rows_in_reference_box(obs, *box):
            value = parse_integer(row["text"])
            if value is not None:
                values.append(value)
        return max(values) if values else None

    def _available_prepare_items(self, obs):
        available = set()
        scaled_counters = [
            scale_point(point) for point in config.COLLABORATION_PREPARE_ITEM_COUNTERS
        ]
        for row in obs.rows:
            fraction = parse_fraction(row["text"])
            if fraction is None or fraction[0] <= 0:
                continue
            distances = [
                (row["x"] - point[0]) ** 2 + (row["y"] - point[1]) ** 2
                for point in scaled_counters
            ]
            nearest = min(range(len(distances)), key=distances.__getitem__)
            tolerance = scale_point((52, 32))
            if (
                abs(row["x"] - scaled_counters[nearest][0]) <= tolerance[0]
                and abs(row["y"] - scaled_counters[nearest][1]) <= tolerance[1]
            ):
                available.add(nearest)
        return available

    def _handle_skill(self, obs):
        state = self.state.collaboration
        if state.skill_step == "select":
            skill_index = choose_skill_candidate(
                self.SKILL_PRIORITY,
                state.maxed_skill_indices,
            )
            if skill_index is not None:
                point, unused_base_cost = config.COLLABORATION_SKILLS[skill_index]
                print(
                    "[collaboration] inspect prioritized skill index={}".format(
                        skill_index
                    )
                )
                self._click_reference(point, "inspect prioritized collaboration skill")
                state.pending_skill_index = skill_index
                state.skill_step = "inspect"
                return True

            state.skill_checked_run = state.run_count
            self.actions.click_xy(
                "collaboration_collection_close",
                "close collaboration skill screen after priorities are maxed",
            )
            return True

        if state.skill_step == "inspect":
            skill_point = config.COLLABORATION_SKILLS[
                state.pending_skill_index
            ][0]
            if obs.contains("满级") or selected_skill_is_maxed(skill_point):
                print(
                    "[collaboration] prioritized skill index={} is maxed".format(
                        state.pending_skill_index
                    )
                )
                state.maxed_skill_indices.add(state.pending_skill_index)
                state.pending_skill_index = None
                state.skill_step = "select"
                return True

            self.actions.click_xy(
                "collaboration_skill_upgrade",
                "upgrade selected collaboration skill",
            )
            state.skill_step = "close"
            return True

        state.skill_checked_run = state.run_count
        state.skill_step = "select"
        state.pending_skill_index = None
        self.actions.click_xy(
            "collaboration_collection_close",
            "close collaboration skill screen after upgrade",
        )
        return True

    def _handle_prepare(self, obs):
        state = self.state.collaboration
        replacement_prompt = obs.contains("请选择要更换的道具")
        if (
            replacement_prompt
            and state.prepare_step in ("select_old", "open_replace")
        ):
            state.prepare_step = "choose_new"
        if state.prepared_run == state.run_count:
            replacement_modal_visible = (
                replacement_prompt
                or obs.contains("取消")
                or obs.contains_all("更换", "初始道具")
            )
            if replacement_modal_visible:
                # A previous no-candidate/exhaustion branch may already have
                # marked preparation complete while the replacement modal is
                # still open. The game-start coordinate is behind this modal;
                # close it first and start only after the prompt disappears.
                self._click_reference(
                    (873, 594),
                    "close collaboration item replacement before starting",
                )
                state.prepare_step = "verify_cancel"
                return True
            if not obs.contains("游戏开始"):
                print(
                    "[collaboration] prepared state has no verified game-start button; wait"
                )
                return True
            self.actions.click_xy(
                "collaboration_game_start",
                "start collaboration run with prepared item set",
            )
            state.in_run = True
            state.shop_step = "select"
            state.shop_completed = False
            state.shop_attempts = 0
            return True

        if state.prepare_step == "select_old":
            slot = config.COLLABORATION_PREPARE_SLOTS[
                state.replacement_slot_cursor % len(config.COLLABORATION_PREPARE_SLOTS)
            ]
            self._click_reference(slot, "select collaboration item slot to replace")
            state.prepare_step = "open_replace"
            return True

        if state.prepare_step == "open_replace":
            self._click_reference((842, 513), "open collaboration item replacement")
            state.prepare_step = "choose_new"
            return True

        if state.prepare_step == "choose_new":
            available = self._available_prepare_items(obs)
            priority_count = len(self.ITEM_PRIORITY)
            chosen = None
            for offset in range(priority_count):
                cursor = (state.replacement_item_cursor + offset) % priority_count
                item_index = self.ITEM_PRIORITY[cursor]
                if item_index in available:
                    chosen = item_index
                    state.replacement_item_cursor = (cursor + 1) % priority_count
                    break
            if chosen is None:
                print("[collaboration] no replacement item available; start without replacement")
                state.prepared_run = state.run_count
                state.prepare_step = "verify_cancel"
                self._click_reference(
                    (873, 594),
                    "close collaboration item replacement without an available item",
                )
                return True
            self._click_reference(
                config.COLLABORATION_PREPARE_ITEMS[chosen],
                "choose available collaboration replacement item",
            )
            state.replacement_attempts += 1
            state.prepare_step = "confirm_new"
            return True

        if state.prepare_step == "confirm_new":
            self._click_reference((733, 594), "confirm collaboration item replacement")
            state.prepare_step = "verify_new"
            return True

        if state.prepare_step == "verify_cancel":
            if obs.contains("请选择要更换的道具"):
                self._click_reference(
                    (873, 594), "cancel exhausted collaboration item replacement"
                )
                return True
        elif obs.contains("请选择要更换的道具") and (
            state.replacement_attempts >= len(self.ITEM_PRIORITY)
        ):
            self._click_reference(
                (873, 594), "cancel exhausted collaboration item replacement"
            )
            state.prepare_step = "verify_cancel"
            return True

        if obs.contains("请选择要更换的道具"):
            # Selecting the same item type as the old slot leaves this prompt
            # open. Rotate to the next available candidate instead of treating
            # the unaccepted replacement as a completed preparation.
            print("[collaboration] replacement was not accepted; try next item")
            state.prepare_step = "choose_new"
            return True

        state.prepared_run = state.run_count
        state.prepare_step = "select_old"
        state.replacement_attempts = 0
        state.replacement_slot_cursor += 1
        return True

    def _handle_shop(self, obs):
        state = self.state.collaboration
        if is_shop_insufficient_funds(obs.texts):
            confirms = obs.exact("确认")
            if len(confirms) == 1:
                self.actions.click_row(
                    confirms[0], "dismiss insufficient collaboration shop coins"
                )
            else:
                self._click_reference(
                    (540, 425), "dismiss insufficient collaboration shop coins"
                )
            state.shop_completed = True
            state.shop_step = "finish"
            return True

        if (
            is_shop_upgrade_confirmation(obs.texts)
            or is_shop_purchase_confirmation(obs.texts)
        ):
            yes_rows = obs.exact("是")
            if len(yes_rows) == 1:
                self.actions.click_row(
                    yes_rows[0], "confirm collaboration item purchase or upgrade"
                )
            else:
                self._click_reference(
                    (444, 425), "confirm collaboration item purchase or upgrade"
                )
            state.shop_visit_count += 1
            state.shop_completed = True
            state.shop_step = "finish"
            return True

        if state.shop_step == "confirm":
            # The prior upgrade click did not produce a confirmation dialog.
            # Try the other guaranteed initial item once, then leave safely.
            state.shop_attempts += 1
            state.shop_step = "select"
            if state.shop_attempts >= len(config.COLLABORATION_SHOP_UPGRADES):
                state.shop_completed = True

        if state.shop_completed:
            self.actions.click_xy(
                "collaboration_shop_confirm",
                "continue after collaboration shop upgrade",
            )
            return True

        if state.shop_step == "select":
            coins = self._visible_integer(obs, (260, 510, 380, 585))
            point, cost = config.COLLABORATION_SHOP_UPGRADES[
                (state.shop_visit_count + state.shop_attempts)
                % len(config.COLLABORATION_SHOP_UPGRADES)
            ]
            if coins is not None and coins < cost:
                state.shop_completed = True
                self.actions.click_xy(
                    "collaboration_shop_confirm",
                    "continue when collaboration shop coins are insufficient",
                )
                return True
            self._click_reference(point, "select collaboration shop item to upgrade")
            state.shop_step = "upgrade"
            return True

        if state.shop_step == "upgrade":
            upgrade_rows = [
                row for row in obs.exact("升级")
                if row["x"] >= scale_point((700, 0))[0]
                and row["y"] >= scale_point((0, 450))[1]
            ]
            if len(upgrade_rows) == 1:
                self.actions.click_row(upgrade_rows[0], "open collaboration item upgrade confirmation")
            else:
                self._click_reference((839, 515), "open collaboration item upgrade confirmation")
            state.shop_step = "confirm"
            return True

        return True

    def _return_home(self, obs):
        state = self.state.collaboration
        if self._collection_visible(obs):
            self.actions.click_xy(
                "collaboration_collection_close",
                "close collaboration collection after claiming rewards",
            )
            return True
        if self._minigame_home_visible(obs):
            self.actions.click_xy(
                "collaboration_minigame_close",
                "leave collaboration minigame after 15 achievements",
            )
            return True
        if self._event_page_visible(obs) or find_minigame_entrance_icon() is not None:
            self.actions.click_xy("event_close", "return home from collaboration event")
            return True
        if home_visible(obs):
            state.phase = CollaborationPhase.COMPLETE
            self.enter_endgame(
                "collaboration collection reached 15 achievements",
                SummonScrollKind.COLLABORATION,
            )
            return True
        return False

    def handle(self, obs):
        state = self.state.collaboration
        if state.phase == CollaborationPhase.COMPLETE:
            return False
        if state.phase == CollaborationPhase.RETURN_HOME:
            return self._return_home(obs)

        activity_guide = self._activity_guide_row(obs)
        if activity_guide is not None:
            state.started = True
            self.actions.click_row(
                activity_guide,
                "dismiss collaboration activity guide",
            )
            return True

        mission_complete = obs.exact("任务完成")
        if len(mission_complete) == 1 and obs.contains("关卡"):
            state.started = True
            self.actions.click_row(
                mission_complete[0],
                "dismiss collaboration mission-complete overlay",
            )
            return True

        if self._collection_visible(obs):
            state.started = True
            count = parse_achievement_count(obs.texts)
            if count is not None:
                state.achievement_count = max(state.achievement_count, count)
            if state.achievement_count >= self.TARGET_ACHIEVEMENTS:
                state.phase = CollaborationPhase.CLAIM_ACHIEVEMENTS

            if state.phase == CollaborationPhase.CLAIM_ACHIEVEMENTS:
                if state.reward_claim_attempts < self.MAX_REWARD_CLICKS:
                    self.actions.click_xy(
                        "collaboration_reward_claim",
                        "claim queued collaboration collection reward",
                    )
                    state.reward_claim_attempts += 1
                else:
                    state.phase = CollaborationPhase.RETURN_HOME
                return True

            state.collection_checked_run = state.run_count
            self.actions.click_xy(
                "collaboration_collection_close",
                "close collaboration collection before next run",
            )
            return True

        if self._skill_visible(obs):
            state.started = True
            return self._handle_skill(obs)

        if self._result_visible(obs):
            state.started = True
            self.actions.click_xy(
                "collaboration_result_continue",
                "continue after collaboration minigame stage result",
            )
            # A victory is a stage boundary, not necessarily the end of a run.
            state.shop_step = "select"
            state.shop_completed = False
            state.shop_attempts = 0
            return True

        if self._shop_visible(obs):
            state.started = True
            return self._handle_shop(obs)

        if self._gameplay_visible(obs):
            state.started = True
            if state.shop_completed:
                state.shop_step = "select"
                state.shop_completed = False
                state.shop_attempts = 0
            self.actions.click_xy("collaboration_roll", "roll collaboration dice")
            state.roll_count += 1
            return True

        if self._prepare_visible(obs):
            state.started = True
            return self._handle_prepare(obs)

        if self._minigame_home_visible(obs):
            state.started = True
            if state.in_run:
                state.in_run = False
                state.run_count += 1
                state.roll_count = 0
                state.prepared_run = -1
                state.prepare_step = "select_old"
                state.shop_step = "select"
                state.shop_completed = False
                state.shop_attempts = 0
            if state.collection_checked_run < state.run_count:
                collection_rows = obs.exact("收集")
                if len(collection_rows) == 1:
                    self.actions.click_row(
                        collection_rows[0],
                        "check collaboration achievement collection",
                    )
                else:
                    self.actions.click_xy(
                        "collaboration_collection",
                        "check collaboration achievement collection",
                    )
            elif state.skill_checked_run < state.run_count:
                skill_rows = obs.exact("技能")
                if len(skill_rows) == 1:
                    self.actions.click_row(
                        skill_rows[0],
                        "open collaboration skill upgrades",
                    )
                else:
                    self.actions.click_xy(
                        "collaboration_skill",
                        "open collaboration skill upgrades",
                    )
            else:
                self.actions.click_xy(
                    "collaboration_game_prepare",
                    "open collaboration minigame preparation",
                )
            return True

        entrance_icon = find_minigame_entrance_icon()
        if self._event_page_visible(obs) or entrance_icon is not None:
            state.started = True
            state.allow_internal_resume = True
            if entrance_icon is None:
                print("[collaboration] minigame dice entrance icon not visible; wait")
                return True
            self.actions.click_xy(
                "collaboration_minigame",
                "open minigame after recognizing its left dice icon",
            )
            state.phase = CollaborationPhase.PLAY
            return True

        if home_visible(obs):
            state.started = True
            self.actions.click_xy(
                "collaboration_event",
                "open collaboration activity from home",
            )
            state.phase = CollaborationPhase.OPEN_MINIGAME
            return True

        return False
