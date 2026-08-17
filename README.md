# NuPhy Air75 V3 Caps Lock notification light for Codex and Claude Code

`nuphy-capslock-agent-beacon` turns the two Caps Lock light bars on a NuPhy
Air75 V3 into a private, local notification beacon on macOS. The bars pulse when
Codex or Claude Code needs approval, presents a plan/chooser question, or
finishes a response while its app is in the background. They stop when you
return to the app or begin your next prompt.

The release deliberately uses the keyboard's standard Caps Lock LED output—not
NuPhy's RGB protocol. It makes no network requests, contains no downloaded
runtime dependencies, does not read keystrokes, and never approves an agent
action.

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

You also need Apple's Xcode Command Line Tools, which provide the trusted Swift
compiler and system Python used by the source-only installer. If `xcrun --find
swift` fails, install them with `xcode-select --install` before continuing.

## Install without piping the internet into a shell

Review the source on GitHub first. Clone it, inspect the local plan, then install:

```sh
git clone https://github.com/justintylerm/nuphy-capslock-agent-beacon.git
cd nuphy-capslock-agent-beacon
./install.sh --dry-run
./install.sh
```

The installer:

- builds the Swift app from the checked-out source with Apple's toolchain;
- installs it only for your account under `~/Applications`;
- installs one readable Python hook under your Application Support folder;
- merges its handlers into existing Codex and Claude JSON without replacing
  unrelated settings or hooks;
- saves mode-`0600` backups before editing either JSON file;
- optionally adds a user LaunchAgent so the app starts after login;
- uses no `sudo`, package manager, remote installer, or network call.

If only one agent is installed, it is selected automatically. You can also be
explicit:

```sh
./install.sh --codex
./install.sh --claude
./install.sh --codex --claude --no-login-item
```

After installation:

1. Approve Input Monitoring only for **NuPhy CapsLock Agent Beacon**. macOS uses
   that permission category for access to a keyboard's output LED even though
   this app does not request input reports.
2. In Codex, open `/hooks`, review the installed commands, and trust them.
3. Leave the keyboard in wired mode or Bluetooth channel 1. No NuPhy web page
   or RGB configuration is needed.

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

The Caps Lock bars are controlled through the standard keyboard LED output that
macOS already uses for normal Caps Lock indication. Beacon writes are volatile:
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
