from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "Hooks/agent_beacon_hook.py"


def load_hook_module():
    spec = importlib.util.spec_from_file_location("agent_beacon_hook", HOOK)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookTests(unittest.TestCase):
    def test_task_complete_requires_matching_turn(self) -> None:
        module = load_hook_module()
        with tempfile.TemporaryDirectory() as temporary:
            transcript = Path(temporary) / "rollout.jsonl"
            transcript.write_bytes(
                b'{"type":"task_complete","turn_id":"other"}\n'
                b'{"type":"assistant_message","turn_id":"wanted"}\n'
            )
            complete, offset = module.scan_task_complete(
                transcript, "wanted", 0
            )
            self.assertFalse(complete)
            self.assertGreater(offset, 0)
            with transcript.open("ab") as stream:
                stream.write(
                    b'{"type":"task_complete","turn_id":"wanted"}\n'
                )
            complete, _ = module.scan_task_complete(
                transcript, "wanted", offset
            )
            self.assertTrue(complete)

    def test_transcript_must_stay_inside_codex_directory(self) -> None:
        module = load_hook_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            codex = root / ".codex"
            codex.mkdir()
            inside = codex / "rollout.jsonl"
            outside = root / "private.jsonl"
            inside.write_text("", encoding="utf-8")
            outside.write_text("", encoding="utf-8")
            old = os.environ.get("NUPHY_AGENT_BEACON_CODEX_DIR")
            os.environ["NUPHY_AGENT_BEACON_CODEX_DIR"] = str(codex)
            try:
                self.assertEqual(
                    module.validated_transcript(
                        {"transcript_path": str(inside)}
                    ),
                    inside.resolve(),
                )
                self.assertIsNone(
                    module.validated_transcript(
                        {"transcript_path": str(outside)}
                    )
                )
            finally:
                if old is None:
                    os.environ.pop("NUPHY_AGENT_BEACON_CODEX_DIR", None)
                else:
                    os.environ["NUPHY_AGENT_BEACON_CODEX_DIR"] = old

    def test_event_persists_routing_only_and_never_decides(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            env = os.environ.copy()
            env.update(
                {
                    "NUPHY_AGENT_BEACON_STATE_DIR": str(state),
                    "NUPHY_AGENT_BEACON_APP_PATH": str(root / "missing.app"),
                }
            )
            payload = {
                "hook_event_name": "PermissionRequest",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "tool_name": "shell",
                "tool_input": {"secret": "DO_NOT_STORE"},
                "prompt": "DO_NOT_STORE",
            }
            result = subprocess.run(
                [sys.executable, str(HOOK), "event", "codex"],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertEqual(result.stdout.strip(), "{}")
            markers = list((state / "requests").glob("*.json"))
            self.assertEqual(len(markers), 1)
            stored = markers[0].read_text(encoding="utf-8")
            self.assertNotIn("DO_NOT_STORE", stored)
            self.assertNotIn("tool_input", stored)
            self.assertEqual(markers[0].stat().st_mode & 0o777, 0o600)

            clear = {
                "hook_event_name": "UserPromptSubmit",
                "session_id": "session-1",
            }
            subprocess.run(
                [sys.executable, str(HOOK), "event", "codex"],
                input=json.dumps(clear),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertEqual(list((state / "requests").glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
