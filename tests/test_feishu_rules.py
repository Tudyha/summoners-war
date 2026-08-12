import json
import unittest

from ._package import project_module


rules = project_module("core.feishu_rules")


def message(text, parent="result-message", sender="user", created="1"):
    return {
        "parent_id": parent,
        "create_time": created,
        "sender": {"sender_type": sender},
        "body": {"content": json.dumps({"text": text}, ensure_ascii=False)},
    }


class FeishuRulesTests(unittest.TestCase):
    def test_accepts_direct_stop_reply(self):
        self.assertEqual(
            "stop",
            rules.decision_from_messages([message("停止脚本")], "result-message"),
        )

    def test_accepts_direct_initialize_reply(self):
        self.assertEqual(
            "reset",
            rules.decision_from_messages([message("初始化数据，继续")], "result-message"),
        )

    def test_ignores_other_threads_and_bot_messages(self):
        items = [
            message("停止", parent="another-message"),
            message("初始化", sender="app"),
        ]
        self.assertIsNone(rules.decision_from_messages(items, "result-message"))

    def test_latest_valid_reply_wins(self):
        items = [
            message("停止", created="1"),
            message("初始化", created="2"),
        ]
        self.assertEqual(
            "reset",
            rules.decision_from_messages(items, "result-message"),
        )


if __name__ == "__main__":
    unittest.main()
