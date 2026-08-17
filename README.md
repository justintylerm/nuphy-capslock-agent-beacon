# NuPhy Air75 V3 Caps Lock notification light for Codex and Claude Code

`nuphy-capslock-agent-beacon` turns the Caps Lock light bar on a NuPhy Air75 V3
into a private, local notification beacon on macOS. The light bar pulses when
Codex or Claude Code needs approval, presents a plan/chooser question, or
finishes a response while its app is in the background. They stop when you
return to the app or begin your next prompt.

The release deliberately uses the keyboard's standard Caps Lock LED output, not
NuPhy's RGB protocol. It makes no network requests, contains no downloaded
runtime dependencies, does not read keystrokes, and never approves an agent
action.

![NuPhy Air75 V3 Caps Lock light bar pulsing as an agent notification](docs/media/air75-v3-beacon-demo.gif)

_The standard Caps Lock light bar pulses when an agent is waiting for you._

## How it works

There is no window to keep open and no keyboard profile to configure:

1. Codex or Claude Code emits an official local hook event when it needs input
   or finishes a response.
2. The included Python hook writes a tiny routing-only marker on your Mac. It
   does not save the prompt, response, command, or tool data.
3. The background Swift app sees that marker and alternates the Air75 V3's
   standard Caps Lock LED bit, making the Caps Lock light bar pulse.
4. Returning to the desktop app or submitting your next CLI prompt clears the
   marker and restores the real Caps Lock light state.

The app starts automatically after login by default. Agent hooks can also launch
it when needed. After setup, use Codex and Claude normally. The beacon is automatic.

## Getting started

### 1. Check the requirements

You need:

- macOS 15 or newer;
- a NuPhy Air75 V3 in USB wired mode or Bluetooth channel 1;
- Codex and/or Claude Code already installed;
- Apple's Xcode Command Line Tools.

Check for Apple's Swift compiler:

```sh
xcrun --find swift
```

If that command fails, run `xcode-select --install` and complete Apple's prompt.

### 2. Download, review, and install

Nothing is piped from the internet into a shell. Clone the source, preview the
exact installation plan, and then run it:

```sh
git clone https://github.com/justintylerm/nuphy-capslock-agent-beacon.git
cd nuphy-capslock-agent-beacon
./install.sh --dry-run
./install.sh
```

The installer automatically configures whichever supported agents it finds.
To select them explicitly, use `./install.sh --codex`, `./install.sh --claude`,
or `./install.sh --codex --claude`.

### 3. Allow the Caps Lock LED connection

Open **System Settings → Privacy & Security → Input Monitoring** and enable
**NuPhy CapsLock Agent Beacon**. macOS places keyboard LED access in this broad
permission category even though this app never requests keyboard input reports.

If the app exited while waiting for permission, launch it again from
`~/Applications/NuPhy CapsLock Agent Beacon.app` or rerun `./install.sh`.

### 4. Trust the Codex hooks

In Codex, enter `/hooks`, review the new user hooks, and trust them. Claude Code
loads its settings automatically.

You do not need NuPhy's web configurator, a special RGB effect, or an open beacon
window.

### 5. Try a simple test

1. Ask Codex or Claude a normal question that takes a few seconds to answer.
2. Switch to another app before the response finishes.
3. When the final response is ready, the Caps Lock light bar should pulse.
4. Return to the Codex/Claude desktop app, or submit your next CLI prompt. The
   pulse should stop and the real Caps Lock state should be restored.

Final-response alerts are intentionally suppressed while you are already looking
at the agent app. Approval and plan/chooser prompts pulse as soon as they appear.
If the test fails, follow the [troubleshooting checklist](docs/TROUBLESHOOTING.md).

## What is supported

| Component | Status |
| --- | --- |
| NuPhy Air75 V3 ANSI, current tested firmware | Tested |
| USB wired mode | Tested |
| Bluetooth channel 1 (`Air75 V3-1`) | Tested |
| Codex desktop app hooks | Tested |
| Claude Code hooks | Tested |
| macOS 15 or newer | Required |
| Bluetooth channels 2/3, 2.4 GHz, ISO/JIS layouts | Not yet verified |
| Other NuPhy models | Intentionally rejected until safely verified |

## What the installer changes

The installer:

- builds the Swift app from the checked-out source with Apple's toolchain;
- installs it only for your account under `~/Applications`;
- installs one readable Python hook under your Application Support folder;
- merges its handlers into existing Codex and Claude JSON without replacing
  unrelated settings or hooks;
- saves mode-`0600` backups before editing either JSON file;
- optionally adds a user LaunchAgent so the app starts after login;
- uses no `sudo`, package manager, remote installer, or network call.

To disable automatic startup after login while keeping on-demand hook launching:

```sh
./install.sh --codex --claude --no-login-item
```

## Behavior

- **Approval or plan question:** starts pulsing immediately.
- **Tool completes, fails, or is denied:** clears the matching approval pulse.
- **Final response in the background:** starts pulsing after a one-second grace
  period, preventing a false alert when you are already looking at the app.
- **Return to the Codex or Claude Desktop app:** clears the message pulse.
- **CLI users:** the next submitted prompt clears the pulse; merely focusing an
  arbitrary terminal cannot be detected without broader app/input observation.
- **Caps Lock is genuinely on:** the beacon pulses around the real state and
  restores the light to on when the alert ends.
- **Disconnect/reconnect:** the app retries and restores the real Caps Lock
  indicator whenever it regains the exact keyboard interface.
- **Update/uninstall:** the app handles the termination signal and restores the
  real indicator before the installer continues.

The default pulse alternates every 0.25 seconds. To change it, edit
`~/Library/Application Support/NuPhy CapsLock Agent Beacon/pulse-timing.json`
and restart the app. Each value must be between 0.15 and 5 seconds.

## Why Caps Lock instead of full-board RGB?

The Air75 V3's animated RGB modes use a vendor-specific control protocol. During
development, RGB effects worked but required repeated vendor lighting-state
writes and introduced more failure modes, including a temporarily stuck
indicator state. The final project excludes every RGB, profile, keymap, macro,
firmware, and reset command.

The Caps Lock light bar is controlled through the standard keyboard LED output
that macOS already uses for normal Caps Lock indication. Beacon writes are volatile:
they change one output bit, not the keyboard's saved lighting profile or
firmware. There is no idle write heartbeat. See [Safety](docs/SAFETY.md) for the
precise hardware boundary and measured tradeoffs.

## Privacy model

Everything stays on the Mac:

- no telemetry, sockets, web requests, analytics, or update checker;
- no Accessibility, Screen Recording, Apple Events, or keystroke capture;
- prompt text, response text, commands, tool inputs, and tool outputs are never
  written by this project;
- marker files retain only source/session/turn/tool routing identifiers and use
  private permissions;
- the Codex final-response gate scans only the exact transcript path supplied by
  the official Stop hook for a matching `task_complete` type and turn ID. It
  neither parses nor stores conversation content;
- diagnostics contain timestamps, event names, sources, counts, and app state,
  never conversation content.

Codex documents that its transcript JSONL format is not stable, so a Codex
update can break final-message detection without expanding this project's data
access. Approval and plan hooks do not depend on that scan. Read the full
[architecture](docs/ARCHITECTURE.md) and [security policy](SECURITY.md).

## Uninstall

Preview the exact removal, then run it:

```sh
./uninstall.sh --dry-run
./uninstall.sh
```

The uninstaller removes only this project's exact hook command, leaves unrelated
settings intact, and moves installed files to a dated folder in `~/.Trash` so
they remain recoverable. Add `--reset-permission` if you also want macOS to
forget this app's Input Monitoring decision. More detail is in
[UNINSTALL.md](UNINSTALL.md).

## Build and test locally

```sh
sh Scripts/test.sh
sh Scripts/build-beacon-app.sh
```

The automated tests use temporary directories and do not open a HID device or
write to a keyboard. Hardware tests are intentionally manual and opt-in.

## Troubleshooting and compatibility

Start with [Troubleshooting](docs/TROUBLESHOOTING.md). If your Air75 V3 is safely
rejected, add a report using the privacy checklist in
[Compatibility](docs/COMPATIBILITY.md); do not post serial numbers, local paths,
hook payloads, or transcripts.

Official references:

- [OpenAI Codex hooks](https://developers.openai.com/codex/hooks)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [NuPhy support center](https://helpcenter.nuphy.com/)

This independent project is not affiliated with or endorsed by NuPhy, OpenAI,
or Anthropic. NuPhy, Codex, Claude, and macOS are trademarks of their respective
owners.

Licensed under the [MIT License](LICENSE).
