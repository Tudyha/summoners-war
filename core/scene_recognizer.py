"""OCR-only main-scene recognition with explicit evidence."""

from .screen_model import Scene, SceneMatch
from .summon_rules import is_summon_ui_title


WORLD_MAP_NAMES = (
    "加仑丛林", "加仑A林", "西泽山", "卡菲勒遗址", "卡勒遗址",
    "卡詳勒遗址", "年勒遗址", "年勃遗址", "拉古恩雪山", "拉古息雪", "粒古息雪", "拉古思",
    "物古恩", "特拉恩丛林", "特拉恩从林", "特拉恩队林",
    "特拉恩A林", "夏依德尼遗址", "厦依德尼遗址", "复依德尼遗址", "塔摩勒沙漠",
    "塔摩勂沙漠", "保罗帕库斯遗址", "帕伊摩恩", "帕伊摩恩火山", "艾登丛林",
    "艾登从林", "佩伦古城", "里纳德山", "泽罗卡遗址",
)


def _present(observation, anchors):
    return [anchor for anchor in anchors if observation.contains(anchor)]


def world_map_match(observation):
    # The stage list is a foreground panel drawn over the world map. OCR still
    # sees map names and Task behind it, so positive world-map anchors alone
    # cannot establish ownership while this panel is open.
    if observation.contains("掉落信息") and observation.contains("难度"):
        return None

    stable = _present(
        observation,
        (
            "竞技场", "竟技场", "宽技场", "试炼之塔", "异界的缝隙",
            "塔尔塔洛斯迷宫", "混沌神殿", "决战之岛", "任务",
        ),
    )
    maps = _present(observation, WORLD_MAP_NAMES)
    matched = (
        (len(stable) >= 3 and len(maps) >= 1)
        or (len(stable) >= 2 and len(maps) >= 2)
        or (len(stable) >= 2 and len(maps) >= 3)
        or (len(maps) >= 3 and observation.contains("任务"))
    )
    if not matched:
        return None
    confidence = min(0.99, 0.55 + len(stable) * 0.07 + len(maps) * 0.04)
    return SceneMatch(Scene.WORLD_MAP, confidence, stable + maps)


def summon_ui_match(observation):
    """Recognize the Summonhenge UI without relying on one exact OCR title."""

    title_anchors = [
        text for text in observation.texts if is_summon_ui_title(text)
    ]
    if title_anchors:
        return SceneMatch(Scene.SUMMON, 0.98, title_anchors)

    summon_anchors = _present(
        observation,
        (
            "光明与黑暗",
            "光明和黑暗",
            "光明",
            "黑暗",
            "特别召唤",
            "特別召唤",
            "新魔灵概率提升",
            "召唤书",
            "召喚書",
        ),
    )
    has_summon_word = observation.contains("召唤") or observation.contains("召喚")
    if has_summon_word and len(summon_anchors) >= 2:
        return SceneMatch(
            Scene.SUMMON,
            min(0.96, 0.72 + len(summon_anchors) * 0.06),
            summon_anchors,
        )
    return None


def home_match(observation):
    nav_anchors = ("战斗", "魔灵", "任务", "社交", "商店")
    nav_hits = _present(observation, nav_anchors)
    home_anchors = _present(observation, ("召唤师之路", "收件"))
    has_nickname = any(text.startswith("LD") for text in observation.texts)
    current_layout = (
        observation.contains("召唤师之路")
        and observation.contains("收件")
        and (observation.contains("信息") or observation.contains("编辑"))
    )
    if not ((home_anchors or has_nickname) and (len(nav_hits) >= 4 or current_layout)):
        return None
    evidence = nav_hits + home_anchors
    if has_nickname:
        evidence.append("LD nickname")
    return SceneMatch(
        Scene.HOME,
        min(0.98, 0.70 + len(evidence) * 0.04),
        evidence,
    )


def home_visible(observation):
    return home_match(observation) is not None


def summon_result_match(observation):
    """Recognize the forced tutorial ten-summon result screen."""
    if not observation.contains("召唤结果"):
        return None
    result_anchors = _present(
        observation,
        ("10次特别", "十连召", "千连召"),
    )
    if not result_anchors:
        return None
    return SceneMatch(
        Scene.SUMMON_RESULT,
        0.99,
        ["召唤结果"] + result_anchors,
    )


def message_center_match(observation):
    """Recognize the full-screen news/activity center."""
    if not observation.contains("消息"):
        return None
    evidence = _present(
        observation,
        ("公告事项", "活动", "游戏引导", "世界竞技场锦标赛"),
    )
    if len(evidence) < 2:
        return None
    return SceneMatch(
        Scene.MESSAGE_CENTER,
        0.99,
        ["消息"] + evidence,
    )


def recognize_scene(observation):
    candidates = []

    world_map = world_map_match(observation)
    if world_map is not None:
        candidates.append(world_map)

    summon_ui = summon_ui_match(observation)
    if summon_ui is not None:
        candidates.append(summon_ui)

    summon_result = summon_result_match(observation)
    if summon_result is not None:
        candidates.append(summon_result)

    message_center = message_center_match(observation)
    if message_center is not None:
        candidates.append(message_center)

    home = home_match(observation)
    if home is not None:
        candidates.append(home)

    rules = (
        (Scene.SUPPORT_LIST, 0.98, ("好友魔灵",)),
        (Scene.BATTLE_RESULT, 0.90, ("胜利", "奖励")),
        (Scene.BATTLE_RESULT, 0.90, ("失败", "停止")),
        (Scene.STAGE_LIST, 0.90, ("掉落信息", "难度")),
        (Scene.BATTLE_PREPARATION, 0.90, ("开始战斗", "结束战斗")),
        (Scene.INBOX, 0.88, ("收件箱", "领取")),
        (Scene.STARTUP, 0.92, ("Google登录", "Hive登录")),
        (Scene.STARTUP, 0.92, ("游戏使用条款",)),
        (Scene.STARTUP, 0.88, ("选择服务器",)),
    )
    for scene, confidence, anchors in rules:
        evidence = _present(observation, anchors)
        if len(evidence) == len(anchors):
            candidates.append(SceneMatch(scene, confidence, evidence))

    if not candidates:
        return SceneMatch(Scene.UNKNOWN, 0.0, [])
    return max(candidates, key=lambda candidate: candidate.confidence)
