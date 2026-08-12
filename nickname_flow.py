"""Nickname input flow handled through Android accessibility nodes."""

import time

from ascript.android import action
from ascript.android.node import Selector

from . import config


class NicknameFlowMixin(object):
    def handle_nickname(self):
        field_selector = Selector(mode=config.SELECTOR_MODE).id(
            config.NICKNAME_FIELD_ID
        )
        field = field_selector.find()
        if field is None:
            return False

        nickname = "LD" + str(int(time.time()))[-10:]
        action.input(nickname, selector=field_selector)
        time.sleep(0.5)
        done = Selector(mode=config.SELECTOR_MODE).id(
            config.NICKNAME_DONE_ID
        ).find()
        if done is None:
            print("[nickname] system Done button is missing")
            return True
        done.click()
        self.last_action_at = time.time()
        print("[nickname] entered {}".format(nickname))
        return True
