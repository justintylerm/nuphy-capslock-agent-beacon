# Troubleshooting

## Nothing pulses

1. Confirm macOS 15 or newer and a NuPhy Air75 V3.
2. Use USB wired mode or Bluetooth channel 1. Bluetooth 2/3 and 2.4 GHz are not
   yet verified.
3. Open System Settings → Privacy & Security → Input Monitoring and enable only
   **NuPhy CapsLock Agent Beacon**.
4. In Codex, open `/hooks` and verify/trust the user hooks.
5. Run `./install.sh --dry-run` to see which agents are detected, then rerun the
   installer if needed.
6. Inspect the routing-only diagnostics:

   ```sh
   tail -n 50 "$HOME/Library/Application Support/NuPhy CapsLock Agent Beacon/events.log"
   ```

Redact usernames and paths before posting any output.

## Approval works, but Codex final messages do not

Codex final-message detection is intentionally stricter. It waits for the exact
turn's `task_complete` record in the transcript path supplied by Codex's Stop
hook. OpenAI documents the JSONL transcript format as unstable; a Codex update
may require a detector update. Do not work around this by uploading a transcript.
Open a redacted issue with app/Codex versions and diagnostic event names only.

## It pulses while I am looking at the app

There is a one-second grace period after a final response. If the app bundle ID
has changed in a new Codex or Claude build, foreground suppression may need an
update. Include the released app version and the exact official app name in a
redacted issue; do not attach window contents.

For CLI use, focusing a terminal does not clear the light because the beacon
does not inspect terminal windows or typing. Submitting the next prompt clears
it through the agent hook.

## The light bar stays inverted

Quit **NuPhy CapsLock Agent Beacon** or disconnect/reconnect the keyboard. The
output is volatile, so either action ends the beacon's control. Confirm the
physical Caps Lock function itself is normal, then check `events.log`. Do not use
a vendor reset solely for this app without first ruling out a running process.

## Bluetooth does not connect

The initial release accepts only the tested channel-1 identity `Air75 V3-1`.
Select channel 1 with the keyboard's documented shortcut and pair it normally in
macOS. The beacon does not pair, unpair, or modify Bluetooth configuration.

## Remove everything

Use `./uninstall.sh --dry-run`, followed by `./uninstall.sh`. See
[UNINSTALL.md](../UNINSTALL.md) for the exact recoverable removal behavior.
