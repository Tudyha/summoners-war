"""Nickname input flow handled through Android accessibility nodes."""

import time

from .. import config
from ..core.run_state import NicknamePhase


class NicknameFlow(object):
    """Own nickname entry until the game-side confirmation has disappeared."""

    CONFIRM_TEXTS = ("确认", "确定", "确队", "确趴")

    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def _nickname(self):
        nickname = self.state.nickname
        if not nickname.value:
            nickname.value = "LD" + str(int(time.time()))[-10:]
        return nickname.value

    def _confirm_rows(self, obs):
        return obs.matching(lambda row: row["text"] in self.CONFIRM_TEXTS)

    def _submit_field(self, field):
        nickname = self.state.nickname
        _, done = self.actions.find_node_by_id(config.NICKNAME_DONE_ID)
        if done is None:
            print("[nickname] system Done button is missing")
            return False

        self.actions.click_node(done, "close nickname input and continue")
        nickname.phase = NicknamePhase.WAITING_CONFIRM
        nickname.submit_attempts += 1
        nickname.last_submit_at = time.time()
        print("[nickname] submitted {}; waiting for game confirmation".format(
            nickname.value
        ))
        return True

    def handle_field(self, obs=None):
        """Enter once, then reuse the same value if the input dialog persists."""
        field_selector, field = self.actions.find_node_by_id(
            config.NICKNAME_FIELD_ID
        )
        if field is None:
            return False

        nickname = self.state.nickname
        if nickname.completed:
            # A completed nickname flow cannot legitimately show an editable
            # nickname field again in the same account. Its reappearance is a
            # reliable lifecycle boundary after in-game initialization.
            nickname.reset()
            print("[nickname] new account nickname field detected; reset workflow")

        value = self._nickname()
        current_text = str(getattr(field, "text", "") or "")
        now = time.time()

        if nickname.phase == NicknamePhase.INACTIVE:
            self.actions.input_node(field, value)
            nickname.phase = NicknamePhase.TEXT_ENTERED
            nickname.input_attempts = 1
            nickname.last_input_at = now
            print("[nickname] entered {}; verifying field before submit".format(value))
            return True

        if nickname.phase == NicknamePhase.TEXT_ENTERED:
            if value not in current_text:
                if now - nickname.last_input_at >= config.NICKNAME_INPUT_RETRY_SECONDS:
                    if nickname.input_attempts < config.NICKNAME_MAX_ATTEMPTS:
                        self.actions.ime_clear()
                        self.actions.ime_input(value)
                        nickname.input_attempts += 1
                        nickname.last_input_at = now
                        print("[nickname] field verification failed; retrying {}".format(
                            value
                        ))
                        return True
                    # Some accessibility implementations keep a stale ``text``
                    # property even though IME input is visible on screen. The
                    # bounded fallback has already run, so continue with the
                    # same value instead of owning the workflow forever.
                    print("[nickname] field text stayed stale; submitting fallback value")
                    return self._submit_field(field)
                return False
            return self._submit_field(field)

        # The accessibility input can remain visible briefly after clicking
        # Done. Never generate or type another nickname in this state. Retry
        # only the closing action, at a bounded interval.
        if nickname.phase == NicknamePhase.WAITING_CONFIRM:
            if (
                now - nickname.last_submit_at
                >= config.NICKNAME_SUBMIT_RETRY_SECONDS
                and nickname.submit_attempts < config.NICKNAME_MAX_ATTEMPTS
            ):
                return self._submit_field(field)
            return False

        return False

    def handle_pending(self, obs):
        """Confirm the game-side nickname page before other visual handlers."""
        nickname = self.state.nickname
        if not nickname.is_active:
            return False

        now = time.time()
        confirm_rows = self._confirm_rows(obs)
        if confirm_rows:
            if (
                nickname.phase != NicknamePhase.CONFIRMING
                or (
                    now - nickname.last_confirm_at
                    >= config.NICKNAME_CONFIRM_RETRY_SECONDS
                    and nickname.confirm_attempts < config.NICKNAME_MAX_ATTEMPTS
                )
            ):
                self.actions.click_row(
                    confirm_rows[0],
                    "confirm submitted nickname",
                )
                nickname.phase = NicknamePhase.CONFIRMING
                nickname.confirm_attempts += 1
                nickname.last_confirm_at = now
                return True
            return False

        if (
            nickname.phase == NicknamePhase.CONFIRMING
            and now - nickname.last_confirm_at
            >= config.NICKNAME_CONFIRM_RETRY_SECONDS
        ):
            nickname.completed = True
            nickname.phase = NicknamePhase.INACTIVE
            print("[nickname] accepted {}".format(nickname.value))
            return False

        wait_started_at = nickname.last_submit_at or nickname.last_input_at
        if (
            wait_started_at
            and now - wait_started_at >= config.NICKNAME_WAIT_LOG_SECONDS
            and now - nickname.last_wait_log_at >= config.NICKNAME_WAIT_LOG_SECONDS
        ):
            print("[nickname] waiting for confirmation: {}".format(
                obs.compact_text()
            ))
            nickname.last_wait_log_at = now
        return False

    def handle(self, obs=None):
        """Compatibility entry retained for direct callers."""
        if self.handle_field(obs):
            return True
        if obs is not None:
            return self.handle_pending(obs)
        return False
