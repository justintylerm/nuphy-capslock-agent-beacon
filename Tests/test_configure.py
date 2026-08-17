from __future__ import annotations

import sys
from pathlib import Path
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

from configure import merge_hooks, remove_hooks  # noqa: E402


class ConfigureTests(unittest.TestCase):
    def test_merge_is_idempotent_and_preserves_other_settings(self) -> None:
        command = '/usr/bin/python3 "/safe/hook.py" event codex'
        original = {
            "theme": "dark",
            "hooks": {
                "Stop": [
                    {
                        "matcher": "existing",
                        "hooks": [{"type": "command", "command": "other"}],
                    }
                ]
            },
        }
        once = merge_hooks(original, "codex", command)
        twice = merge_hooks(once, "codex", command)

        self.assertEqual(once, twice)
        self.assertEqual(original["theme"], once["theme"])
        self.assertEqual(
            original["hooks"]["Stop"][0], once["hooks"]["Stop"][0]
        )
        for groups in once["hooks"].values():
            matching = [
                handler
                for group in groups
                if isinstance(group, dict)
                for handler in group.get("hooks", [])
                if handler.get("command") == command
            ]
            self.assertLessEqual(len(matching), 1)

    def test_remove_deletes_only_exact_command(self) -> None:
        command = '/usr/bin/python3 "/safe/hook.py" event claude'
        document = merge_hooks(
            {"hooks": {"Stop": [{"hooks": [{"command": "other"}]}]}},
            "claude",
            command,
        )
        removed = remove_hooks(document, command)

        self.assertEqual(
            removed["hooks"]["Stop"], [{"hooks": [{"command": "other"}]}]
        )
        self.assertNotIn(command, str(removed))

    def test_invalid_existing_hook_shape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            merge_hooks({"hooks": []}, "codex", "command")
        with self.assertRaises(ValueError):
            merge_hooks({"hooks": {"Stop": {}}}, "codex", "command")

    def test_merge_repairs_own_stale_matcher_only(self) -> None:
        command = '/usr/bin/python3 "/safe/hook.py" event codex'
        document = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "wrong", "hooks": [{"command": command}]},
                    {"matcher": "keep", "hooks": [{"command": "other"}]},
                ]
            }
        }
        merged = merge_hooks(document, "codex", command)
        pre_tool = merged["hooks"]["PreToolUse"]
        self.assertIn(
            {"matcher": "keep", "hooks": [{"command": "other"}]}, pre_tool
        )
        own = [
            group
            for group in pre_tool
            if any(
                handler.get("command") == command
                for handler in group.get("hooks", [])
            )
        ]
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]["matcher"], "^request_user_input$")


if __name__ == "__main__":
    unittest.main()
