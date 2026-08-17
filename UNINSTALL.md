# Uninstall safely

Preview first:

```sh
./uninstall.sh --dry-run
```

Then remove the app:

```sh
./uninstall.sh
```

The script:

1. parses the existing Codex and Claude JSON before changing anything;
2. removes only handlers whose complete command exactly matches this install;
3. preserves unrelated settings and hook handlers;
4. saves private pre-uninstall copies of changed configuration;
5. unloads the exact user LaunchAgent and stops the exact app executable;
6. moves the app, support directory, and LaunchAgent to a dated folder in
   `~/.Trash` rather than permanently deleting them.

To also make macOS forget this app's Input Monitoring decision:

```sh
./uninstall.sh --reset-permission
```

Nothing is installed as root or as a system daemon. If the repository folder is
deleted before uninstalling, manually remove only commands containing the exact
installed path
`~/Library/Application Support/NuPhy CapsLock Agent Beacon/agent_beacon_hook.py`
from `~/.codex/hooks.json` and `~/.claude/settings.json`, then move these paths to
Trash:

- `~/Applications/NuPhy CapsLock Agent Beacon.app`
- `~/Library/Application Support/NuPhy CapsLock Agent Beacon`
- `~/Library/LaunchAgents/io.github.justintylerm.nuphy-capslock-agent-beacon.plist`
