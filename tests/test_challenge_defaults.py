"""Defaults of challenges and assignments and the rules that are NOT constraints."""

from learning_helpers import (
    ASSIGNMENTS,
    CHALLENGES,
    create_assignment,
    create_challenge,
)


def test_a_new_challenge_is_an_active_local_coding_challenge(client, owner):
    response = create_challenge(client, owner, title="Fizz buzz")
    assert response.status_code == 201, response.text
    challenge = response.json()
    assert challenge["category"] == "coding"
    assert challenge["access_model"] == "local"
    assert challenge["is_active"] == 1
    assert challenge["is_external"] == 0
    assert challenge["free_access"] == 0
    assert challenge["account_required"] == 0
    assert challenge["rotation_order"] == 0
    assert challenge["tags_json"] == "[]"
    assert challenge["estimated_minutes"] is None
    assert challenge["version"] == 1


def test_challenge_tags_are_kept_as_text(client, owner):
    response = create_challenge(client, owner, tags_json='["loops", "strings"]')
    assert response.status_code == 201, response.text
    assert response.json()["tags_json"] == '["loops", "strings"]'
    free_text = create_challenge(client, owner, tags_json="not json at all")
    assert free_text.status_code == 201, free_text.text


def test_a_challenge_keeps_the_access_details_it_was_given(client, owner):
    response = create_challenge(
        client,
        owner,
        is_external=1,
        free_access=1,
        account_required=1,
        access_model="freemium",
        access_notes="Free tier covers the first 50 problems",
        access_source_url="https://example.com/pricing",
        url="https://example.com/problem/1",
    )
    assert response.status_code == 201, response.text
    challenge = client.get(
        f"{CHALLENGES}/{response.json()['id']}", headers=owner
    ).json()
    assert challenge["is_external"] == 1
    assert challenge["access_model"] == "freemium"
    assert challenge["url"] == "https://example.com/problem/1"


def test_a_new_assignment_is_assigned_and_not_started(client, owner):
    challenge = create_challenge(client, owner).json()
    response = create_assignment(client, owner, challenge["id"])
    assert response.status_code == 201, response.text
    assignment = response.json()
    assert assignment["status"] == "assigned"
    assert assignment["score_percent"] is None
    assert assignment["time_spent_minutes"] is None
    assert assignment["started_at"] is None
    assert assignment["completed_at"] is None
    assert assignment["version"] == 1


def test_a_challenge_key_is_not_enforced_to_be_unique(client, owner):
    first = create_challenge(client, owner, challenge_key="two-fer")
    second = create_challenge(client, owner, challenge_key="two-fer")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_a_challenge_can_be_assigned_again_on_another_day_or_the_same_day(
    client, owner
):
    challenge = create_challenge(client, owner).json()
    for day in ("2026-10-10", "2026-10-11", "2026-10-11"):
        response = create_assignment(
            client, owner, challenge["id"], assignment_date=day
        )
        assert response.status_code == 201, response.text


def test_a_challenge_keeps_the_old_id_when_it_is_imported(client, owner):
    imported = create_challenge(client, owner, legacy_id=321)
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 321
    assignment = create_assignment(client, owner, 321, legacy_id=654)
    assert assignment.status_code == 201, assignment.text
    assert (assignment.json()["id"], assignment.json()["challenge_id"]) == (654, 321)
    found = client.get(f"{ASSIGNMENTS}/legacy/654", headers=owner)
    assert found.status_code == 200
    assert found.json()["challenge_id"] == 321
    assert create_challenge(client, owner, legacy_id=321).status_code == 409


def test_an_integer_above_the_integer_range_is_refused_not_a_server_error(
    client, owner
):
    assert create_challenge(client, owner, estimated_minutes=2**31).status_code == 422
