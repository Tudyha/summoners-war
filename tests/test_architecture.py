import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_collaboration_gameplay_vetoes_dialogue_detection(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8-sig")
        dialogue_source = source.split("def dialogue_present", 1)[1]

        self.assertIn("is_gameplay_screen(observation.texts)", dialogue_source)
        self.assertIn("return False", dialogue_source)

    def test_full_width_page_footer_cannot_be_dialogue_body(self):
        tutorial = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8-sig")
        dialogue_source = tutorial.split("def dialogue_present", 1)[1]

        self.assertNotIn('observation.contains("联动通行证")', dialogue_source)
        self.assertIn("int(right) <= int(width * 0.94)", dialogue_source)

    def test_battle_preparation_vetoes_dialogue_detection(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8-sig")
        dialogue_source = source.split("def dialogue_present", 1)[1]

        self.assertIn('observation.contains("开始战")', dialogue_source)
        self.assertIn('observation.contains("对战")', dialogue_source)

    def test_world_map_new_area_defines_its_area_scale(self):
        tree = self._tree("vision/map.py")
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "find_world_map_new_area"
        )
        assigned_names = {
            target.id
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        self.assertIn("area_scale", assigned_names)

    def test_summon_ui_is_never_treated_as_dialogue(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8-sig")

        dialogue_source = source.split("def dialogue_present", 1)[1]
        self.assertIn("is_summon_ui_title(text)", dialogue_source)
        self.assertIn("return False", dialogue_source)

    def test_endgame_declines_insufficient_scroll_purchase(self):
        source = (ROOT / "flows/endgame.py").read_text(encoding="utf-8-sig")

        self.assertIn('obs.contains("召唤书不足")', source)
        self.assertIn('"summon_scroll_purchase_decline"', source)

    def test_endgame_owner_advances_forced_dialogue(self):
        source = (ROOT / "flows/endgame.py").read_text(encoding="utf-8-sig")

        self.assertIn("dialogue_present(obs)", source)
        self.assertIn("advance NPC dialogue during endgame", source)

    def test_revive_decline_has_context_bound_ocr_fallback(self):
        source = (ROOT / "flows/overlay.py").read_text(encoding="utf-8-sig")

        self.assertIn('revive_prompt = obs.contains_all("失败", "是否现在复活")', source)
        self.assertIn('"battle_revive_decline"', source)

    def _tree(self, name):
        return ast.parse((ROOT / name).read_text(encoding="utf-8-sig"))

    def test_runner_uses_composition_without_mixins(self):
        tree = self._tree("runner.py")
        runner = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Runner"
        )

        self.assertEqual(["object"], [base.id for base in runner.bases])
        self.assertLess(len((ROOT / "runner.py").read_text(encoding="utf-8").splitlines()), 150)

    def test_flows_do_not_import_ascript_directly(self):
        flow_files = (
            "flows/startup.py",
            "flows/overlay.py",
            "flows/tutorial.py",
            "flows/world_map.py",
            "flows/battle.py",
            "flows/collaboration.py",
            "flows/home.py",
            "flows/friend.py",
            "flows/endgame.py",
            "flows/nickname.py",
        )
        for name in flow_files:
            with self.subTest(name=name):
                imports = []
                for node in self._tree(name).body:
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
                self.assertFalse(
                    any(module.startswith("ascript") for module in imports),
                    imports,
                )

    def test_vision_facade_contains_no_detector_implementation(self):
        tree = self._tree("vision/__init__.py")
        definitions = [
            node for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and getattr(node, "name", None) != "__getattr__"
        ]
        self.assertEqual([], definitions)

    def test_tutorial_overlay_supports_static_collaboration_guides(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8")
        self.assertIn("frame = capture_fresh_image()", source)
        self.assertIn("np.median(value) > 75", source)
        self.assertIn("dark_ratio < 0.48", source)
        self.assertIn("return int(x + box_width / 2)", source)

    def test_business_modals_and_footer_frames_veto_tutorial_overlay(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8")
        detector = source.split(
            "def find_tutorial_text_overlay", 1
        )[1].split("def _find_tutorial_ripple_motion", 1)[0]

        self.assertIn("bright_area >= width * height * 0.14", detector)
        self.assertIn("bright_width >= width * 0.40", detector)
        self.assertIn("bright_height >= height * 0.35", detector)
        self.assertIn("center_y <= height * 0.76", detector)

    def test_item_replacement_modal_vetoes_generic_tutorial_overlay(self):
        source = (ROOT / "flows/tutorial.py").read_text(encoding="utf-8")
        overlay_handler = source.split(
            "def handle_tutorial_overlay", 1
        )[1].split("def handle_dialogue", 1)[0]

        self.assertIn('obs.contains("请选择要更换的道具")', overlay_handler)
        self.assertIn(
            'obs.contains_all("游戏准备", "初始道具")',
            overlay_handler,
        )
        self.assertIn("return False", overlay_handler)

    def test_forced_tutorial_arrow_preempts_home_default_action(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        arrow_position = source.index(
            'handler("tutorial_arrow", self.tutorial.handle_yellow_arrow)'
        )
        home_position = source.index('                "home",')

        self.assertLess(arrow_position, home_position)

    def test_collaboration_activity_page_is_not_closed_after_entry(self):
        source = (ROOT / "flows/overlay.py").read_text(encoding="utf-8")
        event_rule = source.split(
            'if obs.contains_all("联动通行证", "活动期间"):', 1
        )[1].split('self.actions.click_xy("event_close"', 1)[0]

        self.assertIn("self.state.run_mode == RunMode.COLLABORATION", event_rule)
        self.assertIn("self.state.collaboration.started", event_rule)
        self.assertIn("find_minigame_entrance_icon() is not None", event_rule)
        self.assertIn("return False", event_rule)

    def test_collaboration_mode_runs_story_until_dice_entrance_is_visible(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")

        self.assertIn("or self.collaboration.entrance_visible(", source)
        self.assertIn("context.observation", source)
        self.assertNotIn('context.observation.contains("联动活动")', source)
        self.assertGreaterEqual(
            source.count("or not self.state.collaboration.started"), 2
        )

    def test_account_reset_blocks_stale_collaboration_resume(self):
        endgame = (ROOT / "flows/endgame.py").read_text(encoding="utf-8")
        collaboration = (ROOT / "flows/collaboration.py").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "collaboration.reset(allow_internal_resume=False)",
            endgame,
        )
        self.assertIn("state.allow_internal_resume", collaboration)
        self.assertIn('obs.contains_all("联动通行证", "活动期间")', collaboration)

    def test_visual_tutorial_overlay_preempts_collaboration_owner(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        overlay_position = source.index(
            'handler("tutorial_overlay", self.tutorial.handle_tutorial_overlay)'
        )
        collaboration_position = source.index('                "collaboration",')

        self.assertLess(overlay_position, collaboration_position)

    def test_generic_guides_and_dialogue_preempt_collaboration_owner(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        collaboration_position = source.index('                "collaboration",')

        self.assertLess(
            source.index('                "generic_tutorial_text",'),
            collaboration_position,
        )
        self.assertLess(
            source.index('handler("dialogue", self.tutorial.handle_dialogue)'),
            collaboration_position,
        )

    def test_collaboration_dismisses_mission_complete_before_gameplay(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        overlay_position = source.index('mission_complete = obs.exact("任务完成")')
        gameplay_position = source.index("if self._gameplay_visible(obs):")

        self.assertLess(overlay_position, gameplay_position)
        self.assertIn('obs.contains("关卡")', source[overlay_position:gameplay_position])
        self.assertIn("self.actions.click_row(", source[overlay_position:gameplay_position])

    def test_collaboration_diversifies_achievement_actions(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")

        self.assertIn("COLLABORATION_SKILLS", source)
        self.assertIn("COLLABORATION_PREPARE_ITEMS", source)
        self.assertIn("COLLABORATION_SHOP_UPGRADES", source)
        self.assertIn("state.in_run = True", source)

    def test_collection_entry_prefers_ocr_after_footer_layout_update(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        home_handler = source.split(
            "if self._minigame_home_visible(obs):", 2
        )[-1].split("entrance_icon =", 1)[0]
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")

        self.assertIn('collection_rows = obs.exact("收集")', home_handler)
        self.assertIn("self.actions.click_row(", home_handler)
        self.assertIn('"collaboration_collection": (174, 694)', config_source)

    def test_skill_entry_prefers_ocr_after_footer_layout_update(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        home_handler = source.split(
            "if self._minigame_home_visible(obs):", 2
        )[-1].split("entrance_icon =", 1)[0]
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")

        self.assertIn('skill_rows = obs.exact("技能")', home_handler)
        self.assertIn("self.actions.click_row(", home_handler)
        self.assertIn('"collaboration_skill": (78, 695)', config_source)

    def test_collaboration_can_resume_from_an_internal_minigame_screen(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")

        self.assertIn("self.collaboration.resume_if_internal(context.observation)", source)

    def test_collaboration_dice_detector_keeps_internal_pip_contours(self):
        source = (ROOT / "vision/collaboration.py").read_text(encoding="utf-8")

        self.assertIn("cv2.RETR_LIST", source)
        self.assertNotIn("cv2.RETR_EXTERNAL", source)

    def test_item_replacement_screen_is_not_mistaken_for_minigame_home(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        prepare_detector = source.split("def _prepare_visible", 1)[1].split(
            "def _skill_visible", 1
        )[0]
        home_detector = source.split("def _minigame_home_visible", 1)[1].split(
            "def _event_page_visible", 1
        )[0]

        self.assertIn("请选择要更换的道具", prepare_detector)
        self.assertIn('obs.contains_all("最高记录", "游戏准备")', home_detector)
        self.assertNotIn('obs.contains("游戏准备")', home_detector)

    def test_item_replacement_is_verified_before_starting_the_run(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        prepare_handler = source.split("def _handle_prepare", 1)[1].split(
            "def _handle_shop", 1
        )[0]

        self.assertIn('state.prepare_step = "verify_new"', prepare_handler)
        self.assertIn("replacement was not accepted", prepare_handler)
        self.assertIn('state.prepare_step = "choose_new"', prepare_handler)

    def test_prepared_run_closes_replacement_modal_before_starting(self):
        source = (ROOT / "flows/collaboration.py").read_text(encoding="utf-8")
        prepare_handler = source.split("def _handle_prepare", 1)[1].split(
            "def _handle_shop", 1
        )[0]
        prepared_branch = prepare_handler.split(
            "if state.prepared_run == state.run_count:", 1
        )[1].split('if state.prepare_step == "select_old":', 1)[0]

        self.assertIn("replacement_modal_visible = (", prepared_branch)
        self.assertIn('obs.contains("取消")', prepared_branch)
        self.assertIn("(873, 594)", prepared_branch)
        self.assertIn('if not obs.contains("游戏开始"):', prepared_branch)
        self.assertLess(
            prepared_branch.index("if replacement_modal_visible:"),
            prepared_branch.index('"collaboration_game_start"'),
        )

    def test_sparse_support_friend_request_preempts_battle_start(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        friend_position = source.index('                "sparse_support_friend_request",')
        battle_position = source.index(
            'handler("battle_preparation", self.battle.handle_battle_preparation)'
        )

        self.assertLess(friend_position, battle_position)
        self.assertIn(
            "try_request_friend_for_sparse_support(observation)",
            source,
        )

        friend_source = (ROOT / "flows/friend.py").read_text(encoding="utf-8")
        method_source = friend_source.split(
            "    def try_request_friend_for_sparse_support",
            1,
        )[1].split("\n    def try_request_friend_from_chat", 1)[0]
        self.assertNotIn("battle_lower_left_controls_visible", method_source)
        self.assertIn('"开始战斗" in row["text"]', method_source)
        self.assertIn("if len(start_battles) != 1", method_source)

    def test_world_map_return_intent_does_not_require_all_home_labels(self):
        source = (ROOT / "flows/home.py").read_text(encoding="utf-8")
        return_branch = source.split(
            "if self.state.world_map.returning_home_for_task:",
            1,
        )[1].split("return True", 1)[0]

        self.assertNotIn("contains_all", return_branch)
        self.assertIn('click_xy("home_quest"', return_branch)

    def test_normal_and_failed_support_checks_share_one_policy(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        self.assertIn("def _handle_counted_support_list", source)
        self.assertIn(
            "if self.state.battle.needs_support_selection and self.support_popup_visible(obs):\n"
            "            self._handle_counted_support_list(obs)",
            source,
        )
        self.assertIn(
            "if self.state.battle.checking_support_selection and self.support_popup_visible(obs):\n"
            "            self._handle_counted_support_list(obs)",
            source,
        )

    def test_support_popup_reobservation_invalidates_previous_visual_frame(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        method_start = source.index("    def select_first_support_monster(self):")
        method_end = source.index("\n    def support_popup_visible", method_start)
        method_source = source[method_start:method_end]

        self.assertLess(
            method_source.index("begin_visual_frame()"),
            method_source.index("support_obs = observe()"),
        )

    def test_sparse_support_round_requests_three_distinct_players(self):
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")
        friend_source = (ROOT / "flows/friend.py").read_text(encoding="utf-8")

        self.assertIn("FRIEND_REQUESTS_PER_ROUND = 3", config_source)
        self.assertIn("attempted_names = set()", friend_source)
        self.assertIn("candidate_name in attempted_names", friend_source)
        self.assertIn("initiated_count >= config.FRIEND_REQUESTS_PER_ROUND", friend_source)

        one_player_source = friend_source.split(
            "    def _request_one_chat_player", 1
        )[1].split("\n    def try_request_friend_for_sparse_support", 1)[0]
        round_source = friend_source.split(
            "    def try_request_friend_for_sparse_support", 1
        )[1].split("\n    def try_request_friend_from_chat", 1)[0]
        self.assertNotIn("find_chat_open", one_player_source)
        self.assertNotIn("_close_chat_layers", one_player_source)
        self.assertIn("_return_to_open_chat", one_player_source)
        self.assertEqual(1, round_source.count("find_chat_open()"))
        self.assertEqual(1, round_source.count("_close_chat_layers("))
        self.assertNotIn("time.sleep(3.0)", friend_source)
        self.assertIn("def _wait_observation", friend_source)
        self.assertIn("FRIEND_UI_POLL_SECONDS = 0.2", config_source)
        self.assertIn("FRIEND_UI_TIMEOUT_SECONDS = 2.0", config_source)

    def test_friend_flow_supports_new_c_chat_entry_and_legacy_bubble(self):
        friend_source = (ROOT / "flows/friend.py").read_text(encoding="utf-8")
        round_source = friend_source.split(
            "    def try_request_friend_for_sparse_support", 1
        )[1].split("\n    def try_request_friend_from_chat", 1)[0]

        self.assertIn('row["text"].lstrip().startswith("C")', round_source)
        self.assertIn("self.actions.click_row(chat_rows[0]", round_source)
        self.assertEqual(1, round_source.count("find_chat_open()"))
        self.assertIn("chat entry not found in new or legacy style", round_source)

    def test_chat_candidates_survive_merged_message_body(self):
        source = (ROOT / "flows/friend.py").read_text(encoding="utf-8")
        candidate_source = source.split(
            "    def _chat_player_candidates", 1
        )[1].split("\n    def _chat_player_click_point", 1)[0]
        name_source = source.split(
            "    def _chat_player_name", 1
        )[1].split("\n    def _return_to_open_chat", 1)[0]

        self.assertNotIn('"开启了" in text', candidate_source)
        self.assertNotIn('"秘密地下城" in text', candidate_source)
        self.assertNotIn('"召唤出" in text', candidate_source)
        self.assertIn('player_name == "通知"', candidate_source)
        self.assertIn('text.find("【")', name_source)
        self.assertIn('text.find("(")', name_source)

    def test_battle_preparation_progress_does_not_depend_on_map_title_ocr(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")

        self.assertNotIn("filter_maps = [", source)
        self.assertIn('obs.contains("对战")', source)
        self.assertIn('obs.contains("开始战")', source)
        self.assertIn(
            '"start next-stage battle from verified preparation scene"',
            source,
        )

    def test_failed_battle_uses_sparse_available_support(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        policy_source = source.split(
            "    def _handle_counted_support_list", 1
        )[1].split("\n    def handle_battle_preparation", 1)[0]

        self.assertIn("self.state.battle.needs_support_selection", policy_source)
        self.assertIn("support_monster_count > 0", policy_source)
        self.assertIn(
            "support_monster_count >= 6 or failed_battle_requires_support",
            policy_source,
        )

    def test_stage_list_cannot_be_mistaken_for_dialogue(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8")
        dialogue_source = source.split("def dialogue_present", 1)[1]

        self.assertIn('observation.contains("掉落信息")', dialogue_source)
        self.assertIn('observation.contains("难度")', dialogue_source)

    def test_full_team_is_reduced_before_support_selection(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        remove_position = source.index(
            "if preparing_support and len(selected_team) == 4:"
        )
        support_position = source.index(
            'self.actions.click_xy("support_tab", "open support list to count selectable monsters")'
        )

        self.assertLess(remove_position, support_position)
        self.assertIn("find_selected_team_members", source)
        self.assertIn("if preparing_support and len(selected_team) == 4", source)
        self.assertIn("fourth_member = max(selected_team", source)

        detector_source = (ROOT / "vision/stage.py").read_text(encoding="utf-8")
        selected_detector = detector_source.split(
            "def find_selected_team_members", 1
        )[1].split("def find_highest_star_team_members", 1)[0]
        self.assertIn("card_roi.std()", selected_detector)
        self.assertIn("edge_density < 0.08", selected_detector)
        self.assertNotIn("box_width * box_height * 0.75", selected_detector)
        self.assertNotIn("contour_fill_ratio >= 0.20", selected_detector)
        self.assertIn('leader_placeholders = observation.exact("领队")', selected_detector)
        self.assertIn('row["x"]', selected_detector)
        self.assertIn('row["y"]', selected_detector)
        self.assertIn("int(width * 0.025)", selected_detector)
        self.assertIn("int(height * 0.035)", selected_detector)

        ranked_detector = detector_source.split(
            "def find_highest_star_team_members", 1
        )[1]
        self.assertIn("require_disabled_start=True", ranked_detector)
        self.assertIn('observation.contains("领袖")', ranked_detector)

    def test_full_formation_popup_recovers_without_losing_support_intent(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        handler = source.split(
            "    def handle_battle_preparation", 1
        )[1].split('        if obs.contains("至少要安排一个魔灵"):', 1)[0]

        self.assertIn('obs.contains("栏位中魔灵已满")', handler)
        self.assertIn("close full formation before support selection", handler)
        self.assertIn("self.state.battle.needs_support_selection = True", handler)
        self.assertIn("self.state.battle.checking_support_selection = False", handler)

    def test_empty_team_warning_rebuilds_the_formation(self):
        source = (ROOT / "flows/battle.py").read_text(encoding="utf-8")
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")

        popup_position = source.index('obs.contains("至少要安排一个魔灵")')
        leader_position = source.index("if self._leader_skill_warning_visible(obs):")
        self.assertLess(popup_position, leader_position)
        self.assertIn("at_least_one_monster_confirm", config_source)
        self.assertIn("needs_team_selection = True", source)
        self.assertIn("clear selected team before rebuilding formation", source)
        self.assertIn("require_disabled_start=False", source)
        self.assertIn("reselect {}-star story team member", source)

    def test_generic_promotion_x_accepts_dim_neutral_strokes(self):
        source = (ROOT / "vision/overlay.py").read_text(encoding="utf-8")
        self.assertIn("np.array([0, 0, 165]", source)
        self.assertIn("np.array([179, 100, 255]", source)
        self.assertIn("template_coverage < 0.70", source)
        self.assertIn("component_coverage < 0.28", source)

    def test_collaboration_scroll_detector_never_scans_between_rows(self):
        source = (ROOT / "vision/summon.py").read_text(encoding="utf-8")
        detector = source.split(
            "def find_collaboration_scroll_icon", 1
        )[1]

        self.assertIn("int(172 * scale_y)", detector)
        self.assertIn("int(258 * scale_y)", detector)
        self.assertNotIn("for center_y in range", detector)

    def test_summon_result_uses_visual_stars_and_real_operator_reply(self):
        endgame_source = (ROOT / "flows/endgame.py").read_text(encoding="utf-8")
        summon_source = (ROOT / "vision/summon.py").read_text(encoding="utf-8")

        self.assertIn("find_summon_result_star_count", summon_source)
        self.assertIn("cv2.bitwise_or(gold, purple)", summon_source)
        self.assertIn('text.count("★")', endgame_source)
        self.assertIn('{"25": 3, "30": 4, "35": 5}', endgame_source)
        self.assertIn("conflicting summon star evidence", endgame_source)
        self.assertIn("star_count is None", endgame_source)
        self.assertIn("if star_count == 5:", endgame_source)
        self.assertIn("FIVE_STAR_REPLY_TIMEOUT_SECONDS", endgame_source)
        self.assertIn("reply_wait_started_at", endgame_source)
        self.assertIn("phase = EndgamePhase.WAIT_FEISHU_REPLY", endgame_source)
        self.assertIn("if star_count in (3, 4):", endgame_source)
        self.assertIn("AUTO_RESET_AFTER_NON_FIVE_STAR", endgame_source)
        self.assertIn("self._begin_game_reset()", endgame_source)
        self.assertIn("decision, detail = poll_summon_decision", endgame_source)
        self.assertNotIn('decision = "reset"', endgame_source)

        reply_wait = endgame_source.split(
            "    def _handle_feishu_reply_wait", 1
        )[1].split("\n    def _reset_summon_search", 1)[0]
        self.assertLess(
            reply_wait.index("decision, detail = poll_summon_decision"),
            reply_wait.rindex("if five_star_timed_out:"),
        )
        self.assertLess(
            reply_wait.index('if detail != "ok":'),
            reply_wait.rindex("if five_star_timed_out:"),
        )

    def test_stop_states_exit_the_engine_instead_of_idling(self):
        engine_source = (ROOT / "core/engine.py").read_text(encoding="utf-8")
        stop_block = engine_source.split("        while True:", 1)[1].split(
            "            try:", 1
        )[0]

        self.assertIn("stop.requested_by_operator", stop_block)
        self.assertIn("stop.for_five_star", stop_block)
        self.assertIn("stop.before_reset", stop_block)
        self.assertEqual(3, stop_block.count("return"))
        self.assertNotIn("time.sleep", stop_block)


if __name__ == "__main__":
    unittest.main()
