# Compatibility reports

Version 0.1.0 is intentionally conservative. It supports only identities that
were observed and manually tested, because broad keyboard HID matching would be
an unnecessary safety risk.

## Verified matrix

| Keyboard | Layout | Connection | Result |
| --- | --- | --- | --- |
| NuPhy Air75 V3 | ANSI | USB wired | Verified |
| NuPhy Air75 V3 | ANSI | Bluetooth channel 1 | Verified |

Bluetooth channels 2/3, the 2.4 GHz receiver, other layouts, firmware variants,
and other NuPhy models are not claimed yet.

## Reporting a safe rejection

Open an issue with:

- keyboard model and layout;
- macOS version;
- firmware version as shown by NuPhy's official tool;
- wired, Bluetooth channel number, or 2.4 GHz;
- which feature failed: connect, approval, plan question, final response, clear.

Do **not** post:

- keyboard serial numbers;
- `~/.codex` or `~/.claude` files;
- hook JSON payloads;
- transcripts, prompts, responses, tool data, or diagnostic logs containing
  local paths;
- screenshots that expose account names or private conversations.

A new device identity should be added only after a contributor demonstrates the
standard Caps Lock output element on real hardware and supplies a narrowly scoped
change with a manual restore test. Compatibility must never be expanded to all
keyboards or all HID output elements merely to make discovery easier.
