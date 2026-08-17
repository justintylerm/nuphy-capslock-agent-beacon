from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "Scripts/install.py"
UNINSTALL = ROOT / "Scripts/uninstall.py"


@unittest.skipUnless(sys.platform == "darwin", "macOS installer")
class InstallRoundTripTests(unittest.TestCase):
    def test_install_and_uninstall_preserve_unrelated_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            fake_app = root / "fixture.app"
            fake_app.mkdir(parents=True)
            (fake_app / "fixture").write_text("safe", encoding="utf-8")
            codex_config = home / ".codex/hooks.json"
            claude_config = home / ".claude/settings.json"
            codex_config.parent.mkdir(parents=True)
            claude_config.parent.mkdir(parents=True)
            original_codex = {
                "other": 1,
                "hooks": {"Stop": [{"hooks": [{"command": "keep-codex"}]}]},
            }
            original_claude = {
                "other": 2,
                "hooks": {"Stop": [{"hooks": [{"command": "keep-claude"}]}]},
            }
            codex_config.write_text(json.dumps(original_codex), encoding="utf-8")
            claude_config.write_text(json.dumps(original_claude), encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "NUPHY_AGENT_BEACON_HOME": str(home),
                    "NUPHY_AGENT_BEACON_SKIP_BUILD": "1",
                    "NUPHY_AGENT_BEACON_BUILT_APP": str(fake_app),
                    "NUPHY_AGENT_BEACON_SKIP_LAUNCH": "1",
                }
            )

            subprocess.run(
                [sys.executable, str(INSTALL), "--codex", "--claude"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            installed_codex = json.loads(codex_config.read_text(encoding="utf-8"))
            installed_claude = json.loads(claude_config.read_text(encoding="utf-8"))
            self.assertEqual(installed_codex["other"], 1)
            self.assertEqual(installed_claude["other"], 2)
            self.assertIn("agent_beacon_hook.py", str(installed_codex))
            self.assertTrue(
                (home / "Applications/NuPhy CapsLock Agent Beacon.app").is_dir()
            )

            subprocess.run(
                [sys.executable, str(UNINSTALL)],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                json.loads(codex_config.read_text(encoding="utf-8")),
                original_codex,
            )
            self.assertEqual(
                json.loads(claude_config.read_text(encoding="utf-8")),
                original_claude,
            )
            self.assertFalse(
                (home / "Applications/NuPhy CapsLock Agent Beacon.app").exists()
            )
            self.assertEqual(len(list((home / ".Trash").iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
