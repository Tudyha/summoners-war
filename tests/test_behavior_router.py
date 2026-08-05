import unittest

from ._package import project_module


router_module = project_module("core.behavior_router")
BehaviorStatus = router_module.BehaviorStatus
HandlerBehavior = router_module.HandlerBehavior
PriorityRouter = router_module.PriorityRouter


class PriorityRouterTests(unittest.TestCase):
    def test_first_action_preempts_lower_priority_behaviors(self):
        calls = []
        router = PriorityRouter((
            HandlerBehavior("overlay", lambda context: calls.append("overlay") or True),
            HandlerBehavior("scene", lambda context: calls.append("scene") or True),
        ))

        result = router.tick(object())

        self.assertEqual(BehaviorStatus.ACTED, result.status)
        self.assertEqual("overlay", result.behavior)
        self.assertEqual(["overlay"], calls)

    def test_owner_can_block_lower_priority_handlers_without_clicking(self):
        calls = []
        router = PriorityRouter((
            HandlerBehavior(
                "endgame",
                lambda context: False,
                enabled=lambda context: True,
                blocks_when_idle=True,
            ),
            HandlerBehavior("battle", lambda context: calls.append("battle") or True),
        ))

        result = router.tick(object())

        self.assertEqual(BehaviorStatus.RUNNING, result.status)
        self.assertEqual("endgame", result.behavior)
        self.assertEqual([], calls)

    def test_disabled_owner_does_not_block(self):
        router = PriorityRouter((
            HandlerBehavior(
                "endgame",
                lambda context: False,
                enabled=lambda context: False,
                blocks_when_idle=True,
            ),
            HandlerBehavior("battle", lambda context: True),
        ))

        result = router.tick(object())

        self.assertEqual(BehaviorStatus.ACTED, result.status)
        self.assertEqual("battle", result.behavior)


if __name__ == "__main__":
    unittest.main()
