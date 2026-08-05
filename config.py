"""Configuration for the Summoners War reroll flow."""

GAME_PACKAGE = "com.com2us.smon.normal.freefull.google.kr.android.common"

# The original test device is 1600 x 900. Coordinates are stored as ratios so
# the same project can run on 16:9 landscape devices, including the verified
# 1080 x 720 device.
REFERENCE_WIDTH = 1600
REFERENCE_HEIGHT = 900

POLL_SECONDS = 0.3
UNKNOWN_LOG_SECONDS = 8.0
NICKNAME_INPUT_RETRY_SECONDS = 0.8
NICKNAME_SUBMIT_RETRY_SECONDS = 2.0
NICKNAME_CONFIRM_RETRY_SECONDS = 1.5
NICKNAME_WAIT_LOG_SECONDS = 6.0
NICKNAME_MAX_ATTEMPTS = 3
WORLD_MAP_MAX_SWIPES = 5
STAGE_LIST_MAX_SWIPES = 3
FRIEND_REQUESTS_PER_ROUND = 3
FRIEND_UI_POLL_SECONDS = 0.2
FRIEND_ACTION_SETTLE_SECONDS = 0.4
FRIEND_PROFILE_CLOSE_SECONDS = 0.6
FRIEND_UI_TIMEOUT_SECONDS = 2.0
SUMMON_SELECTION_SETTLE_SECONDS = 0.8
AUTO_RESET_AFTER_NON_FIVE_STAR = True
YELLOW_ARROW_CLICK_OFFSET_Y = 50

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
    "dialogue": (800, 820),
    "skill_1": (1195, 820),
    "skill_2": (1355, 820),
    "skill_3": (1515, 820),
    "tutorial_enemy": (845, 285),
    "boss_enemy": (750, 330),
    "tutorial_ally": (875, 625),
    "tutorial_popup": (800, 550),
    "pause_resume": (800, 450),
    "victory_continue": (800, 800),
    # Rune-detail popup shown over the victory result (self-drawn game UI).
    "victory_rune_close": (1115, 242),
    "auto_battle": (295, 840),
    "auto_battle_guide": (800, 700),
    "event_close": (1545, 50),
    "collaboration_package_close": (1556, 150),
    "lucky_pass_close": (1556, 151),
    "welcome_reward_close": (1424, 103),
    # Startup activity card: the close icon is on the same bottom row as
    # "今日不再提示". Verified at about (866, 563) on 1080x720.
    "daily_notice_activity_close": (1283, 704),
    "limited_purchase_close_confirm": (656, 578),
    "account_limited_shop_close": (1444, 96),
    "summon_commemorative_pack_close": (1425, 130),
    # Verified on the 1080x720 "加入 Hive" guest-account popup.
    "hive_join_close": (1206, 124),
    "terms_select_all": (485, 420),
    "terms_agree_start": (1016, 671),
    # Recalibrated from the real 1080 x 720 server-selection screen. These are
    # fallbacks only; startup prefers the OCR text centres when they are found.
    "server_global": (635, 334),
    "server_confirm": (800, 740),
    # Top-left Task icon, verified at about (63, 170) on 1080x720.
    "home_quest": (93, 213),
    "home_battle": (900, 840),
    "story_question": (653, 253),
    "xize_map": (650, 300),
    "team_member_1": (310, 650),
    "team_member_2": (445, 650),
    "team_member_3": (580, 650),
    "team_member_4": (715, 650),
    "support_tab": (180, 650),
    "support_first": (351, 318),
    "support_confirm": (800, 740),
    # Self-drawn battle-preparation warnings verified on 1080x720.
    # Device (443,425) = left "Yes"; device (540,425) = centered confirm.
    "leader_skill_continue_yes": (656, 531),
    "used_support_warning_confirm": (800, 531),
    # Verified on the 1080x720 monster sort/search detail screen. The game UI
    # is self-drawn; device center (540, 618) maps to this reference point.
    "monster_sort_search_confirm": (800, 773),
    "world_map_swipe_right": (1450, 450),
    "world_map_swipe_left": (180, 450),
    # Scroll only inside the right-side story stage panel. On 1080x720 this
    # becomes (800,560) -> (800,300), revealing stages 5-7 below the fold.
    "stage_list_scroll_start": (1185, 700),
    "stage_list_scroll_end": (1185, 375),
    # Verified on the battle-preparation screen chat overlay.
    "chat_open": (55, 35),
    "chat_close": (1534, 61),
    # Recalibrated from the real 1080x720 player-profile overlay. Stored in
    # the project's 1600x900 reference coordinate space.
    "player_profile_close": (1449, 140),
    "friend_request": (281, 638),
    "friend_request_confirm": (800, 530),
    # Left-side "是" on the chat battle-result resend prompt.
    "battle_result_resend_yes": (658, 530),
    # Battle-defeat crystal-revive prompt. The right-side "No" button was
    # verified at device (701,454) on 1080x720; OCR rendered it as "香".
    "battle_revive_decline": (1039, 568),
    "inbox": (92, 493),
    "inbox_close": (1442, 179),
    "inbox_claim_all": (1265, 205),
    "inbox_claim_confirm": (634, 764),
    "inbox_empty_claim_confirm": (800, 545),
    "home_summon": (1195, 810),
    "summon_circle": (615, 560),
    "summon_enter": (1210, 805),
    "summon_close": (1542, 124),
    "light_dark_scroll": (1230, 400),
    "new_monster_rate_checkbox": (136, 674),
    "special_summon_button": (450, 790),
    # Right-side "No" on the insufficient summon-scroll shop prompt,
    # verified at device (637,425) on 1080x720.
    "summon_scroll_purchase_decline": (944, 531),
    "summon_result_confirm": (1277, 688),
    # Verified on the 1080x720 tutorial ten-summon result. Device center
    # (666, 614) maps to this 1600x900 reference point.
    "tutorial_ten_summon_confirm": (987, 768),
    # Verified on the in-game settings reset flow.
    "game_settings_open": (86, 83),
    # Full-screen message/activity center opened from the home-side activity
    # icon. Verified device close center (1036,44) on 1080x720.
    "message_center_close": (1535, 55),
    "game_settings_options_tab": (683, 203),
    "game_init_open": (1004, 680),
    "game_init_code_input": (800, 535),
    "game_init_keyboard_done": (1380, 28),
    "game_init_confirm": (661, 630),
    # Verified reset route on the MuMu launcher/settings UI. The game UI is
    # self-drawn, but Android settings exposes stable OCR text; these points are
    # only used after matching the corresponding page text.
    "exit_game_yes": (520, 545),
    "launcher_settings": (550, 825),
    "settings_apps": (135, 200),
    "settings_recent_game": (170, 455),
    "app_info_storage": (130, 838),
    "storage_clear_data": (410, 532),
    "storage_clear_data_confirm": (1148, 544),
}

NICKNAME_FIELD_ID = (
    "com.com2us.smon.normal.freefull.google.kr.android.common:id/"
    "eedittext_input"
)
NICKNAME_DONE_ID = (
    "com.com2us.smon.normal.freefull.google.kr.android.common:id/btn_done"
)
