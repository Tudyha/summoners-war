"""Pure screen facts produced from one OCR observation."""

import time


class Scene(object):
    UNKNOWN = "unknown"
    STARTUP = "startup"
    HOME = "home"
    WORLD_MAP = "world_map"
    STAGE_LIST = "stage_list"
    BATTLE_PREPARATION = "battle_preparation"
    SUPPORT_LIST = "support_list"
    BATTLE_RESULT = "battle_result"
    SUMMON = "summon"
    SUMMON_RESULT = "summon_result"
    MESSAGE_CENTER = "message_center"
    INBOX = "inbox"


class Overlay(object):
    DAILY_ACTIVITY = "daily_activity"
    PURCHASE_CLOSE_CONFIRM = "purchase_close_confirm"
    ITEM_PURCHASE = "item_purchase"
    HIVE_JOIN = "hive_join"
    REVIVE = "revive"
    PAUSE = "pause"
    SUPPORT_LIST = "support_list"
    PROMOTION = "promotion"


class OverlayMatch(object):
    def __init__(self, overlay, confidence, evidence=None, owner="global"):
        self.overlay = overlay
        self.confidence = float(confidence)
        self.evidence = list(evidence or [])
        self.owner = owner


class SceneMatch(object):
    def __init__(self, scene, confidence, evidence=None):
        self.scene = scene
        self.confidence = float(confidence)
        self.evidence = list(evidence or [])


class ScreenSnapshot(object):
    """OCR and derived facts from a single decision tick."""

    def __init__(self, observation, scene_match, overlays=None, captured_at=None):
        self.observation = observation
        self.scene_match = scene_match
        self.overlays = list(overlays or [])
        self.captured_at = time.time() if captured_at is None else captured_at

    @property
    def scene(self):
        return self.scene_match.scene

    @property
    def has_blocking_overlay(self):
        return bool(self.overlays)


class DecisionContext(object):
    def __init__(self, runner, snapshot):
        self.runner = runner
        self.snapshot = snapshot
        self.state = runner.state

    @property
    def observation(self):
        return self.snapshot.observation
