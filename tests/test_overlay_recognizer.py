import unittest

from ._package import project_module


screen_model = project_module("core.screen_model")
overlay_recognizer = project_module("core.overlay_recognizer")
Overlay = screen_model.Overlay


class FakeObservation(object):
    def __init__(self, texts):
        self.texts = list(texts)

    def contains(self, fragment):
        return any(fragment in text for text in self.texts)

    def contains_all(self, *fragments):
        return all(self.contains(fragment) for fragment in fragments)


class OverlayRecognizerTests(unittest.TestCase):
    def test_support_list_is_owned_by_battle_flow(self):
        matches = overlay_recognizer.recognize_overlays(
            FakeObservation(("好友魔灵", "确认"))
        )

        self.assertEqual(Overlay.SUPPORT_LIST, matches[0].overlay)
        self.assertEqual("battle", matches[0].owner)

    def test_confirmation_text_alone_is_not_a_global_overlay(self):
        matches = overlay_recognizer.recognize_overlays(
            FakeObservation(("确认", "是"))
        )

        self.assertEqual([], matches)

    def test_promotion_requires_multiple_markers(self):
        matches = overlay_recognizer.recognize_overlays(
            FakeObservation(("限时礼包", "购买商品"))
        )

        self.assertTrue(any(match.overlay == Overlay.PROMOTION for match in matches))

    def test_leader_skill_warning_is_not_used_support_warning(self):
        observation = FakeObservation((
            "没有可使用的领袖技能。确定要继续战斗吗？",
            "魔灵",
        ))

        self.assertTrue(
            overlay_recognizer.leader_skill_warning_visible(observation)
        )
        self.assertFalse(
            overlay_recognizer.used_support_warning_text_visible(observation)
        )

    def test_used_support_warning_requires_explicit_wording(self):
        observation = FakeObservation(("已使用的魔灵无法再次使用",))

        self.assertTrue(
            overlay_recognizer.used_support_warning_text_visible(observation)
        )


if __name__ == "__main__":
    unittest.main()
