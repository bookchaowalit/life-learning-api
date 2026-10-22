"""Shared helpers for the learning domain tests."""

import uuid
from typing import Any

CHALLENGES = "/v1/challenges"
ASSIGNMENTS = "/v1/challenge-assignments"


def create_challenge(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {
        "challenge_key": f"key-{uuid.uuid4().hex[:8]}",
        "track": "python",
        "challenge_type": "coding",
        "provider": "exercism",
        "title": "Two fer",
    }
    return client.post(CHALLENGES, headers=owner, json={**body, **fields})


def create_assignment(
    client: Any, owner: dict[str, str], challenge_id: int, **fields: Any
) -> Any:
    body = {"challenge_id": challenge_id, "assignment_date": "2026-10-10"}
    return client.post(ASSIGNMENTS, headers=owner, json={**body, **fields})


def another_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """Headers of a second owner in a different workspace, with every permission."""
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    headers: dict[str, str] = harness.token(actor, workspace)
    return headers
