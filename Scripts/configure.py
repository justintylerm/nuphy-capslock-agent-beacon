#!/usr/bin/python3
"""Pure JSON hook merge/remove helpers used by install and tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CODEX_SPECS: tuple[tuple[str, str | None], ...] = (
    ("PreToolUse", "^request_user_input$"),
    ("PermissionRequest", None),
    ("PostToolUse", None),
    ("UserPromptSubmit", None),
    ("Stop", None),
    ("SessionEnd", None),
)

CLAUDE_SPECS: tuple[tuple[str, str | None], ...] = (
    ("PermissionRequest", None),
    ("Notification", "permission_prompt|idle_prompt|elicitation_dialog"),
    ("PostToolUse", None),
    ("PostToolUseFailure", None),
    ("PermissionDenied", None),
    ("UserPromptSubmit", None),
    ("Stop", None),
    ("StopFailure", None),
    ("SessionEnd", None),
)


def specs_for(source: str) -> tuple[tuple[str, str | None], ...]:
    if source == "codex":
        return CODEX_SPECS
    if source == "claude":
        return CLAUDE_SPECS
    raise ValueError(f"unsupported source: {source}")


def merge_hooks(
    document: dict[str, Any],
    source: str,
    command: str,
) -> dict[str, Any]:
    """Return a copy with this project's exact command appended once/event."""
    # Canonicalize an earlier installation of this same command before adding
    # the current event/matcher set. Unrelated commands are never touched.
    result = remove_hooks(document, command)
    hooks = result.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("the existing 'hooks' value is not an object")

    for event, matcher in specs_for(source):
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"the existing hooks.{event} value is not an array")
        group: dict[str, Any] = {
            "hooks": [
                {
                    "type": "command",
                    "command": command,
                    "timeout": 5,
                }
            ]
        }
        if matcher is not None:
            group["matcher"] = matcher
        groups.append(group)
    return result


def remove_hooks(document: dict[str, Any], command: str) -> dict[str, Any]:
    """Remove only handlers whose command exactly matches this installation."""
    result = deepcopy(document)
    hooks = result.get("hooks")
    if not isinstance(hooks, dict):
        return result

    for event in list(hooks):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups: list[Any] = []
        for group in groups:
            if not isinstance(group, dict):
                kept_groups.append(group)
                continue
            handlers = group.get("hooks")
            if not isinstance(handlers, list):
                kept_groups.append(group)
                continue
            kept_handlers = [
                handler
                for handler in handlers
                if not (
                    isinstance(handler, dict)
                    and handler.get("command") == command
                )
            ]
            if kept_handlers:
                updated = deepcopy(group)
                updated["hooks"] = kept_handlers
                kept_groups.append(updated)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            hooks.pop(event, None)
    if not hooks:
        result.pop("hooks", None)
    return result
