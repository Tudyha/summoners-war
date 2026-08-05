import unittest

from ._package import project_module


screen_model = project_module("core.screen_model")
scene_recognizer = project_module("core.scene_recognizer")
Scene = screen_model.Scene


class FakeObservation(object):
    def __init__(self, texts):
        self.texts = list(texts)

    def contains(self, fragment):
        return any(fragment in text for text in self.texts)


class SceneRecognizerTests(unittest.TestCase):
    def test_stage_list_foreground_preempts_world_map_background(self):
        observation = FakeObservation((
            "西泽山",
            "拉古恩雪山",
            "卡菲勒遗址",
            "任务",
            "掉落信息",
            "难度级别 普通",
        ))

        self.assertIsNone(scene_recognizer.world_map_match(observation))
        self.assertEqual(
            Scene.STAGE_LIST,
            scene_recognizer.recognize_scene(observation).scene,
        )

    def test_world_map_survives_one_missing_stable_anchor(self):
        observation = FakeObservation((
            "试炼之塔", "异界的缝隙", "西泽山", "拉古恩雪山",
        ))

        self.assertIsNotNone(scene_recognizer.world_map_match(observation))

    def test_world_map_uses_multiple_independent_anchors(self):
        observation = FakeObservation((
            "竞技场", "试炼之塔", "异界的缝隙", "任务", "艾登丛林",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.WORLD_MAP, match.scene)
        self.assertGreaterEqual(match.confidence, 0.8)
        self.assertIn("艾登丛林", match.evidence)

    def test_late_world_map_ocr_variants_are_recognized(self):
        observation = FakeObservation((
            "年勒遗址",
            "夏依德尼遗址",
            "塔摩勒沙漠",
            "任务",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.WORLD_MAP, match.scene)
        self.assertIn("年勒遗址", match.evidence)

    def test_single_map_name_is_not_enough(self):
        observation = FakeObservation(("艾登丛林", "确认"))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.UNKNOWN, match.scene)

    def test_support_overlay_has_stronger_identity_than_generic_summon_text(self):
        observation = FakeObservation(("好友魔灵", "召唤", "魔灵"))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.SUPPORT_LIST, match.scene)

    def test_home_requires_navigation_and_home_identity(self):
        observation = FakeObservation((
            "战斗", "魔灵", "任务", "社交", "商店", "LD123456",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.HOME, match.scene)

    def test_navigation_words_without_home_identity_are_not_enough(self):
        observation = FakeObservation(("战斗", "魔灵", "任务", "社交", "商店"))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.UNKNOWN, match.scene)

    def test_summon_ui_accepts_exact_title(self):
        observation = FakeObservation(("魔灵召喚阵",))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.SUMMON, match.scene)

    def test_dialogue_mention_does_not_become_summon_scene(self):
        observation = FakeObservation((
            "下一个要介绍的非常重要！那就是魔灵召唤阵。",
            "4艾琳",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.UNKNOWN, match.scene)

    def test_summon_ui_accepts_split_light_dark_evidence(self):
        observation = FakeObservation(("光明", "黑暗召唤书", "特别召唤"))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.SUMMON, match.scene)

    def test_summon_word_without_specific_evidence_is_not_enough(self):
        observation = FakeObservation(("召唤", "魔灵"))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.UNKNOWN, match.scene)

    def test_tutorial_ten_summon_result_has_its_own_scene(self):
        observation = FakeObservation((
            "召唤结果",
            "千连召结果",
            "10次特别唤",
            "确队",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.SUMMON_RESULT, match.scene)

    def test_message_activity_center_has_its_own_scene(self):
        observation = FakeObservation((
            "消息",
            "公告事项",
            "活动",
            "游戏引导",
        ))

        match = scene_recognizer.recognize_scene(observation)

        self.assertEqual(Scene.MESSAGE_CENTER, match.scene)


if __name__ == "__main__":
    unittest.main()
