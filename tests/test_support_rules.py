import unittest

from ._package import project_module


support_rules = project_module("core.support_rules")


class SupportSlotRulesTests(unittest.TestCase):
    def test_flat_empty_placeholder_is_rejected(self):
        self.assertFalse(support_rules.is_occupied_support_slot(8.5, 0.0))

    def test_detailed_monster_card_is_accepted(self):
        self.assertTrue(support_rules.is_occupied_support_slot(32.2, 0.288))

    def test_one_strong_feature_does_not_create_a_false_positive(self):
        self.assertFalse(support_rules.is_occupied_support_slot(32.2, 0.02))
        self.assertFalse(support_rules.is_occupied_support_slot(10.0, 0.288))


if __name__ == "__main__":
    unittest.main()
