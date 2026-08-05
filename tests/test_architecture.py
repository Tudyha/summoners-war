import ast
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
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

    def test_tutorial_overlay_never_falls_back_to_panel_center(self):
        source = (ROOT / "vision/tutorial.py").read_text(encoding="utf-8")
        self.assertNotIn("return int(x + box_width / 2)", source)
        self.assertIn("frame = capture_fresh_image()", source)

    def test_forced_tutorial_arrow_preempts_home_default_action(self):
        source = (ROOT / "runner.py").read_text(encoding="utf-8")
        arrow_position = source.index(
            'handler("tutorial_arrow", self.tutorial.handle_yellow_arrow)'
        )
        home_position = source.index('                "home",')

        self.assertLess(arrow_position, home_position)

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

    def test_generic_promotion_x_accepts_dim_neutral_strokes(self):
        source = (ROOT / "vision/overlay.py").read_text(encoding="utf-8")
        self.assertIn("np.array([0, 0, 165]", source)
        self.assertIn("np.array([179, 100, 255]", source)
        self.assertIn("template_coverage < 0.70", source)
        self.assertIn("component_coverage < 0.28", source)


if __name__ == "__main__":
    unittest.main()
