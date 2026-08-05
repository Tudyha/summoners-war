import unittest

from ._package import project_module


state_module = project_module("core.run_state")
nickname_module = project_module("flows.nickname")


class FakeClock(object):
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now


class FakeNode(object):
    def __init__(self, text=""):
        self.text = text


class FakeSelector(object):
    def __init__(self, actions):
        self.actions = actions

    def find(self):
        return self.actions.field


class FakeActions(object):
    def __init__(self):
        self.field = FakeNode()
        self.done = FakeNode()
        self.inputs = []
        self.ime_inputs = []
        self.node_clicks = []
        self.row_clicks = []

    def find_node_by_id(self, resource_id):
        selector = FakeSelector(self)
        if resource_id.endswith("eedittext_input"):
            return selector, self.field
        return selector, self.done

    def input_node(self, node, text):
        self.inputs.append(text)

    def ime_clear(self):
        pass

    def ime_input(self, text):
        self.ime_inputs.append(text)

    def click_node(self, node, reason):
        self.node_clicks.append(reason)

    def click_row(self, row, reason):
        self.row_clicks.append((row, reason))


class FakeObservation(object):
    def __init__(self, texts=()):
        self.rows = [
            {"text": text, "x": 500, "y": 500}
            for text in texts
        ]

    def matching(self, predicate):
        return [row for row in self.rows if predicate(row)]

    def compact_text(self):
        return " | ".join(row["text"] for row in self.rows)


class NicknameFlowTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.original_time = nickname_module.time
        nickname_module.time = self.clock
        self.state = state_module.RunnerState()
        self.actions = FakeActions()
        self.flow = nickname_module.NicknameFlow(self.state, self.actions)

    def tearDown(self):
        nickname_module.time = self.original_time

    def test_enters_once_then_submits_same_nickname(self):
        self.assertTrue(self.flow.handle_field())
        value = self.state.nickname.value
        self.assertEqual([value], self.actions.inputs)
        self.assertEqual(
            state_module.NicknamePhase.TEXT_ENTERED,
            self.state.nickname.phase,
        )

        self.actions.field.text = value
        self.clock.now += 1.0
        self.assertTrue(self.flow.handle_field())
        self.assertEqual([value], self.actions.inputs)
        self.assertEqual(1, len(self.actions.node_clicks))
        self.assertEqual(
            state_module.NicknamePhase.WAITING_CONFIRM,
            self.state.nickname.phase,
        )

        self.clock.now += 0.5
        self.assertFalse(self.flow.handle_field())
        self.assertEqual([value], self.actions.inputs)
        self.assertEqual(1, len(self.actions.node_clicks))

    def test_visible_field_starts_new_cycle_after_previous_account(self):
        nickname = self.state.nickname
        nickname.value = "LD9999999999"
        nickname.completed = True

        self.assertTrue(self.flow.handle_field())

        self.assertFalse(nickname.completed)
        self.assertNotEqual("LD9999999999", nickname.value)
        self.assertEqual([nickname.value], self.actions.inputs)
        self.assertEqual(
            state_module.NicknamePhase.TEXT_ENTERED,
            nickname.phase,
        )

    def test_game_confirmation_completes_owned_flow(self):
        nickname = self.state.nickname
        nickname.value = "LD1234567890"
        nickname.phase = state_module.NicknamePhase.WAITING_CONFIRM
        nickname.last_submit_at = self.clock.now
        self.actions.field = None

        self.assertTrue(self.flow.handle_pending(FakeObservation(("确认",))))
        self.assertEqual(1, len(self.actions.row_clicks))
        self.assertEqual(
            state_module.NicknamePhase.CONFIRMING,
            nickname.phase,
        )

        self.clock.now += 2.0
        self.assertFalse(self.flow.handle_pending(FakeObservation()))
        self.assertTrue(nickname.completed)
        self.assertFalse(nickname.is_active)

    def test_pending_flow_never_generates_a_second_nickname(self):
        self.assertTrue(self.flow.handle_field())
        value = self.state.nickname.value
        self.state.nickname.phase = state_module.NicknamePhase.WAITING_CONFIRM
        self.state.nickname.last_submit_at = self.clock.now

        self.clock.now += 0.5
        self.flow.handle_field()
        self.clock.now += 0.5
        self.flow.handle_pending(FakeObservation())

        self.assertEqual(value, self.state.nickname.value)
        self.assertEqual([value], self.actions.inputs)

    def test_stale_node_text_uses_bounded_ime_fallback_then_submits(self):
        self.assertTrue(self.flow.handle_field())
        for _ in range(nickname_module.config.NICKNAME_MAX_ATTEMPTS - 1):
            self.clock.now += 1.0
            self.assertTrue(self.flow.handle_field())

        self.clock.now += 1.0
        self.assertTrue(self.flow.handle_field())
        self.assertEqual(
            nickname_module.config.NICKNAME_MAX_ATTEMPTS - 1,
            len(self.actions.ime_inputs),
        )
        self.assertEqual(1, len(self.actions.node_clicks))
        self.assertEqual(
            state_module.NicknamePhase.WAITING_CONFIRM,
            self.state.nickname.phase,
        )


if __name__ == "__main__":
    unittest.main()
