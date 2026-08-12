"""Home-island story continuation flow."""

import time

from ..vision.core import scale_point


class HomeFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def handle_home_story(self, obs):
        if self.state.endgame.is_active:
            return False

        # Runner only calls this handler after home recognition has succeeded.
        # The explicit return intent is therefore sufficient. Requiring all
        # five bottom navigation labels here made this branch stricter than
        # home recognition; one transient OCR miss fell through to Battle.
        if self.state.world_map.returning_home_for_task:
            self.state.world_map.returning_home_for_task = False
            self.actions.click_xy("home_quest", "open top-left task after world map miss")
            time.sleep(1)
            self.actions.click_point([448, 169], "click task ?")
            return True

        # if (
        #     obs.contains_all("战斗", "魔灵", "社交", "商店")
        #     and obs.contains("召唤师之路")
        #     and home_quest_arrow_present()
        # ):
        #     self.actions.click_xy("home_quest", "open highlighted story quest")
        #     return True

        # if (
        #     obs.contains_all("战斗", "魔灵", "任务", "社交", "商店")
        #     and obs.contains("请调查西泽山遗址")
        # ):
        #     self.actions.click_xy("story_question", "open story NPC dialogue")
        #     return True

        # if (
        #     any(text.startswith("LD") for text in obs.texts)
        #     and home_summon_arrow_present()
        # ):
        #     self.actions.click_xy("home_summon", "open highlighted summon")
        #     return True

        if (
            obs.contains_all("任务", "商店")
            and any(text.startswith("LD") for text in obs.texts)
        ):
            self.actions.click_xy("home_battle", "continue story from home")
            time.sleep(1)
            return True

        return False

    def handle_home_ownership(self, obs):
        """Handle home actions and prevent lower-priority visual misclicks."""

        if obs.contains_all("信息", "编辑"):
            # Android Back on the island opens the exit-game prompt. Use the
            # inbox as a safe modal round-trip to clear the selected object.
            inbox_rows = obs.matching(
                lambda row: "收件箱" in row["text"]
                and row["x"] <= scale_point((168, 0))[0]
            )
            if len(inbox_rows) == 1:
                self.actions.click_row(
                    inbox_rows[0],
                    "open inbox to clear selected home object",
                )
            else:
                self.actions.click_xy("inbox", "open inbox to clear selected home object")
            return True
        return self.handle_home_story(obs)
