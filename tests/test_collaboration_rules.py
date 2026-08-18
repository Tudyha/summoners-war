import unittest

from ._package import project_module


rules = project_module("core.collaboration_rules")


class CollaborationRulesTests(unittest.TestCase):
    def test_all_observed_activity_guide_pages_are_recognized(self):
        pages = [
            "全新活动地下城围剿委托现已开启,体验不一样的战斗!",
            "每次通关关卡时,均可获得带有特殊效果的魔导书。",
            "与联动角色一起挑战围剿委托吧!",
            "联动期间,还可以体验全新小游戏召唤骰子。",
            "召唤骰子是一款桌游风格小游戏。",
            "参与小游戏,收集全新道具,完成收集吧。",
        ]

        for page in pages:
            self.assertTrue(rules.is_collaboration_activity_guide([page]))
            self.assertTrue(rules.is_collaboration_internal_screen([page]))
        self.assertFalse(rules.is_collaboration_activity_guide([
            "联动通行证", "活动期间", "小游戏",
        ]))

    def test_dice_icon_requires_all_three_visual_features(self):
        self.assertTrue(rules.is_minigame_entrance_icon(0.31, 0.14, 6))
        self.assertTrue(rules.is_minigame_entrance_icon(0.521, 0.254, 1))
        self.assertFalse(rules.is_minigame_entrance_icon(0.31, 0.14, 0))
        self.assertFalse(rules.is_minigame_entrance_icon(0.01, 0.14, 6))
        self.assertFalse(rules.is_minigame_entrance_icon(0.31, 0.0, 6))

    def test_achievement_counter_accepts_only_collection_total(self):
        self.assertEqual(15, rules.parse_achievement_count(["收集进度 (15/37)"]))
        self.assertEqual(12, rules.parse_achievement_count(["3/10", "12 / 37"]))
        self.assertIsNone(rules.parse_achievement_count(["15/30"]))

    def test_fraction_parser_tolerates_ocr_letter_o_for_zero(self):
        self.assertEqual((0, 2), rules.parse_fraction("O/2"))
        self.assertEqual((1, 1), rules.parse_fraction(" 1 / 1 "))
        self.assertIsNone(rules.parse_fraction("available"))

    def test_integer_parser_rejects_labels_and_fractions(self):
        self.assertEqual(195, rules.parse_integer("195"))
        self.assertEqual(1200, rules.parse_integer("1,200"))
        self.assertIsNone(rules.parse_integer("10/20"))
        self.assertIsNone(rules.parse_integer("cost 10"))

    def test_shop_upgrade_confirmation_accepts_simplified_and_traditional(self):
        self.assertTrue(rules.is_shop_upgrade_confirmation([
            "是否升级所选道具?", "是", "否",
        ]))
        self.assertTrue(rules.is_shop_upgrade_confirmation([
            "是否升級所选道具?", "是", "否",
        ]))
        self.assertFalse(rules.is_shop_upgrade_confirmation([
            "商店", "升级", "确认",
        ]))

    def test_shop_purchase_confirmation_requires_the_full_prompt(self):
        self.assertTrue(rules.is_shop_purchase_confirmation([
            "是否购买所选道具?", "是", "否",
        ]))
        self.assertFalse(rules.is_shop_purchase_confirmation([
            "道具购买及升级", "确认",
        ]))

    def test_shop_insufficient_funds_requires_all_modal_anchors(self):
        self.assertTrue(rules.is_shop_insufficient_funds([
            "商店", "持有的铜钱不足", "确认",
        ]))
        self.assertTrue(rules.is_shop_insufficient_funds([
            "商店", "持有的銅线不足", "确认",
        ]))
        self.assertFalse(rules.is_shop_insufficient_funds([
            "持有硬币", "商店", "确认",
        ]))

    def test_skill_candidate_skips_only_proven_maxed_priorities(self):
        priority = (11, 9, 0)

        self.assertEqual(11, rules.choose_skill_candidate(priority))
        self.assertEqual(
            9,
            rules.choose_skill_candidate(priority, {11}),
        )

    def test_selected_skill_level_parser(self):
        self.assertEqual(6, rules.parse_skill_level("增加体力 6级"))
        self.assertEqual(12, rules.parse_skill_level("增加骰子12 级"))
        self.assertIsNone(rules.parse_skill_level("技能升级"))

    def test_yellow_skill_badge_proves_max_level(self):
        self.assertFalse(rules.is_skill_max_badge(0.0))
        self.assertFalse(rules.is_skill_max_badge(0.02))
        self.assertTrue(rules.is_skill_max_badge(0.03))

    def test_internal_screen_resume_uses_strong_minigame_anchors(self):
        self.assertTrue(rules.is_collaboration_internal_screen([
            "关卡2", "体力", "护盾",
        ]))
        self.assertTrue(rules.is_collaboration_internal_screen([
            "技能", "收集", "帮助", "召唤骰子", "游戏准备",
        ]))
        self.assertFalse(rules.is_collaboration_internal_screen([
            "关卡2", "体力",
        ]))
        self.assertFalse(rules.is_collaboration_internal_screen([
            "刷取模式", "请选择本次脚本目标", "关卡2", "体力", "护盾",
        ]))
        self.assertFalse(rules.is_collaboration_internal_screen([
            "关卡2", "胜利", "已击败", "任务完成",
        ]))
        self.assertFalse(rules.is_collaboration_internal_screen([
            "加仑丛林小道[普通]", "对战", "开始战斗", "体力", "护盾",
        ]))

    def test_minigame_landing_page_is_not_gameplay(self):
        self.assertFalse(rules.is_gameplay_screen([
            "召唤骰子",
            "最高记录",
            "关卡2",
            "游戏准备",
            "技能",
            "收集",
            "帮助",
        ]))
        self.assertTrue(rules.is_gameplay_screen(["关卡2", "体力", "骰子"]))


if __name__ == "__main__":
    unittest.main()
