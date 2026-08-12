"""Explicit runtime state grouped by workflow responsibility."""


class RuntimeState(object):
    def __init__(self):
        self.last_action_at = 0.0
        self.last_unknown_log_at = 0.0
        self.last_scene = None
        self.last_behavior = None
        self.consecutive_errors = 0


class FriendState(object):
    def __init__(self):
        self.last_request_at = 0.0
        self.requests_disabled = False
        self.candidate_cursor = 0
        self.attempted_for_preparation = False

    def should_request_for_support(self, battle):
        return (
            not self.requests_disabled
            and not self.attempted_for_preparation
            and battle.support_count_checked_for_preparation
            and battle.support_monster_count < 6
        )


class BattleState(object):
    def __init__(self):
        self.needs_team_selection = False
        self.needs_support_selection = False
        self.checking_support_selection = False
        self.support_checked = False
        self.support_first_unavailable = False
        self.support_monster_count = 0
        self.support_count_checked_for_preparation = False
        self.stage_list_scroll_count = 0


class WorldMapState(object):
    def __init__(self):
        self.miss_count = 0
        self.returning_home_for_task = False


class NicknamePhase(object):
    INACTIVE = "inactive"
    TEXT_ENTERED = "text_entered"
    WAITING_CONFIRM = "waiting_confirm"
    CONFIRMING = "confirming"


class NicknameState(object):
    def __init__(self):
        self.reset()

    def reset(self):
        """Clear all per-account nickname workflow state."""
        self.phase = NicknamePhase.INACTIVE
        self.value = ""
        self.input_attempts = 0
        self.submit_attempts = 0
        self.confirm_attempts = 0
        self.last_input_at = 0.0
        self.last_submit_at = 0.0
        self.last_confirm_at = 0.0
        self.last_wait_log_at = 0.0
        self.completed = False

    @property
    def is_active(self):
        return self.phase != NicknamePhase.INACTIVE


class EndgamePhase(object):
    INACTIVE = "inactive"
    SUMMON = "summon"
    WAIT_FEISHU_REPLY = "wait_feishu_reply"
    RESET = "reset"
    RESET_CONFIRM = "reset_confirm"


class RunMode(object):
    VOLCANO = "volcano"
    COLLABORATION = "collaboration"


class SummonScrollKind(object):
    LIGHT_DARK = "light_dark"
    COLLABORATION = "collaboration"


class CollaborationPhase(object):
    OPEN_EVENT = "open_event"
    OPEN_MINIGAME = "open_minigame"
    PLAY = "play"
    CLAIM_ACHIEVEMENTS = "claim_achievements"
    RETURN_HOME = "return_home"
    COMPLETE = "complete"


class CollaborationState(object):
    def __init__(self):
        self.reset()

    def reset(self, allow_internal_resume=True):
        self.phase = CollaborationPhase.OPEN_EVENT
        self.achievement_count = 0
        self.reward_claim_attempts = 0
        self.run_count = 0
        self.roll_count = 0
        self.collection_checked_run = -1
        self.in_run = False
        self.skill_checked_run = -1
        self.skill_step = "select"
        self.maxed_skill_indices = set()
        self.pending_skill_index = None
        self.prepared_run = -1
        self.prepare_step = "select_old"
        self.replacement_slot_cursor = 0
        self.replacement_item_cursor = 0
        self.replacement_attempts = 0
        self.shop_step = "select"
        self.shop_completed = False
        self.shop_visit_count = 0
        self.shop_attempts = 0
        self.started = False
        # A fresh script may legitimately start inside the minigame. After an
        # account reset, however, one or more stale frames from the old account
        # can remain visible and must not immediately restore old ownership.
        self.allow_internal_resume = allow_internal_resume

    @property
    def is_complete(self):
        return self.phase == CollaborationPhase.COMPLETE


class EndgameState(object):
    def __init__(self):
        self.phase = EndgamePhase.INACTIVE
        self.inbox_claimed = False
        self.light_dark_selected = False
        self.scroll_kind = SummonScrollKind.LIGHT_DARK
        self.feishu_message_id = None
        self.feishu_sent_at = 0
        self.last_feishu_poll_at = 0
        self.last_feishu_send_at = 0
        self.reply_wait_started_at = 0
        self.summon_was_five_star = False
        self.summon_started = False
        self.entering_summon_circle = False
        self.summon_search_step = 0
        self.summon_rejected_points = []
        self.summon_probe_point = None

    @property
    def is_active(self):
        return self.phase != EndgamePhase.INACTIVE


class StopState(object):
    def __init__(self):
        self.for_five_star = False
        self.before_reset = False
        self.requested_by_operator = False


class RunnerState(object):
    """The complete mutable state of one automation run."""

    def __init__(self, run_mode=RunMode.VOLCANO):
        self.run_mode = run_mode
        self.runtime = RuntimeState()
        self.friend = FriendState()
        self.battle = BattleState()
        self.world_map = WorldMapState()
        self.nickname = NicknameState()
        self.endgame = EndgameState()
        self.collaboration = CollaborationState()
        self.stop = StopState()
