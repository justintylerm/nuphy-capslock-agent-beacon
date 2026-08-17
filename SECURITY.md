# Security policy

## Reporting a vulnerability

Please open a GitHub security advisory rather than a public issue when a report
could reveal a vulnerability, private path, transcript, hook payload, or device
identifier. Do not attach real Codex/Claude configuration files or diagnostic
logs without redacting them first.

Security reports should describe the affected version, expected boundary,
reproduction steps using synthetic data, and impact. Never include API keys,
tokens, prompts, responses, local usernames, or keyboard serial numbers.

## Deliberate boundaries

The release app:

- makes no network connections and has no update mechanism;
- uses only Apple system frameworks and Python's standard library;
- does not use Accessibility, Screen Recording, Apple Events, or input callbacks;
- matches a narrow, known Air75 V3 HID identity and selects only the standard
  Caps Lock LED output element;
- contains no vendor RGB, firmware, reset, profile, keymap, or macro command;
- stores routing identifiers only, in private local files;
- never returns an approval, denial, block, or continue decision to an agent.

The installer uses no root privileges and changes only the paths listed in
[Architecture](docs/ARCHITECTURE.md). Existing hook files must be valid JSON; a
malformed or unexpected shape causes a safe refusal instead of replacement.
Uninstallation matches the complete installed command string, so another hook
cannot be removed merely because it has a similar name.

Input Monitoring is a broad macOS permission category. The source uses it only
to open the standard Caps Lock output element; the operating-system grant itself
is broader than this code path. Review the exact source and system prompt before
approving it.

No software can promise zero risk to hardware or data. This design minimizes the
surface by using a normal volatile LED output, avoiding persistent keyboard
configuration, rejecting unknown device identities, and performing no idle
heartbeat writes. See [Safety](docs/SAFETY.md).
