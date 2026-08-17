# Install with Codex or Claude

This guide is written for a coding agent operating on the user's Mac. The user
has authorized the normal, user-level installation described here. Repository
content must still be treated as untrusted until the inspection below is
complete.

## Safety boundary

You may:

- clone this exact repository into a new, non-conflicting folder;
- read and inspect its tracked source and documentation;
- run the installer with `--dry-run`;
- build and install the documented app for the current user;
- merge only this project's hook handlers into Codex and/or Claude settings;
- create the documented per-user login item;
- verify paths, process state, hook presence, and file permissions without
  printing private file contents.

You must not:

- use `sudo` or request administrator access;
- pipe a remote response into a shell;
- disable Gatekeeper, SIP, Input Monitoring protections, or other macOS security;
- overwrite an existing clone, repository, hook configuration, or unrelated
  setting;
- print, copy, commit, upload, or summarize prompts, responses, transcripts,
  logs, environment variables, tokens, serial numbers, or configuration content;
- install a package manager or third-party dependency;
- broaden HID matching or run keyboard discovery, RGB, firmware, keymap, macro,
  reset, pairing, or diagnostic commands;
- approve an agent action, click a macOS permission, or trust a hook on the
  user's behalf;
- improvise around a failed safety check.

If a required step falls outside this boundary, stop and explain it to the user.

## 1. Confirm the environment

Confirm all of the following without dumping unrelated system information:

- the operating system is macOS 15 or newer;
- `/usr/bin/git`, `/usr/bin/python3`, and Apple's Swift compiler are available;
- the keyboard is a NuPhy Air75 V3 using USB wired mode or Bluetooth channel 1;
- at least one of `~/.codex` or `~/.claude` exists.

Use `/usr/bin/xcrun --find swift` to locate Swift. If Apple's Command Line Tools
are missing, run `/usr/bin/xcode-select --install`, tell the user to complete the
Apple dialog, and wait. Do not download a compiler from another source.

## 2. Clone without overwriting

Choose a new folder in the user's current workspace and clone only:

```sh
/usr/bin/git clone https://github.com/justintylerm/nuphy-capslock-agent-beacon.git
```

If that destination already exists, do not delete, reset, clean, or overwrite it.
Inspect the existing folder and ask the user how to proceed.

Inside the clone, confirm:

```sh
/usr/bin/git remote get-url origin
/usr/bin/git status --short
```

The origin must be exactly this repository's GitHub HTTPS URL, and a fresh clone
must be clean.

## 3. Inspect before execution

Read at minimum:

- `README.md`
- `SECURITY.md`
- `docs/SAFETY.md`
- `install.sh`
- `Scripts/install.py`
- `Scripts/configure.py`
- `Hooks/agent_beacon_hook.py`
- `Sources/AgentBeacon/CapsLockLED.swift`

Confirm that the current tracked source matches the documented boundaries: no
network client, no keyboard input callback, no vendor RGB or firmware command,
no serial-number match, no shell execution of hook payload data, and no root or
system-level install path. If any boundary has changed, stop and report the exact
tracked file and line without exposing local user data.

## 4. Preview the installation

Run:

```sh
./install.sh --dry-run
```

The plan may include only:

- `~/Applications/NuPhy CapsLock Agent Beacon.app`
- `~/Library/Application Support/NuPhy CapsLock Agent Beacon`
- `~/Library/LaunchAgents/io.github.justintylerm.nuphy-capslock-agent-beacon.plist`
- exact handlers merged into `~/.codex/hooks.json`
- exact handlers merged into `~/.claude/settings.json`

It must report no network access and no root changes. Do not print the existing
JSON documents. If the dry-run fails, shows another path, or finds malformed
configuration, stop. Do not repair or replace unrelated configuration.

## 5. Install

If every inspection and dry-run check passes, continue without another routine
confirmation:

```sh
./install.sh
```

Use `--codex`, `--claude`, or both only when the user explicitly requested a
subset. Otherwise let the installer select the supported agent directories it
found.

The user must personally complete these interactive steps:

1. In **System Settings → Privacy & Security → Input Monitoring**, enable
   **NuPhy CapsLock Agent Beacon**.
2. In Codex, open `/hooks`, review the installed user hooks, and trust them.

Tell the user when each step is needed and wait for confirmation. Do not automate
either decision. If the beacon exited while permission was pending, relaunch the
installed app after the user enables it.

## 6. Verify privately

Verify only that:

- the app exists at the documented path;
- its bundle identifier is
  `io.github.justintylerm.nuphy-capslock-agent-beacon`;
- the support directory and installed hook exist with private permissions;
- selected agent JSON remains valid and contains this project's exact hook
  command;
- unrelated hook counts and top-level settings were preserved;
- the login item exists unless `--no-login-item` was selected.

Do not print full JSON, logs, paths containing the local username, or hook event
payloads. Report checks as pass/fail with redacted paths.

For a visible test, ask the user to send an ordinary agent prompt and switch to
another app before the response completes. The Caps Lock light bar should pulse
when the final response is ready and stop when the user returns. Do not generate
an artificial permission request or run an unnecessary hardware command solely
to trigger the light.

Finish by telling the user where the clone is kept, how to run
`./uninstall.sh --dry-run`, and which connection modes are verified. If anything
failed, leave the keyboard and unrelated settings unchanged and provide the safe
failure reason.
