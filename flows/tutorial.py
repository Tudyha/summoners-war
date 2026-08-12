"""Tutorial arrow, text overlay, and dialogue flow."""

from .. import config
from ..core.scene_recognizer import (
    home_visible,
    summon_result_match,
    world_map_match,
)
from ..vision.tutorial import (
    dialogue_present,
    find_tutorial_text_overlay,
    find_yellow_arrow,
)


class TutorialFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def handle_generic_tap_texts(self, obs):
        for text in config.GENERIC_TAP_TEXTS:
            if obs.contains(text):
                self.actions.click_xy("dialogue", "dismiss generic guide text: {}".format(text))
                return True
        return False

    def handle_yellow_arrow(self, obs):
        excluded_maps = (
            "保罗帕贵址",
            "保罗帕斯遗址",
            "保罗帕库斯遗址",
            "保罗帕市遗址",
            "保罗帕遗址",
            "保罗帕市贵址",
            "保罗帕库鄭遗址",
            "保罗帕库遗址",
            "保罗帕库遗址",
            "保罗帕所遗址",
        )
        if any(obs.contains(name) for name in excluded_maps):
            return False
        arrow_target = find_yellow_arrow()
        if arrow_target is None:
            return False
        self.actions.click_point(arrow_target, "follow yellow tutorial arrow")
        return True

    def handle_tutorial_overlay(self, obs):
        # The collaboration item-replacement modal dims the board and contains
        # a wide gold/brown item-description frame, so it satisfies the generic
        # visual tutorial shape.  Its title/prompt prove that this is a real
        # business screen; leave it to CollaborationFlow instead of clicking
        # the description panel forever.
        if (
            obs.contains("请选择要更换的道具")
            or obs.contains_all("游戏准备", "初始道具")
        ):
            return False
        overlay_target = find_tutorial_text_overlay()
        if overlay_target is None:
            return False
        self.actions.click_point(overlay_target, "dismiss generic tutorial text overlay")
        return True

    def handle_dialogue(self, obs):
        if (
            summon_result_match(obs) is None
            and not world_map_match(obs) is not None
            and not home_visible(obs)
            and dialogue_present(obs)
        ):
            self.actions.click_xy("dialogue", "advance NPC dialogue")
            return True
        return False
