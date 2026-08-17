# Contributing

Issues and narrowly scoped pull requests are welcome.

Before submitting code:

```sh
sh Scripts/test.sh
```

Automated tests must not open a HID device, request Input Monitoring, or write to
a keyboard. Hardware behavior requires a separate, explicit manual test plan.
Never include real hooks, transcripts, logs, usernames, local paths, serial
numbers, keys, tokens, or conversation content in a fixture or issue.

Changes that broaden HID matching, add a device/transport, increase write rate,
read an input element, or add any vendor-specific command require a written
safety rationale and real-hardware verification. RGB, firmware, reset, keymap,
macro, telemetry, and remote update features are outside the release's current
security boundary.

Keep the project dependency-free unless a dependency is essential and its
security/privacy cost is documented. Preserve unrelated user configuration in
installer changes and add an install/uninstall round-trip test.
