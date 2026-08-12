"""Pure parsing rules for Feishu endgame decisions."""

import json


def message_text(item):
    """Flatten text and post message JSON from one Feishu history item."""
    content = item.get("body", {}).get("content", "")
    try:
        content = json.loads(content)
    except (TypeError, ValueError):
        return str(content or "")

    pieces = []

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("text"), str):
                pieces.append(value["text"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(content)
    return " ".join(pieces)


def decision_from_messages(items, parent_message_id):
    """Return ``stop`` or ``reset`` from a direct human reply, if present."""
    ordered = sorted(
        items or [],
        key=lambda item: int(item.get("create_time") or 0),
        reverse=True,
    )
    for item in ordered:
        if item.get("parent_id") != parent_message_id:
            continue
        if item.get("sender", {}).get("sender_type") == "app":
            continue
        text = "".join(message_text(item).split()).lower()
        if "停止" in text or text in ("stop", "停止脚本"):
            return "stop"
        if "初始化" in text or "继续" in text or text in ("reset", "continue"):
            return "reset"
    return None
