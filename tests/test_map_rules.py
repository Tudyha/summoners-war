import unittest

from ._package import project_module


map_rules = project_module("core.map_rules")


class WorldMapStarRulesTests(unittest.TestCase):
    def test_real_bright_star_is_accepted(self):
        self.assertTrue(map_rules.is_bright_world_map_star(200.5, 21, 21, 1.0))

    def test_terrain_fragments_are_rejected(self):
        self.assertFalse(map_rules.is_bright_world_map_star(52.5, 13, 11, 1.0))
        self.assertFalse(map_rules.is_bright_world_map_star(1353.0, 91, 35, 1.0))


class HomeSummonCircleRulesTests(unittest.TestCase):
    def test_accepts_wide_live_summon_circle(self):
        self.assertTrue(
            map_rules.is_home_summon_circle_component(
                9767.0, 164, 102, 0.584, 1.0, 1.0
            )
        )

    def test_rejects_round_dimensional_portal(self):
        self.assertFalse(
            map_rules.is_home_summon_circle_component(
                13564.0, 167, 148, 0.549, 1.0, 1.0
            )
        )

    def test_rejects_tall_mana_pool(self):
        self.assertFalse(
            map_rules.is_home_summon_circle_component(
                12388.0, 177, 129, 0.54, 1.0, 1.0
            )
        )


if __name__ == "__main__":
    unittest.main()
