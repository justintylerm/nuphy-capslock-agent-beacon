#!/usr/bin/python3
"""Safely remove NuPhy CapsLock Agent Beacon from the current user."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from configure import remove_hooks
from install import APP_NAME, BUNDLE_ID, LAUNCH_LABEL, hook_command, home_directory


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Refusing to modify malformed JSON: {path}: {error}")
    if not isinstance(value, dict):
        raise RuntimeError(f"Refusing to modify non-object JSON: {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=".beacon-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(
            descriptor,
            (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def unique_trash_directory(home: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = home / ".Trash" / f"NuPhy-CapsLock-Agent-Beacon-{stamp}"
    candidate = base
    suffix = 1
    while candidate.exists():
        candidate = Path(f"{base}-{suffix}")
        suffix += 1
    return candidate


def bootout(plist_path: Path) -> None:
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") == "1":
        return
    subprocess.run(
        [
            "/bin/launchctl",
            "bootout",
            f"gui/{os.getuid()}",
            str(plist_path),
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_app() -> None:
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") == "1":
        return
    subprocess.run(
        ["/usr/bin/pkill", "-TERM", "-x", "nuphy-capslock-agent-beacon"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        running = subprocess.run(
            ["/usr/bin/pgrep", "-x", "nuphy-capslock-agent-beacon"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if running.returncode != 0:
            return
        time.sleep(0.1)
    raise RuntimeError("the beacon did not stop cleanly; installed files were kept")


def move_if_present(path: Path, trash: Path, name: str) -> None:
    if not path.exists() and not path.is_symlink():
        return
    trash.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.replace(path, trash / name)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the removal plan without changing files",
    )
    parser.add_argument(
        "--reset-permission",
        action="store_true",
        help="also reset this app's macOS Input Monitoring decision",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if sys.platform != "darwin":
        raise RuntimeError("This project currently supports macOS only")

    home = home_directory()
    support = home / "Library/Application Support/NuPhy CapsLock Agent Beacon"
    hook_path = support / "agent_beacon_hook.py"
    app_path = home / "Applications" / APP_NAME
    launch_agent = home / "Library/LaunchAgents" / f"{LAUNCH_LABEL}.plist"
    trash = unique_trash_directory(home)
    configs = {
        "codex": home / ".codex/hooks.json",
        "claude": home / ".claude/settings.json",
    }

    updated: dict[str, dict[str, Any]] = {}
    changed: dict[str, bool] = {}
    for source, path in configs.items():
        document = load_json(path)
        command = hook_command(hook_path, source)
        updated[source] = remove_hooks(document, command)
        changed[source] = updated[source] != document

    print("NuPhy CapsLock Agent Beacon removal plan:")
    for source, path in configs.items():
        print(f"  remove exact {source} hook entries: {path} ({'yes' if changed[source] else 'not found'})")
    print(f"  stop app and login item: {app_path}")
    print(f"  move installed files to Trash: {trash}")
    print(f"  reset Input Monitoring decision: {'yes' if arguments.reset_permission else 'no'}")
    if arguments.dry_run:
        print("Dry run complete; no files changed.")
        return 0

    bootout(launch_agent)
    stop_app()
    trash.mkdir(mode=0o700, parents=True, exist_ok=True)
    for source, path in configs.items():
        if not changed[source]:
            continue
        shutil.copy2(path, trash / f"{source}-config.before-uninstall.json")
        os.chmod(trash / f"{source}-config.before-uninstall.json", 0o600)
        write_json_atomic(path, updated[source])

    move_if_present(launch_agent, trash, "launch-agent.plist")
    move_if_present(app_path, trash, APP_NAME)
    move_if_present(support, trash, "Application Support")

    if arguments.reset_permission:
        subprocess.run(
            ["/usr/bin/tccutil", "reset", "ListenEvent", BUNDLE_ID],
            check=False,
        )

    print("Removal complete. Installed files are recoverable from:")
    print(f"  {trash}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Removal stopped safely: {error}", file=sys.stderr)
        raise SystemExit(1)
