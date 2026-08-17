# Architecture

The project has three small pieces and no server.

```text
Codex / Claude hook event
          |
          v
agent_beacon_hook.py  -- routing-only marker -->  Application Support
                                                        |
                                                        v
Swift background app  -- one standard LED bit -->  exact Air75 V3 interface
```

## Hook bridge

`Hooks/agent_beacon_hook.py` receives the JSON event on standard input. It loads
that object in memory but persists only these allow-listed string fields:
`source`, `session_id`, `turn_id`, `tool_use_id`, and `tool_name`. Strings are
length-limited. Marker file names are SHA-256 hashes of that routing metadata.

The bridge creates approval markers for permission requests and interactive
questions, removes them after matching completion/failure/denial events, and
clears message markers on the next prompt. It launches the app through
`/usr/bin/open` with an argument array; it never invokes a shell with event data.

For Claude Code, the documented `Stop` event means the main agent finished
responding, so it enters the one-second foreground grace gate directly.

For Codex, Stop can occur before all visible work has settled. The gate uses the
official Stop payload's exact `transcript_path`, `session_id`, and `turn_id`. A
short-lived process scans newly available bytes for a line containing both the
matching turn ID and a `task_complete` record. It does not deserialize or retain
other transcript lines. The path must resolve inside `~/.codex`; traversal and
external paths are rejected. OpenAI documents the transcript format as unstable,
so this narrow detector may need maintenance after Codex updates.

Codex hooks receive `{}` on standard output. That is a valid no-decision result:
the beacon never approves, denies, blocks, or continues a workflow.

## State and foreground behavior

State lives under
`~/Library/Application Support/NuPhy CapsLock Agent Beacon`:

| Path | Contents |
| --- | --- |
| `requests/*.json` | Active approval/question routing markers |
| `pending-messages/*.json` | One-second final-message grace markers |
| `messages/*.json` | Background unseen-message routing markers |
| `terminal-gates/*` | Codex turn deduplication receipts |
| `events.log` | Routing-only diagnostics, rotated at 512 KiB |
| `pulse-timing.json` | Two bounded pulse durations |
| `backups/` | Private pre-install hook configuration copies |

Directories use mode `0700`; hook marker/config backup files use mode `0600`.
The Swift app asks `NSWorkspace` only for the frontmost application's bundle ID.
The Python grace worker asks Apple's local `lsappinfo` for the same identity. No
window titles, contents, notifications, or UI hierarchy are inspected.
Foreground matching is limited to the official Codex and Claude Desktop bundle
identifiers. In a CLI terminal, the next `UserPromptSubmit` clears the marker;
the project intentionally does not monitor terminal typing or windows.

## LED app

The Swift app reconnects to one of two narrowly identified interfaces:

- wired: the tested Air75 V3 keyboard interface and its one-bit, report-0 Caps
  Lock LED output element;
- Bluetooth: tested channel 1 (`Air75 V3-1`) and its report-6 Caps Lock LED
  output element.

While idle it performs no heartbeat write. During an alert it alternates the
inverse of the real logical Caps Lock state and the real state. When the alert
clears, startup occurs, or a connection fails, it restores the current logical
state whenever the device remains reachable.

## Installed paths

- `~/Applications/NuPhy CapsLock Agent Beacon.app`
- `~/Library/Application Support/NuPhy CapsLock Agent Beacon`
- `~/Library/LaunchAgents/io.github.justintylerm.nuphy-capslock-agent-beacon.plist`
- exact handlers merged into `~/.codex/hooks.json`
- exact handlers merged into `~/.claude/settings.json`

The LaunchAgent is a per-user login item with `RunAtLoad`; it is not a daemon,
does not use `KeepAlive`, and does not run as root.
