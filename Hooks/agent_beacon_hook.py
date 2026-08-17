#!/usr/bin/python3
"""Routing-only Codex and Claude Code hook for NuPhy CapsLock Agent Beacon.

The hook never approves or denies agent actions. It deliberately retains only
event/source/session/turn/tool identifiers and never writes prompt, response,
command, tool input, or tool output content to disk.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any


APP_NAME = "NuPhy CapsLock Agent Beacon.app"
APP_PATH = Path.home() / "Applications" / APP_NAME
DEFAULT_STATE_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / "NuPhy CapsLock Agent Beacon"
)
DEFAULT_CODEX_DIR = Path.home() / ".codex"
FOREGROUND_GRACE_SECONDS = 1.0
TERMINAL_POLL_SECONDS = 0.25
TERMINAL_GATE_SECONDS = 6 * 60 * 60
TERMINAL_RECEIPT_SECONDS = 24 * 60 * 60
ROUTING_ID = re.compile(r"[0-9A-Za-z._:-]{1,160}\Z")
EVENT_NAME = re.compile(r"[A-Za-z][0-9A-Za-z_:-]{0,79}\Z")
TASK_COMPLETE = re.compile(rb'"type"\s*:\s*"task_complete"')
MAX_EVENT_BYTES = 2 * 1024 * 1024
SOURCE_BUNDLE_IDENTIFIERS = {
    "codex": "com.openai.codex",
    "claude": "com.anthropic.claudefordesktop",
}


def state_directory() -> Path:
    override = os.environ.get("NUPHY_AGENT_BEACON_STATE_DIR")
    return Path(override) if override else DEFAULT_STATE_DIR


def codex_directory() -> Path:
    override = os.environ.get("NUPHY_AGENT_BEACON_CODEX_DIR")
    return Path(override) if override else DEFAULT_CODEX_DIR


def installed_app_path() -> Path:
    override = os.environ.get("NUPHY_AGENT_BEACON_APP_PATH")
    return Path(override) if override else APP_PATH


def ensure_private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def requests_directory() -> Path:
    return ensure_private_directory(state_directory() / "requests")


def messages_directory() -> Path:
    return ensure_private_directory(state_directory() / "messages")


def pending_messages_directory() -> Path:
    return ensure_private_directory(state_directory() / "pending-messages")


def gates_directory() -> Path:
    return ensure_private_directory(state_directory() / "terminal-gates")


def diagnostic(event: str, source: str = "system", **details: str) -> None:
    """Append routing-only diagnostics; never include hook payload content."""
    try:
        directory = ensure_private_directory(state_directory())
        record = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "source": source,
            **details,
        }
        descriptor = os.open(
            directory / "events.log",
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(
                descriptor,
                (json.dumps(record, sort_keys=True) + "\n").encode("utf-8"),
            )
        finally:
            os.close(descriptor)
    except OSError:
        pass


def read_input() -> dict[str, Any]:
    try:
        raw = sys.stdin.read(MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            return {}
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def normalized_metadata(source: str, payload: dict[str, Any]) -> dict[str, str]:
    result = {"source": source}
    for field in ("session_id", "turn_id", "tool_use_id", "tool_name"):
        value = payload.get(field)
        if isinstance(value, str) and ROUTING_ID.fullmatch(value):
            result[field] = value
    return result


def event_name(payload: dict[str, Any]) -> str:
    value = payload.get("hook_event_name")
    return value if isinstance(value, str) and EVENT_NAME.fullmatch(value) else "unknown"


def record_token(metadata: dict[str, str]) -> str:
    stable = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def write_private_json(path: Path, record: dict[str, str]) -> None:
    ensure_private_directory(path.parent)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".agent-beacon-",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(
            descriptor,
            json.dumps(record, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
        )
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def launch_app() -> None:
    app = installed_app_path()
    if not app.is_dir():
        return
    subprocess.run(
        ["/usr/bin/open", "-gj", str(app)],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
    )


def start_approval(source: str, payload: dict[str, Any]) -> None:
    metadata = normalized_metadata(source, payload)
    token = record_token(metadata)
    write_private_json(
        requests_directory() / f"{token}.json",
        {**metadata, "token": token},
    )
    diagnostic(
        "approval-started",
        source,
        hook_event=event_name(payload),
    )
    launch_app()


def record_matches(
    record: dict[str, Any],
    source: str,
    payload: dict[str, Any],
    clear_session: bool,
) -> bool:
    if record.get("source") != source:
        return False
    session_id = payload.get("session_id")
    if clear_session:
        return not isinstance(session_id, str) or record.get("session_id") == session_id
    for field in ("tool_use_id", "turn_id"):
        value = payload.get(field)
        if isinstance(value, str) and record.get(field) == value:
            return True
    return isinstance(session_id, str) and record.get("session_id") == session_id


def clear_approvals(
    source: str,
    payload: dict[str, Any],
    *,
    clear_session: bool,
) -> None:
    removed = 0
    for path in requests_directory().glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(record, dict) and record_matches(
            record, source, payload, clear_session
        ):
            try:
                path.unlink()
                removed += 1
            except FileNotFoundError:
                pass
    if removed:
        diagnostic("approvals-cleared", source, count=str(removed))


def clear_messages(source: str, payload: dict[str, Any]) -> None:
    # Codex Desktop has a single physical indicator, so any new Codex prompt
    # acknowledges all Codex completions. Claude stays session-scoped.
    session_id = None if source == "codex" else payload.get("session_id")
    removed = 0
    paths = list(messages_directory().glob(f"waiting-{source}-*.json"))
    paths += list(
        pending_messages_directory().glob(f"waiting-{source}-*.json")
    )
    for path in paths:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(record, dict) or record.get("source") != source:
            continue
        if isinstance(session_id, str) and record.get("session_id") != session_id:
            continue
        try:
            path.unlink()
            removed += 1
        except FileNotFoundError:
            pass
    if removed:
        diagnostic("messages-cleared", source, count=str(removed))


def launch_services_asn(arguments: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["/usr/bin/lsappinfo", *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"ASN:0x[0-9A-Fa-f]+-0x[0-9A-Fa-f]+", result.stdout)
    return match.group(0) if match else None


def source_is_frontmost(source: str) -> bool:
    bundle_identifier = SOURCE_BUNDLE_IDENTIFIERS.get(source)
    if bundle_identifier is None:
        return False
    source_asn = launch_services_asn(["find", f"bundleid={bundle_identifier}"])
    front_asn = launch_services_asn(["front"])
    return source_asn is not None and source_asn == front_asn


def pending_message_path(source: str, token: str) -> Path:
    return pending_messages_directory() / f"waiting-{source}-{token}.json"


def message_path(source: str, token: str) -> Path:
    return messages_directory() / f"waiting-{source}-{token}.json"


def start_message(source: str, payload: dict[str, Any]) -> None:
    metadata = normalized_metadata(source, payload)
    token = record_token(metadata)
    generation = str(time.time_ns())
    write_private_json(
        pending_message_path(source, token),
        {**metadata, "token": token, "generation": generation},
    )
    subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "defer-message",
            source,
            token,
            generation,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    diagnostic("message-pending", source)


def defer_message(source: str, token: str, generation: str) -> int:
    if source not in SOURCE_BUNDLE_IDENTIFIERS or not re.fullmatch(
        r"[0-9a-f]{64}", token
    ):
        return 0
    time.sleep(FOREGROUND_GRACE_SECONDS)
    pending = pending_message_path(source, token)
    try:
        record = json.loads(pending.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(record, dict) or record.get("generation") != generation:
        return 0
    if source_is_frontmost(source):
        try:
            pending.unlink()
        except FileNotFoundError:
            pass
        diagnostic("message-suppressed-foreground", source)
        return 0
    try:
        os.replace(pending, message_path(source, token))
    except FileNotFoundError:
        return 0
    diagnostic("message-created", source)
    launch_app()
    return 0


def create_exclusive(path: Path) -> bool:
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    os.close(descriptor)
    return True


def gate_paths(session_id: str, turn_id: str) -> tuple[Path, Path]:
    token = hashlib.sha256(f"{session_id}\0{turn_id}".encode()).hexdigest()
    directory = gates_directory()
    return directory / f"active-{token}", directory / f"done-{token}"


def purge_old_gates() -> None:
    now = time.time()
    for path in gates_directory().iterdir():
        lifetime = (
            TERMINAL_RECEIPT_SECONDS
            if path.name.startswith("done-")
            else TERMINAL_GATE_SECONDS
        )
        try:
            if now - path.stat().st_mtime > lifetime:
                path.unlink()
        except OSError:
            pass


def validated_transcript(payload: dict[str, Any]) -> Path | None:
    raw = payload.get("transcript_path")
    if not isinstance(raw, str) or not raw:
        return None
    candidate = Path(raw).expanduser().resolve()
    root = codex_directory().expanduser().resolve()
    try:
        if os.path.commonpath([candidate, root]) != str(root):
            return None
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def schedule_codex_terminal(payload: dict[str, Any]) -> None:
    session_id = payload.get("session_id")
    turn_id = payload.get("turn_id")
    transcript = validated_transcript(payload)
    if (
        not isinstance(session_id, str)
        or not ROUTING_ID.fullmatch(session_id)
        or not isinstance(turn_id, str)
        or not ROUTING_ID.fullmatch(turn_id)
        or transcript is None
    ):
        diagnostic("terminal-gate-skipped", "codex")
        return
    purge_old_gates()
    active, done = gate_paths(session_id, turn_id)
    if done.exists() or not create_exclusive(active):
        return
    try:
        subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "wait-terminal",
                str(transcript),
                session_id,
                turn_id,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError:
        try:
            active.unlink()
        except OSError:
            pass
        return
    diagnostic("terminal-gate-started", "codex")


def scan_task_complete(path: Path, turn_id: str, offset: int) -> tuple[bool, int]:
    turn_pattern = re.compile(
        rb'"turn_id"\s*:\s*"' + re.escape(turn_id.encode("ascii")) + rb'"'
    )
    try:
        size = path.stat().st_size
        if size < offset:
            offset = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            for line in stream:
                if TASK_COMPLETE.search(line) and turn_pattern.search(line):
                    return True, stream.tell()
            return False, stream.tell()
    except OSError:
        return False, offset


def wait_terminal(
    transcript_argument: str,
    session_id: str,
    turn_id: str,
) -> int:
    payload = {"transcript_path": transcript_argument}
    transcript = validated_transcript(payload)
    if (
        transcript is None
        or not ROUTING_ID.fullmatch(session_id)
        or not ROUTING_ID.fullmatch(turn_id)
    ):
        return 0
    active, done = gate_paths(session_id, turn_id)
    deadline = time.monotonic() + TERMINAL_GATE_SECONDS
    offset = 0
    try:
        while time.monotonic() < deadline and active.exists():
            if (state_directory() / "paused").exists() or done.exists():
                return 0
            complete, offset = scan_task_complete(transcript, turn_id, offset)
            if complete:
                if create_exclusive(done):
                    start_message(
                        "codex",
                        {
                            "hook_event_name": "TaskComplete",
                            "session_id": session_id,
                            "turn_id": turn_id,
                        },
                    )
                    diagnostic("terminal-complete", "codex")
                return 0
            time.sleep(TERMINAL_POLL_SECONDS)
    finally:
        try:
            active.unlink()
        except OSError:
            pass
    return 0


def handle_event(source: str, payload: dict[str, Any]) -> None:
    event = payload.get("hook_event_name")
    diagnostic("hook-event", source, hook_event=event_name(payload))
    if event == "PermissionRequest" or (
        event == "PreToolUse" and payload.get("tool_name") == "request_user_input"
    ):
        start_approval(source, payload)
    elif event == "Notification" and payload.get("notification_type") in {
        "permission_prompt",
        "idle_prompt",
        "elicitation_dialog",
    }:
        start_approval(source, payload)
    elif event == "UserPromptSubmit":
        clear_approvals(source, payload, clear_session=True)
        clear_messages(source, payload)
        launch_app()
    elif event == "Stop":
        clear_approvals(source, payload, clear_session=True)
        if source == "codex":
            schedule_codex_terminal(payload)
        else:
            start_message(source, payload)
    elif event == "StopFailure":
        clear_approvals(source, payload, clear_session=True)
        start_message(source, payload)
    elif event == "SessionEnd":
        clear_approvals(source, payload, clear_session=True)
        clear_messages(source, payload)
    elif event in {
        "PostToolUse",
        "PostToolUseFailure",
        "PermissionDenied",
    }:
        clear_approvals(source, payload, clear_session=False)


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "wait-terminal":
        return wait_terminal(sys.argv[2], sys.argv[3], sys.argv[4])
    if len(sys.argv) == 5 and sys.argv[1] == "defer-message":
        return defer_message(sys.argv[2], sys.argv[3], sys.argv[4])
    if len(sys.argv) != 3 or sys.argv[1] != "event" or sys.argv[2] not in {
        "codex",
        "claude",
    }:
        return 64

    source = sys.argv[2]
    if (state_directory() / "paused").exists():
        if source == "codex":
            print("{}")
        return 0
    payload = read_input()
    try:
        handle_event(source, payload)
    except OSError:
        # Hooks are advisory and must never interrupt or decide an agent action.
        pass
    if source == "codex":
        # Codex Stop requires valid JSON. An empty object never approves,
        # denies, blocks, or continues the agent workflow.
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
