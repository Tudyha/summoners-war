"""Recognize blocking layers independently from the underlying main scene."""

from .screen_model import Overlay, OverlayMatch


def leader_skill_warning_visible(observation):
    return (
        observation.contains("没有可使用的领袖技能")
    )


def used_support_warning_text_visible(observation):
    """Match only explicit used-support wording, never loose cross-row words."""
    return (
        observation.contains("已使用的魔灵")
        or observation.contains("已经使用过的魔灵")
        or observation.contains_all("已使用", "支援魔灵")
    )


def _evidence(observation, anchors):
    return [anchor for anchor in anchors if observation.contains(anchor)]


def recognize_overlays(observation):
    matches = []
    rules = (
        (Overlay.DAILY_ACTIVITY, 0.98, ("今日不再提示",), "global"),
        (Overlay.DAILY_ACTIVITY, 0.94, ("今日不再提",), "global"),
        (
            Overlay.PURCHASE_CLOSE_CONFIRM,
            0.99,
            ("是否关闭购买窗口",),
            "global",
        ),
        (Overlay.ITEM_PURCHASE, 0.94, ("购买道具", "关闭"), "global"),
        (
            Overlay.HIVE_JOIN,
            0.97,
            ("加入Hive", "登录Hive享受更多游戏乐趣"),
            "global",
        ),
        (Overlay.REVIVE, 0.98, ("失败", "是否现在复活"), "battle"),
        (
            Overlay.PAUSE,
            0.98,
            ("技能信息", "战斗效果", "结束战斗"),
            "battle",
        ),
        (Overlay.SUPPORT_LIST, 0.99, ("好友魔灵",), "battle"),
    )
    for overlay, confidence, anchors, owner in rules:
        evidence = _evidence(observation, anchors)
        if len(evidence) == len(anchors):
            matches.append(OverlayMatch(overlay, confidence, evidence, owner))

    promotion_evidence = _evidence(
        observation,
        ("礼包", "限时", "商品", "购买", "免费"),
    )
    if len(promotion_evidence) >= 2:
        matches.append(
            OverlayMatch(
                Overlay.PROMOTION,
                min(0.90, 0.60 + len(promotion_evidence) * 0.07),
                promotion_evidence,
                "global",
            )
        )
    return sorted(matches, key=lambda match: match.confidence, reverse=True)
