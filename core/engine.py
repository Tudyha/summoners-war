"""Automation runtime: perceive, decide, act, then observe again."""

import time

from .. import config
from .behavior_router import BehaviorStatus
from ..platform.lifecycle import ensure_game
from .overlay_recognizer import recognize_overlays
from .scene_recognizer import recognize_scene
from .screen_model import DecisionContext, ScreenSnapshot
from ..vision.core import begin_visual_frame, display_size, observe


class AutomationEngine(object):
    def __init__(self, runner):
        self.runner = runner

    def _capture_context(self):
        begin_visual_frame()
        observation = observe()
        scene_match = recognize_scene(observation)
        overlays = recognize_overlays(observation)
        snapshot = ScreenSnapshot(observation, scene_match, overlays)
        return DecisionContext(self.runner, snapshot)

    def run_forever(self):
        # ensure_game()
        width, height = display_size()
        print("[runner] display {}x{} landscape".format(width, height))
        print("[runner] reactive screen-driven engine started")

        while True:
            stop = self.runner.state.stop
            if stop.requested_by_operator:
                print("[runner] stopped by Feishu operator decision")
                return
            if stop.for_five_star:
                print("[runner] five-star reply window ended; script stopped")
                return
            if stop.before_reset:
                print("[runner] stopped before data initialization")
                return

            try:
                context = self._capture_context()
                result = self.runner.tick(context)
                runtime = self.runner.state.runtime
                runtime.last_scene = context.snapshot.scene
                runtime.last_behavior = result.behavior
                runtime.consecutive_errors = 0

                if (
                    result.status == BehaviorStatus.NO_MATCH
                    and time.time() - runtime.last_unknown_log_at
                    > config.UNKNOWN_LOG_SECONDS
                ):
                    print(
                        "[observe] no handler scene={} confidence={:.2f}: {}".format(
                            context.snapshot.scene,
                            context.snapshot.scene_match.confidence,
                            context.observation.compact_text(),
                        )
                    )
                    runtime.last_unknown_log_at = time.time()
                elif (
                    result.status == BehaviorStatus.RUNNING
                    and result.behavior == "endgame"
                    and time.time() - runtime.last_action_at
                    > config.UNKNOWN_LOG_SECONDS
                    and time.time() - runtime.last_unknown_log_at
                    > config.UNKNOWN_LOG_SECONDS
                ):
                    print(
                        "[endgame] waiting without action scene={} overlays={}: {}".format(
                            context.snapshot.scene,
                            [match.overlay for match in context.snapshot.overlays],
                            context.observation.compact_text(),
                        )
                    )
                    runtime.last_unknown_log_at = time.time()
            except Exception as exc:
                runtime = self.runner.state.runtime
                runtime.consecutive_errors += 1
                print(
                    "[runner] recoverable error #{}: {}".format(
                        runtime.consecutive_errors,
                        exc,
                    )
                )
            time.sleep(config.POLL_SECONDS)
