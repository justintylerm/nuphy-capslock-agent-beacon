#!/usr/bin/python3
"""Build and safely install NuPhy CapsLock Agent Beacon for the current user."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from configure import merge_hooks


APP_NAME = "NuPhy CapsLock Agent Beacon.app"
BUNDLE_ID = "io.github.justintylerm.nuphy-capslock-agent-beacon"
LAUNCH_LABEL = BUNDLE_ID


def home_directory() -> Path:
    override = os.environ.get("NUPHY_AGENT_BEACON_HOME")
    return Path(override).expanduser().resolve() if override else Path.home()


def project_directory() -> Path:
    return Path(__file__).resolve().parent.parent


def support_directory(home: Path) -> Path:
    return home / "Library/Application Support/NuPhy CapsLock Agent Beacon"


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
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".beacon-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
        os.write(descriptor, payload)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def hook_command(hook_path: Path, source: str) -> str:
    if '"' in str(hook_path):
        raise RuntimeError("Installation path may not contain a double quote")
    return f'/usr/bin/python3 "{hook_path}" event {source}'


def backup_file(path: Path, backup_dir: Path, timestamp: str) -> None:
    if not path.exists():
        return
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = backup_dir / f"{path.parent.name}-{path.name}.{timestamp}.backup"
    shutil.copy2(path, destination)
    os.chmod(destination, 0o600)


def build_app(project: Path) -> Path:
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_BUILD") == "1":
        fixture = os.environ.get("NUPHY_AGENT_BEACON_BUILT_APP")
        if not fixture:
            raise RuntimeError("SKIP_BUILD requires NUPHY_AGENT_BEACON_BUILT_APP")
        return Path(fixture)
    subprocess.run(
        ["/bin/sh", str(project / "Scripts/build-beacon-app.sh")],
        cwd=project,
        check=True,
    )
    return project / "dist" / APP_NAME


def install_app(built_app: Path, destination: Path, backup_dir: Path, timestamp: str) -> None:
    if not built_app.is_dir():
        raise RuntimeError(f"Built app not found: {built_app}")
    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    staging = destination.parent / f".{APP_NAME}.installing"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(built_app, staging, symlinks=True)
    if destination.exists():
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        backup = backup_dir / f"previous-app.{timestamp}.bundle-backup"
        os.replace(destination, backup)
    os.replace(staging, destination)


def install_hook(source: Path, destination: Path) -> None:
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    os.chmod(destination, 0o700)


def stop_existing_app() -> None:
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") == "1":
        return
    executable = "nuphy-capslock-agent-beacon"
    subprocess.run(
        ["/usr/bin/pkill", "-TERM", "-x", executable],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(50):
        running = subprocess.run(
            ["/usr/bin/pgrep", "-x", executable],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if running.returncode != 0:
            return
        time.sleep(0.1)
    raise RuntimeError("the existing beacon did not stop cleanly")


def write_default_timing(path: Path) -> None:
    if path.exists():
        return
    write_json_atomic(
        path,
        {"inverted_seconds": 0.25, "normal_seconds": 0.25},
    )


def write_launch_agent(path: Path, app: Path) -> None:
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    value = {
        "Label": LAUNCH_LABEL,
        "ProgramArguments": ["/usr/bin/open", "-gj", str(app)],
        "RunAtLoad": True,
        "ProcessType": "Interactive",
    }
    descriptor, temporary_name = tempfile.mkstemp(prefix=".beacon-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o644)
        os.write(descriptor, plistlib.dumps(value, fmt=plistlib.FMT_XML))
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def bootout_launch_agent(plist_path: Path) -> None:
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") == "1":
        return
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["/bin/launchctl", "bootout", domain, str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def refresh_launch_agent(plist_path: Path) -> None:
    bootout_launch_agent(plist_path)
    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") == "1":
        return
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["/bin/launchctl", "bootstrap", domain, str(plist_path)],
        check=False,
    )


def selected_sources(arguments: argparse.Namespace, home: Path) -> list[str]:
    if arguments.codex or arguments.claude:
        return [
            source
            for source, selected in (
                ("codex", arguments.codex),
                ("claude", arguments.claude),
            )
            if selected
        ]
    found: list[str] = []
    if (home / ".codex").exists():
        found.append("codex")
    if (home / ".claude").exists():
        found.append("claude")
    if not found:
        raise RuntimeError(
            "Neither ~/.codex nor ~/.claude exists. Run with --codex or --claude."
        )
    return found


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", action="store_true", help="configure Codex")
    parser.add_argument("--claude", action="store_true", help="configure Claude Code")
    parser.add_argument(
        "--no-login-item",
        action="store_true",
        help="do not start the beacon automatically after login",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate configuration and print the plan without changing files",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if sys.platform != "darwin":
        raise RuntimeError("This project currently supports macOS only")

    home = home_directory()
    project = project_directory()
    support = support_directory(home)
    hook_source = project / "Hooks/agent_beacon_hook.py"
    hook_destination = support / "agent_beacon_hook.py"
    app_destination = home / "Applications" / APP_NAME
    launch_agent = home / "Library/LaunchAgents" / f"{LAUNCH_LABEL}.plist"
    backups = support / "backups"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sources = selected_sources(arguments, home)

    config_paths = {
        "codex": home / ".codex/hooks.json",
        "claude": home / ".claude/settings.json",
    }
    documents = {source: load_json(config_paths[source]) for source in sources}
    commands = {
        source: hook_command(hook_destination, source) for source in sources
    }
    merged = {
        source: merge_hooks(documents[source], source, commands[source])
        for source in sources
    }

    print("NuPhy CapsLock Agent Beacon installation plan:")
    print(f"  app: {app_destination}")
    print(f"  hook: {hook_destination}")
    for source in sources:
        print(f"  merge {source} hooks: {config_paths[source]}")
    print(f"  login item: {'no' if arguments.no_login_item else 'yes'}")
    print("  network access: none")
    print("  sudo/root changes: none")
    if arguments.dry_run:
        print("Dry run complete; no files changed.")
        return 0

    built_app = build_app(project)
    stop_existing_app()
    support.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(support, 0o700)
    install_app(built_app, app_destination, backups, timestamp)
    install_hook(hook_source, hook_destination)
    write_default_timing(support / "pulse-timing.json")

    for source in sources:
        backup_file(config_paths[source], backups, timestamp)
        write_json_atomic(config_paths[source], merged[source])

    if arguments.no_login_item:
        bootout_launch_agent(launch_agent)
        if launch_agent.exists():
            launch_agent.unlink()
    else:
        write_launch_agent(launch_agent, app_destination)
        refresh_launch_agent(launch_agent)

    if os.environ.get("NUPHY_AGENT_BEACON_SKIP_LAUNCH") != "1":
        subprocess.run(["/usr/bin/open", "-gj", str(app_destination)], check=False)

    print("Installation complete.")
    if "codex" in sources:
        print("Open /hooks in Codex and review/trust the new user hooks.")
    print("Approve Input Monitoring only for NuPhy CapsLock Agent Beacon.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Install stopped safely: {error}", file=sys.stderr)
        raise SystemExit(1)
