"""Priority-based reactive behavior routing."""


class BehaviorStatus(object):
    NO_MATCH = "no_match"
    ACTED = "acted"
    RUNNING = "running"
    BLOCKED = "blocked"
    FAILED = "failed"


class BehaviorResult(object):
    def __init__(self, status, behavior=None, detail=None):
        self.status = status
        self.behavior = behavior
        self.detail = detail

    @property
    def handled(self):
        return self.status in (
            BehaviorStatus.ACTED,
            BehaviorStatus.RUNNING,
            BehaviorStatus.BLOCKED,
        )

    @classmethod
    def no_match(cls, behavior=None):
        return cls(BehaviorStatus.NO_MATCH, behavior)

    @classmethod
    def acted(cls, behavior, detail=None):
        return cls(BehaviorStatus.ACTED, behavior, detail)

    @classmethod
    def running(cls, behavior, detail=None):
        return cls(BehaviorStatus.RUNNING, behavior, detail)


class HandlerBehavior(object):
    """Adapt a focused Flow handler to the behavior-result contract."""

    def __init__(self, name, handler, enabled=None, blocks_when_idle=False):
        self.name = name
        self.handler = handler
        self.enabled = enabled
        self.blocks_when_idle = blocks_when_idle

    def tick(self, context):
        if self.enabled is not None and not self.enabled(context):
            return BehaviorResult.no_match(self.name)
        if self.handler(context):
            return BehaviorResult.acted(self.name)
        if self.blocks_when_idle:
            return BehaviorResult.running(
                self.name,
                "behavior owns the current workflow",
            )
        return BehaviorResult.no_match(self.name)


class PriorityRouter(object):
    def __init__(self, behaviors):
        self.behaviors = list(behaviors)

    def tick(self, context):
        for behavior in self.behaviors:
            result = behavior.tick(context)
            if result.status != BehaviorStatus.NO_MATCH:
                return result
        return BehaviorResult.no_match()
