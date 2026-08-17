# Keyboard and system safety

## What is written to the keyboard

The only hardware mutation is a Boolean value on the HID element whose usage is
the standard Caps Lock LED. This is the same class of volatile output used when
the operating system reflects ordinary Caps Lock state.

The release contains no command for:

- RGB colors, effects, speed, or brightness;
- onboard lighting profiles;
- firmware or bootloader updates;
- keymaps, macros, reset, or calibration;
- vendor feature reports.

The LED state is not a saved configuration and does not write the keyboard's
firmware flash. There is no idle hardware heartbeat. While an alert is active,
the default timing changes the one-bit LED state about four times per second.
When idle, the app writes only when it needs to restore/synchronize the real Caps
Lock indication or after reconnecting.

## Wear assessment

LEDs and volatile HID output registers are designed to change repeatedly. This
project's Caps Lock path is materially lower risk than repeatedly rewriting
vendor lighting settings. It also avoids the persistent-memory wear concern that
motivated the final design.

No independent NuPhy endurance specification for this exact control path has
been published, so the project does not claim a mathematically zero risk. The
safety argument is architectural: standard volatile LED output, one bit, bounded
rate, no saved profile, no firmware path, exact-device matching, and no writes
while idle.

## Why Input Monitoring appears

macOS protects keyboard HID access under Input Monitoring even when a process
selects an output element. The app calls the HID permission API, but it never
registers an input-report callback, interprets keycodes, or stores keyboard
input. The OS permission is broader than the program's source-level behavior.

## Failure handling

- Unknown and mismatched HID devices are rejected.
- Disconnects trigger a retry rather than a broader device search.
- The real logical Caps Lock state is restored at startup, alert completion, and
  before a reconnect attempt when the device is reachable.
- `SIGTERM`/`SIGINT` cancel the pulse and run that same restore path before an
  update or uninstall finishes stopping the app.
- Approval markers expire after 30 minutes in the app; message markers expire
  after 12 hours.
- Invalid pulse timing falls back to 0.25 seconds and values below 0.15 seconds
  are rejected.

If the indicator ever behaves incorrectly, quit the app or unplug/reconnect the
keyboard. Both stop the volatile output immediately. Then file a synthetic,
redacted report before re-enabling the beacon.
