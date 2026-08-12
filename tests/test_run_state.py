import unittest

from ._package import project_module


state_module = project_module("core.run_state")


class RunnerStateTests(unittest.TestCase):
    def test_nickname_reset_clears_previous_account(self):
        state = state_module.RunnerState()
        state.nickname.value = "LD1234567890"
        state.nickname.completed = True
        state.nickname.input_attempts = 3

        state.nickname.reset()

        self.assertEqual("", state.nickname.value)
        self.assertFalse(state.nickname.completed)
        self.assertEqual(0, state.nickname.input_attempts)
        self.assertEqual(state_module.NicknamePhase.INACTIVE, state.nickname.phase)

    def test_workflow_state_is_grouped(self):
        state = state_module.RunnerState()

        state.battle.needs_support_selection = True
        state.endgame.phase = state_module.EndgamePhase.RESET
        state.nickname.phase = state_module.NicknamePhase.WAITING_CONFIRM
        state.battle.support_count_checked_for_preparation = True
        state.friend.attempted_for_preparation = True

        self.assertTrue(state.battle.needs_support_selection)
        self.assertEqual(state_module.EndgamePhase.RESET, state.endgame.phase)
        self.assertTrue(state.endgame.is_active)
        self.assertTrue(state.nickname.is_active)
        self.assertTrue(state.battle.support_count_checked_for_preparation)
        self.assertTrue(state.friend.attempted_for_preparation)
        self.assertFalse(state.friend.requests_disabled)

    def test_groups_do_not_share_mutable_collections(self):
        first = state_module.RunnerState()
        second = state_module.RunnerState()

        first.endgame.summon_rejected_points.append((1, 2))

        self.assertEqual([], second.endgame.summon_rejected_points)

    def test_collaboration_mode_and_reset_are_per_account(self):
        state = state_module.RunnerState(state_module.RunMode.COLLABORATION)
        state.collaboration.started = True
        state.collaboration.achievement_count = 15
        state.collaboration.in_run = True
        state.collaboration.skill_step = "upgrade"
        state.collaboration.maxed_skill_indices.update((11, 9))
        state.collaboration.pending_skill_index = 9
        state.collaboration.prepare_step = "confirm_new"
        state.collaboration.replacement_attempts = 3
        state.collaboration.shop_step = "confirm"
        state.collaboration.phase = state_module.CollaborationPhase.COMPLETE
        state.endgame.scroll_kind = state_module.SummonScrollKind.COLLABORATION

        state.collaboration.reset(allow_internal_resume=False)

        self.assertEqual(state_module.RunMode.COLLABORATION, state.run_mode)
        self.assertFalse(state.collaboration.started)
        self.assertEqual(0, state.collaboration.achievement_count)
        self.assertFalse(state.collaboration.in_run)
        self.assertEqual("select", state.collaboration.skill_step)
        self.assertEqual(set(), state.collaboration.maxed_skill_indices)
        self.assertIsNone(state.collaboration.pending_skill_index)
        self.assertFalse(state.collaboration.allow_internal_resume)
        self.assertEqual("select_old", state.collaboration.prepare_step)
        self.assertEqual(0, state.collaboration.replacement_attempts)
        self.assertEqual("select", state.collaboration.shop_step)
        self.assertEqual(
            state_module.CollaborationPhase.OPEN_EVENT,
            state.collaboration.phase,
        )
        self.assertEqual(
            state_module.SummonScrollKind.COLLABORATION,
            state.endgame.scroll_kind,
        )

    def test_friend_request_requires_measured_support_count_below_six(self):
        state = state_module.RunnerState()

        state.battle.support_monster_count = 5
        self.assertFalse(
            state.friend.should_request_for_support(state.battle)
        )

        state.battle.support_count_checked_for_preparation = True
        self.assertTrue(
            state.friend.should_request_for_support(state.battle)
        )

        state.battle.support_monster_count = 6
        self.assertFalse(
            state.friend.should_request_for_support(state.battle)
        )

        state.battle.support_monster_count = 5
        state.friend.attempted_for_preparation = True
        self.assertFalse(
            state.friend.should_request_for_support(state.battle)
        )


if __name__ == "__main__":
    unittest.main()
