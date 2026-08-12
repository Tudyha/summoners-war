"""Configuration for the Summoners War reroll flow."""

GAME_PACKAGE = "com.com2us.smon.normal.freefull.google.kr.android.common"

# The automation is currently calibrated and supported only at 1080 x 720.
REFERENCE_WIDTH = 1080
REFERENCE_HEIGHT = 720

POLL_SECONDS = 0.3
UNKNOWN_LOG_SECONDS = 8.0
NICKNAME_INPUT_RETRY_SECONDS = 0.8
NICKNAME_SUBMIT_RETRY_SECONDS = 2.0
NICKNAME_CONFIRM_RETRY_SECONDS = 1.5
NICKNAME_WAIT_LOG_SECONDS = 6.0
NICKNAME_MAX_ATTEMPTS = 3
WORLD_MAP_MAX_SWIPES = 5
STAGE_LIST_MAX_SWIPES = 3
FRIEND_REQUESTS_PER_ROUND = 8
FRIEND_UI_POLL_SECONDS = 0.2
FRIEND_ACTION_SETTLE_SECONDS = 0.4
FRIEND_PROFILE_CLOSE_SECONDS = 0.6
FRIEND_UI_TIMEOUT_SECONDS = 6.0
SUMMON_SELECTION_SETTLE_SECONDS = 0.8
FEISHU_REPLY_POLL_SECONDS = 3.0
FIVE_STAR_REPLY_TIMEOUT_SECONDS = 5 * 60
AUTO_RESET_AFTER_NON_FIVE_STAR = True
YELLOW_ARROW_CLICK_OFFSET_Y = 40

OCR_CONFIDENCE = 0.35
SELECTOR_MODE = 2

# Self-drawn tutorial/help overlays that can be dismissed by tapping once.
# Add short stable fragments here when a new one-off guide blocks the flow.
GENERIC_TAP_TEXTS = [
    "攻击是否有利",
    "箭头颜色",
    "自动战斗时点击敌人,会造成很大伤害。",
    "清点击画面",
    "请点击画面",
    "技能信息",
    "可以查看首领魔灵的技能",
]

# Verified on the real device during the first tutorial.
POINTS = {
    "dialogue": (540, 656),
    "skill_1": (806, 656),
    "skill_2": (914, 656),
    "skill_3": (1022, 656),
    "tutorial_enemy": (570, 228),
    "boss_enemy": (506, 264),
    "tutorial_ally": (590, 500),
    "tutorial_popup": (540, 440),
    "pause_resume": (540, 360),
    "victory_continue": (540, 640),
    # Rune-detail popup shown over the victory result (self-drawn game UI).
    "victory_rune_close": (752, 193),
    "auto_battle": (199, 672),
    "auto_battle_guide": (540, 560),
    "event_close": (1042, 40),
    "collaboration_package_close": (1050, 120),
    "lucky_pass_close": (1050, 120),
    "welcome_reward_close": (961, 82),
    # Startup activity card: the close icon is on the same bottom row as
    # "今日不再提示". Verified at about (866, 563) on 1080x720.
    "daily_notice_activity_close": (866, 563),
    "limited_purchase_close_confirm": (442, 462),
    "account_limited_shop_close": (974, 76),
    "summon_commemorative_pack_close": (961, 104),
    # Verified on the 1080x720 "加入 Hive" guest-account popup.
    "hive_join_close": (814, 99),
    "terms_select_all": (327, 336),
    "terms_agree_start": (685, 536),
    # Recalibrated from the real 1080 x 720 server-selection screen. These are
    # fallbacks only; startup prefers the OCR text centres when they are found.
    "server_global": (428, 267),
    "server_confirm": (540, 592),
    # Top-left Task icon, verified at about (63, 170) on 1080x720.
    "home_quest": (62, 170),
    "home_battle": (607, 672),
    "story_question": (440, 202),
    "xize_map": (438, 240),
    "team_member_1": (209, 520),
    "team_member_2": (300, 520),
    "team_member_3": (391, 520),
    "team_member_4": (482, 520),
    "support_tab": (121, 520),
    "support_first": (236, 254),
    "support_confirm": (540, 592),
    # Self-drawn battle-preparation warnings verified on 1080x720.
    # Device (443,425) = left "Yes"; device (540,425) = centered confirm.
    "leader_skill_continue_yes": (442, 424),
    "used_support_warning_confirm": (540, 424),
    # Verified on Android-209's self-drawn "至少要安排一个魔灵" dialog.
    "at_least_one_monster_confirm": (540, 424),
    # Verified on the 1080x720 monster sort/search detail screen. The game UI
    # is self-drawn; device center is (540, 618).
    "monster_sort_search_confirm": (540, 618),
    "world_map_swipe_right": (978, 360),
    "world_map_swipe_left": (121, 360),
    # Scroll only inside the right-side story stage panel. On 1080x720 this
    # becomes (800,560) -> (800,300), revealing stages 5-7 below the fold.
    "stage_list_scroll_start": (799, 560),
    "stage_list_scroll_end": (799, 300),
    # Verified on the battle-preparation screen chat overlay.
    "chat_open": (37, 28),
    "chat_close": (1035, 48),
    # Recalibrated from the real 1080x720 player-profile overlay.
    "player_profile_close": (978, 112),
    "friend_request": (189, 510),
    "friend_request_confirm": (540, 424),
    # Left-side "是" on the chat battle-result resend prompt.
    "battle_result_resend_yes": (444, 424),
    # Battle-defeat crystal-revive prompt. The right-side "No" button was
    # verified at device (701,454) on 1080x720; OCR rendered it as "香".
    "battle_revive_decline": (701, 454),
    "inbox": (62, 394),
    "inbox_close": (973, 143),
    "inbox_claim_all": (853, 164),
    "inbox_claim_confirm": (427, 611),
    "inbox_empty_claim_confirm": (540, 436),
    # Frieren collaboration activity and dice minigame, verified on Android-125.
    "collaboration_event": (1030, 348),
    "collaboration_minigame": (884, 558),
    "collaboration_collection": (234, 654),
    "collaboration_collection_close": (947, 92),
    "collaboration_reward_claim": (805, 551),
    "collaboration_minigame_close": (1033, 56),
    "collaboration_game_prepare": (842, 651),
    "collaboration_game_start": (669, 594),
    "collaboration_roll": (968, 592),
    "collaboration_result_continue": (540, 400),
    "collaboration_skill": (137, 654),
    "collaboration_skill_health": (603, 295),
    "collaboration_skill_upgrade": (740, 549),
    "collaboration_shop_confirm": (540, 622),
    "home_summon": (806, 648),
    "summon_circle": (415, 448),
    "summon_enter": (816, 644),
    "summon_close": (1040, 99),
    "light_dark_scroll": (830, 320),
    "new_monster_rate_checkbox": (91, 539),
    "special_summon_button": (303, 632),
    # Right-side "No" on the insufficient summon-scroll shop prompt,
    # verified at device (637,425) on 1080x720.
    "summon_scroll_purchase_decline": (637, 424),
    "summon_result_confirm": (861, 550),
    # Verified on the 1080x720 tutorial ten-summon result.
    "tutorial_ten_summon_confirm": (666, 614),
    # Verified on the in-game settings reset flow.
    "game_settings_open": (58, 66),
    # Full-screen message/activity center opened from the home-side activity
    # icon. Verified device close center (1036,44) on 1080x720.
    "message_center_close": (1036, 44),
    "game_settings_options_tab": (461, 162),
    "game_init_open": (677, 544),
    "game_init_code_input": (540, 428),
    "game_init_keyboard_done": (931, 22),
    "game_init_confirm": (446, 504),
    # Verified reset route on the MuMu launcher/settings UI. The game UI is
    # self-drawn, but Android settings exposes stable OCR text; these points are
    # only used after matching the corresponding page text.
    "exit_game_yes": (351, 436),
    "launcher_settings": (371, 660),
    "settings_apps": (91, 160),
    "settings_recent_game": (114, 364),
    "app_info_storage": (87, 670),
    "storage_clear_data": (276, 425),
    "storage_clear_data_confirm": (774, 435),
}

# Reference-frame coordinates verified on Android-125. These are collections
# because the flow deliberately rotates through different slots/items/skills
# instead of repeating one action and missing diversity achievements.
COLLABORATION_PREPARE_SLOTS = (
    (230, 380), (315, 380), (230, 468),
    (315, 468), (230, 556), (315, 556),
)
COLLABORATION_PREPARE_ITEMS = (
    (484, 244), (576, 244), (668, 244), (760, 244), (852, 244),
    (484, 346), (576, 346),
)
COLLABORATION_PREPARE_ITEM_COUNTERS = (
    (484, 296), (576, 296), (668, 296), (760, 296), (852, 296),
    (484, 397), (576, 397),
)
COLLABORATION_SKILLS = (
    ((224, 184), 20), ((350, 184), 20), ((476, 184), 50),
    ((602, 184), 50), ((728, 184), 50), ((854, 184), 50),
    ((224, 299), 50), ((350, 299), 50), ((476, 299), 100),
    ((602, 299), 30), ((728, 299), 500), ((854, 299), 70),
    ((224, 413), 50), ((350, 413), 300), ((476, 413), 50),
    ((602, 413), 50), ((728, 413), 100), ((854, 413), 200),
)
COLLABORATION_SHOP_UPGRADES = (
    ((490, 385), 10),
    ((585, 385), 10),
)

NICKNAME_FIELD_ID = (
    "com.com2us.smon.normal.freefull.google.kr.android.common:id/"
    "eedittext_input"
)
NICKNAME_DONE_ID = (
    "com.com2us.smon.normal.freefull.google.kr.android.common:id/btn_done"
)
