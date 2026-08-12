import unittest

from ._package import project_module


summon_rules = project_module("core.summon_rules")


class SummonRulesTests(unittest.TestCase):
    def test_summon_title_must_be_standalone(self):
        self.assertTrue(summon_rules.is_summon_ui_title("魔灵召唤阵"))
        self.assertFalse(
            summon_rules.is_summon_ui_title(
                "下一个要介绍的非常重要！那就是魔灵召唤阵。"
            )
        )

    def test_accepts_live_light_dark_icon_component(self):
        self.assertTrue(
            summon_rules.is_light_dark_scroll_icon_component(
                4021.5, 73, 81, 0.68, 1.0, 1.0
            )
        )

    def test_rejects_small_magenta_fragment_from_other_scroll(self):
        self.assertFalse(
            summon_rules.is_light_dark_scroll_icon_component(
                294.5, 37, 15, 0.531, 1.0, 1.0
            )
        )

    def test_collaboration_icon_requires_cyan_red_and_cream_artwork(self):
        self.assertTrue(
            summon_rules.is_collaboration_scroll_icon_patch(0.34, 0.09, 0.18)
        )
        self.assertFalse(
            summon_rules.is_collaboration_scroll_icon_patch(0.34, 0.0, 0.18)
        )
        self.assertFalse(
            summon_rules.is_collaboration_scroll_icon_patch(0.34, 0.09, 0.0)
        )

    def test_accepts_result_panel_star_component(self):
        self.assertTrue(
            summon_rules.is_summon_result_star_component(
                260, 27, 27, 0.36, 1.0, 1.0
            )
        )

    def test_rejects_small_result_panel_gold_fragment(self):
        self.assertFalse(
            summon_rules.is_summon_result_star_component(
                18, 7, 6, 0.43, 1.0, 1.0
            )
        )


if __name__ == "__main__":
    unittest.main()
