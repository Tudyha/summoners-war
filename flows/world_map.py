"""World-map progression flow."""

from .. import config
from ..core.scene_recognizer import WORLD_MAP_NAMES, world_map_match
from ..vision.core import scale_point
from ..vision.map import find_world_map_in_progress_area, find_world_map_new_area, world_map_area_star_count


class WorldMapFlow(object):
    def __init__(self, state, actions, enter_endgame):
        self.state = state
        self.actions = actions
        self.enter_endgame = enter_endgame

    def _world_maps(self):
        return WORLD_MAP_NAMES

    def _world_map_visible(self, obs):
        return world_map_match(obs) is not None

    def handle_world_map(self, obs):
        if not self._world_map_visible(obs):
            return False

        paimon_star_count = world_map_area_star_count(
            obs,
            (
                "帕伊摩恩",
                "帕伊劇恩",
                "伯伊摩恩",
                "帕伊度恩",
                "始伊摩恩",
                "帕伊摩图",
                "帕伊劇思",
            ),
        )
        if paimon_star_count == 1:
            self.enter_endgame(
                "Paimon Volcano has exactly one star on world map"
            )
            self.state.world_map.miss_count = 0
            self.actions.press_back("return home after verified one-star Paimon Volcano")
            return True

        visual_new_map = find_world_map_new_area(obs, self._world_maps())
        if visual_new_map is not None:
            self.state.world_map.miss_count = 0
            self.actions.click_point(
                visual_new_map["point"],
                "enter map marked new by orange glyph",
            )
            return True

        new_maps = obs.matching(
            lambda row: "新" in row["text"]
            and len(row["text"]) <= 3
            and scale_point((135, 0))[0] <= row["x"] <= scale_point((978, 0))[0]
            and scale_point((0, 40))[1] <= row["y"] <= scale_point((0, 608))[1]
            and not (
                scale_point((236, 0))[0] <= row["x"] <= scale_point((486, 0))[0]
                and row["y"] >= scale_point((0, 520))[1]
            )
        )
        kairos_labels = obs.matching(lambda row: "卡伊洛斯地下城" in row["text"])
        new_maps = [
            row for row in new_maps
            if not any(
                abs(row["x"] - kairos["x"]) <= scale_point((202, 0))[0]
                and abs(row["y"] - kairos["y"]) <= scale_point((0, 152))[1]
                for kairos in kairos_labels
            )
        ]
        if len(new_maps) == 1:
            self.state.world_map.miss_count = 0
            _, offset_y = scale_point((0, 36))
            self.actions.click_point(
                (new_maps[0]["x"], new_maps[0]["y"] + offset_y),
                "enter map marked new",
            )
            return True

        in_progress_map = find_world_map_in_progress_area(obs)
        if in_progress_map is not None:
            self.state.world_map.miss_count = 0
            self.actions.click_point(
                in_progress_map,
                "enter visible unlocked zero-star story map",
            )
            return True

        self.state.world_map.miss_count += 1
        if self.state.world_map.miss_count >= config.WORLD_MAP_MAX_SWIPES:
            self.state.world_map.miss_count = 0
            self.state.world_map.returning_home_for_task = True
            self.actions.press_back("return home after world map has no new area")
            return True

        self.actions.swipe_xy(
            "world_map_swipe_right",
            "world_map_swipe_left",
            "pan world map right to find new story area",
        )
        return True
