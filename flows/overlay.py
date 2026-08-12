"""Blocking overlay and generic confirmation flow."""

from .. import config
from ..core.run_state import RunMode
from ..core.scene_recognizer import summon_result_match
from ..vision.core import scale_point
from ..vision.collaboration import find_minigame_entrance_icon
from ..vision.overlay import find_top_right_close_button


class OverlayFlow(object):
    def __init__(self, state, actions):
        self.state = state
        self.actions = actions

    def handle_popups_and_tutorial_text(self, obs):
        # Activity artwork and titles rotate. The opt-out label is the stable
        # anchor shared by this startup card, so never identify it by content.
        if obs.contains("今日不再提示") or obs.contains("今日不再提"):
            self.actions.click_xy(
                "daily_notice_activity_close",
                "close activity popup beside daily notice option",
            )
            return True

        # The forced tutorial ten-summon is not the endgame light/dark result.
        # Own it before dialogue heuristics can mistake monster names and the
        # 50,000 price label for a speaker/body pair.
        if (
            not self.state.endgame.is_active
            and summon_result_match(obs) is not None
        ):
            confirms = obs.matching(
                lambda row: row["text"] in ("确认", "确队", "确趴")
            )
            if confirms:
                self.actions.click_row(
                    confirms[0],
                    "confirm tutorial ten-summon result",
                )
            else:
                self.actions.click_xy(
                    "tutorial_ten_summon_confirm",
                    "confirm tutorial ten-summon result",
                )
            return True

        if obs.contains("魔灵排序/搜索"):
            self.actions.click_xy(
                "monster_sort_search_confirm",
                "confirm monster sort/search detail settings",
            )
            return True

        # if obs.contains("好友魔灵") and not self.state.battle.checking_support_selection:
        #     self.actions.click_xy(
        #         "daily_notice_activity_close",
        #         "close activity popup beside daily notice option",
        #     )
        #     return True

        if obs.contains("是否关闭购买窗口"):
            close_confirms = obs.exact("是")
            if len(close_confirms) == 1:
                self.actions.click_row(
                    close_confirms[0],
                    "confirm closing limited purchase popup",
                )
            else:
                self.actions.click_xy(
                    "limited_purchase_close_confirm",
                    "confirm closing limited purchase popup",
                )
            return True

        purchase_closes = obs.exact("关闭")
        if obs.contains("购买道具") and len(purchase_closes) == 1:
            self.actions.click_row(purchase_closes[0], "close optional item purchase popup")
            return True

        if obs.contains("召唤纪念礼包") and obs.contains("限时商品"):
            self.actions.click_xy(
                "summon_commemorative_pack_close",
                "close summon commemorative pack popup",
            )
            return True

        review_later = obs.exact("下次再说")
        if obs.contains("现在就去评论") and len(review_later) == 1:
            self.actions.click_row(review_later[0], "dismiss post-summon review prompt")
            return True

        if obs.contains_all("加入Hive", "登录Hive享受更多游戏乐趣"):
            self.actions.click_xy("hive_join_close", "close Hive join popup")
            return True

        yes = obs.exact("是")
        if obs.contains_all("要用1,000", "魔力石购买吗") and len(yes) == 1:
            self.actions.click_row(yes[0], "confirm forced tutorial purchase")
            return True

        if obs.contains_all("完成任务后", "移动到该任务") and len(yes) == 1:
            self.actions.click_row(yes[0], "move to story unlock task")
            return True

        revive_prompt = obs.contains_all("失败", "是否现在复活")
        decline_revive = obs.matching(
            lambda row: row["text"] == "否"
            or (
                scale_point((573, 0))[0] <= row["x"] <= scale_point((843, 0))[0]
                and scale_point((0, 400))[1] <= row["y"] <= scale_point((0, 520))[1]
                and len(row["text"]) <= 2
            )
        )
        if revive_prompt:
            if len(decline_revive) == 1:
                self.actions.click_row(
                    decline_revive[0],
                    "decline crystal revive after defeat",
                )
            else:
                self.actions.click_xy(
                    "battle_revive_decline",
                    "decline crystal revive after defeat",
                )
            return True

        closes = obs.exact("关闭")
        if obs.contains("属性相生") and len(closes) == 1:
            self.actions.click_row(closes[0], "close attribute relationship guide")
            return True

        if obs.contains_all("技能信息", "战斗效果", "结束战斗"):
            self.actions.click_xy("pause_resume", "dismiss pause overlay")
            return True

        if obs.contains_all("选择要使用技能", "我军目标"):
            self.actions.click_xy("tutorial_ally", "select allied tutorial skill target")
            return True

        if obs.contains_all("联动通行证", "活动期间"):
            # The collaboration activity page itself carries both labels.
            # Once the dice entrance is visible, ownership switches to the
            # collaboration flow even if the normal story is still active.
            if (
                self.state.run_mode == RunMode.COLLABORATION
                and (
                    self.state.collaboration.started
                    or find_minigame_entrance_icon() is not None
                )
            ):
                return False
            self.actions.click_xy("event_close", "close event popup")
            return True

        if obs.contains_all("账号限定礼包商店", "仅此一次的机会"):
            self.actions.click_xy("account_limited_shop_close", "close account limited shop popup")
            return True

        if (
            obs.contains_all("阿美利亚", "通行证")
            or obs.contains_all("幸运通行证", "激活增益奖励")
        ):
            self.actions.click_xy(
                "lucky_pass_close",
                "close Amelia lucky pass popup",
            )
            return True

        if (
            obs.contains("限时出售")
            and obs.contains("特别商品")
            and (obs.contains("查看构成") or obs.contains("购买所有礼包"))
        ):
            self.actions.click_xy(
                "collaboration_package_close",
                "close collaboration commemorative package popup",
            )
            return True

        # MLKit may alternate between simplified `召唤` and traditional `召喚`.
        if obs.contains_all("欢迎特别奖励", "每天签到"):
            self.actions.click_xy("welcome_reward_close", "close welcome reward popup")
            return True

        if obs.contains("成长的第一步") and obs.contains("初级礼包"):
            popup_closes = obs.matching(
                lambda row: row["text"] in ("X", "×")
                and row["x"] >= scale_point((877, 0))[0]
                and row["y"] <= scale_point((0, 144))[1]
            )
            if len(popup_closes) == 1:
                self.actions.click_row(
                    popup_closes[0],
                    "close initial package popup",
                )
            else:
                self.actions.click_xy(
                    "welcome_reward_close",
                    "close initial package popup",
                )
            return True

        return False

    def handle_confirm(self, obs):
        for r in obs.matching(lambda row: row["text"] in ("确认", "是", "确队", "确趴", "确议")):
            self.actions.click_row(r, "confirm dialog")
            return True
        return False

    def handle_global_overlays(self, obs):
        """Resolve recognized blocking layers before any main-scene action."""

        # This is a known global modal, so its confirmation is safe before
        # scene routing. Unknown confirmation buttons are handled last.
        if obs.contains("全新地区开启") and self.handle_confirm(obs):
            return True

        # After an unexpected game restart, the game can automatically open
        # the mailbox during the normal story. Do not claim rewards or infer
        # endgame from it; close the full mailbox screen and resume the story.
        if (
            not self.state.endgame.is_active
            and obs.contains_all("礼物箱", "公会收件箱", "友情点数")
        ):
            self.actions.click_xy("inbox_close", "close auto-opened story inbox")
            return True

        # Promotion titles and artwork rotate. Generic purchase affordances
        # establish the page class; the click itself comes from visual X-shape
        # detection, not from any activity name or a per-event coordinate.
        promotion_markers = sum(
            1
            for text in ("礼包", "限时", "商品", "购买", "免费")
            if obs.contains(text)
        )
        if promotion_markers >= 3:
            promotion_close = find_top_right_close_button()
            if promotion_close is not None:
                self.actions.click_point(
                    promotion_close,
                    "close generic promotion overlay by visual X",
                )
                return True

        return self.handle_popups_and_tutorial_text(obs)
