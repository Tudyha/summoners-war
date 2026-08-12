"""Composition root for the reactive Summoners War automation."""

from .core.behavior_router import HandlerBehavior, PriorityRouter
from .core.engine import AutomationEngine
from .core.overlay_recognizer import recognize_overlays
from .core.run_state import RunMode, RunnerState
from .core.scene_recognizer import home_visible, recognize_scene
from .core.screen_model import DecisionContext, ScreenSnapshot
from .flows.battle import BattleFlow
from .flows.collaboration import CollaborationFlow
from .flows.endgame import EndgameFlow
from .flows.friend import FriendFlow
from .flows.home import HomeFlow
from .flows.nickname import NicknameFlow
from .flows.overlay import OverlayFlow
from .flows.startup import StartupFlow
from .flows.tutorial import TutorialFlow
from .flows.world_map import WorldMapFlow
from .platform.actions import DeviceActions
class Runner(object):
    """Own dependencies and route one immutable screen snapshot per tick."""

    def __init__(self, run_mode=RunMode.VOLCANO):
        self.state = RunnerState(run_mode)
        self.actions = DeviceActions(self.state)

        self.endgame = EndgameFlow(self.state, self.actions)
        self.collaboration = CollaborationFlow(
            self.state, self.actions, self.endgame.enter
        )
        self.friend = FriendFlow(self.state, self.actions)
        self.nickname = NicknameFlow(self.state, self.actions)
        self.overlay = OverlayFlow(self.state, self.actions)
        self.startup = StartupFlow(self.state, self.actions)
        self.battle = BattleFlow(self.state, self.actions)
        self.home = HomeFlow(self.state, self.actions)
        self.world_map = WorldMapFlow(
            self.state,
            self.actions,
            self.endgame.enter,
        )
        self.tutorial = TutorialFlow(self.state, self.actions)
        self.router = self._build_router()

    def _build_router(self):
        def handler(name, method, enabled=None, blocks_when_idle=False):
            return HandlerBehavior(
                name,
                lambda context: method(context.observation),
                enabled=enabled,
                blocks_when_idle=blocks_when_idle,
            )

        return PriorityRouter((
            handler("chat_overlay", self.friend.handle_stray_chat_layers),
            handler("global_overlay", self.overlay.handle_global_overlays),
            # Accessibility provides an exact editable-node match. Keep it
            # ahead of OCR dialogue and tutorial heuristics.
            handler("nickname_field", self.nickname.handle_field),
            handler(
                "nickname",
                self.nickname.handle_pending,
                enabled=lambda context: self.state.nickname.is_active,
                blocks_when_idle=True,
            ),
            handler(
                "endgame",
                self.endgame.handle,
                enabled=lambda context: self.state.endgame.is_active,
                blocks_when_idle=True,
            ),
            # A visible forced-guide arrow is more specific than the generic
            # home scene. It must act before HomeFlow's default Battle click.
            handler("tutorial_arrow", self.tutorial.handle_yellow_arrow),
            handler("tutorial_overlay", self.tutorial.handle_tutorial_overlay),
            handler(
                "generic_tutorial_text",
                self.tutorial.handle_generic_tap_texts,
            ),
            handler("dialogue", self.tutorial.handle_dialogue),
            handler(
                "collaboration",
                self.collaboration.handle,
                enabled=lambda context: (
                    self.state.run_mode == RunMode.COLLABORATION
                    and not self.state.endgame.is_active
                    and (
                        self.state.collaboration.started
                        or self.collaboration.entrance_visible(context.observation)
                    )
                ),
                blocks_when_idle=True,
            ),
            handler(
                "home",
                self.home.handle_home_ownership,
                enabled=lambda context: (
                    not self.state.endgame.is_active
                    and (self.state.run_mode == RunMode.VOLCANO
                         or not self.state.collaboration.started)
                    and home_visible(context.observation)
                ),
                blocks_when_idle=True,
            ),
            handler(
                "support_overlay",
                self.battle.handle_battle_preparation,
                enabled=lambda context: self.battle.support_popup_visible(
                    context.observation
                ),
                blocks_when_idle=True,
            ),
            handler(
                "world_map",
                self.world_map.handle_world_map,
                enabled=lambda context: (self.state.run_mode == RunMode.VOLCANO
                                         or not self.state.collaboration.started),
            ),
            handler("startup", self.startup.handle),
            handler(
                "sparse_support_friend_request",
                lambda observation: (
                    self.friend.try_request_friend_for_sparse_support(observation)
                ),
                enabled=lambda context: not self.state.endgame.is_active,
            ),
            handler("battle_preparation", self.battle.handle_battle_preparation),
            handler("battle_result", self.battle.handle_battle_result),
            handler("battle_runtime", self.battle.handle_battle_runtime),
            # Business-owned confirmations have already had a chance to run.
            handler("generic_confirm", self.overlay.handle_confirm),
        ))

    def tick(self, context):
        if self.state.run_mode == RunMode.COLLABORATION:
            self.collaboration.resume_if_internal(context.observation)
        return self.router.tick(context)

    def handle_observation(self, observation):
        """Compatibility entry for tools that supply an OCR observation."""
        snapshot = ScreenSnapshot(
            observation,
            recognize_scene(observation),
            recognize_overlays(observation),
        )
        return self.tick(DecisionContext(self, snapshot)).handled

    def run_forever(self):
        AutomationEngine(self).run_forever()
