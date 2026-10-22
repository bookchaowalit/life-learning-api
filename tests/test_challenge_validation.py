"""What the learning cell refuses: missing fields, unknown kinds, dangling refs and backwards times."""

import pytest
from learning_helpers import (
    ASSIGNMENTS,
    CHALLENGES,
    another_workspace,
    create_assignment,
    create_challenge,
)

MISSING = 987654321


def test_a_challenge_needs_a_key_track_type_provider_and_title(client, owner):
    complete = {
        "challenge_key": "two-fer",
        "track": "python",
        "challenge_type": "coding",
        "provider": "exercism",
        "title": "Two fer",
    }
    for missing in complete:
        body = {k: v for k, v in complete.items() if k != missing}
        response = client.post(CHALLENGES, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_challenge_text_fields_cannot_be_empty(client, owner):
    for field in ("challenge_key", "track", "provider", "title"):
        assert create_challenge(client, owner, **{field: ""}).status_code == 422, field


def test_challenge_type_must_be_a_known_kind(client, owner):
    assert create_challenge(client, owner, challenge_type="game").status_code == 422
    for kind in ("coding", "quiz", "study", "project", "competition"):
        assert (
            create_challenge(client, owner, challenge_type=kind).status_code == 201
        ), kind


def test_minutes_and_flags_must_be_whole_numbers(client, owner):
    assert create_challenge(client, owner, estimated_minutes="soon").status_code == 422
    assert create_challenge(client, owner, rotation_order=1.5).status_code == 422
    assert create_challenge(client, owner, is_active="yes").status_code == 422


def test_a_challenge_refuses_fields_it_does_not_have(client, owner):
    assert create_challenge(client, owner, language="python").status_code == 422


def test_required_challenge_fields_cannot_be_cleared_on_update(client, owner):
    challenge = create_challenge(client, owner).json()
    path = f"{CHALLENGES}/{challenge['id']}"
    for field in ("challenge_key", "track", "challenge_type", "provider", "title"):
        cleared = client.patch(path, headers=owner, json={field: None})
        assert cleared.status_code == 422, field
        assert cleared.json()["detail"] == {"error": "invalid_value", "fields": [field]}


def test_an_assignment_needs_a_challenge_and_a_date(client, owner):
    challenge = create_challenge(client, owner).json()
    no_date = client.post(
        ASSIGNMENTS, headers=owner, json={"challenge_id": challenge["id"]}
    )
    assert no_date.status_code == 422
    no_challenge = client.post(
        ASSIGNMENTS, headers=owner, json={"assignment_date": "2026-10-10"}
    )
    assert no_challenge.status_code == 422


def test_an_assignment_can_only_point_at_an_existing_challenge(client, owner):
    refused = create_assignment(client, owner, MISSING)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}
    assert create_assignment(client, owner, 0).status_code == 422


def test_an_assignment_cannot_point_at_a_challenge_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign = create_challenge(client, stranger).json()
    refused = create_assignment(client, owner, foreign["id"])
    assert refused.status_code == 422, refused.text


def test_assignment_status_must_be_a_known_step(client, owner):
    challenge = create_challenge(client, owner).json()
    assert (
        create_assignment(client, owner, challenge["id"], status="failed").status_code
        == 422
    )
    for status in ("assigned", "in_progress", "completed", "skipped"):
        response = create_assignment(client, owner, challenge["id"], status=status)
        assert response.status_code == 201, status


def test_assignment_date_must_be_a_calendar_date(client, owner):
    challenge = create_challenge(client, owner).json()
    assert (
        create_assignment(
            client, owner, challenge["id"], assignment_date="today"
        ).status_code
        == 422
    )
    assert (
        create_assignment(
            client, owner, challenge["id"], assignment_date="2026-02-30"
        ).status_code
        == 422
    )


def test_score_and_time_must_be_numbers(client, owner):
    challenge = create_challenge(client, owner).json()
    assert (
        create_assignment(
            client, owner, challenge["id"], score_percent="high"
        ).status_code
        == 422
    )
    assert (
        create_assignment(
            client, owner, challenge["id"], score_percent=88.5
        ).status_code
        == 422
    )
    assert (
        create_assignment(
            client, owner, challenge["id"], time_spent_minutes="a while"
        ).status_code
        == 422
    )
    ok = create_assignment(
        client, owner, challenge["id"], score_percent=88, time_spent_minutes=42.5
    )
    assert ok.status_code == 201, ok.text


def test_an_assignment_cannot_be_completed_before_it_started(client, owner):
    challenge = create_challenge(client, owner).json()
    backwards = create_assignment(
        client,
        owner,
        challenge["id"],
        started_at="2026-10-10T10:00:00+00:00",
        completed_at="2026-10-10T09:00:00+00:00",
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["completed_at", "started_at"],
    }
    same_moment = create_assignment(
        client,
        owner,
        challenge["id"],
        started_at="2026-10-10T10:00:00+00:00",
        completed_at="2026-10-10T10:00:00+00:00",
    )
    assert same_moment.status_code == 201, same_moment.text


def test_completing_before_the_start_is_refused_on_update(client, owner):
    challenge = create_challenge(client, owner).json()
    assignment = create_assignment(
        client, owner, challenge["id"], started_at="2026-10-10T10:00:00+00:00"
    ).json()
    path = f"{ASSIGNMENTS}/{assignment['id']}"
    refused = client.patch(
        path, headers=owner, json={"completed_at": "2026-10-09T10:00:00+00:00"}
    )
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["completed_at"] is None
    # A patch that touches neither moment still works.
    noted = client.patch(path, headers=owner, json={"notes": "Tricky edge cases"})
    assert noted.status_code == 200, noted.text


@pytest.mark.xfail(
    strict=True,
    reason="cellkit accepts NaN and Infinity for a real field: the row is stored but read back "
    "with time_spent_minutes null (201 instead of 422)",
)
@pytest.mark.parametrize("not_a_number", ["NaN", "Infinity", "-Infinity"])
def test_time_spent_that_is_not_a_finite_number_is_refused(client, owner, not_a_number):
    challenge = create_challenge(client, owner).json()
    raw = (
        f'{{"challenge_id": {challenge["id"]}, "assignment_date": "2026-10-10", '
        f'"time_spent_minutes": {not_a_number}}}'
    )
    response = client.post(
        ASSIGNMENTS, headers={**owner, "content-type": "application/json"}, content=raw
    )
    assert response.status_code == 422
