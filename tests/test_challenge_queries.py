"""Listing, grouping and lifecycle of challenges and their assignments."""

from learning_helpers import (
    ASSIGNMENTS,
    CHALLENGES,
    create_assignment,
    create_challenge,
)


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def listed(client, owner, path, **params):
    return ids(client.get(path, headers=owner, params=params))


def test_challenges_filter_by_type_and_category(client, owner):
    coding = create_challenge(client, owner, challenge_type="coding").json()
    quiz = create_challenge(
        client, owner, challenge_type="quiz", category="math"
    ).json()
    assert listed(client, owner, CHALLENGES, challenge_type="quiz") == [quiz["id"]]
    assert listed(client, owner, CHALLENGES, category="coding") == [coding["id"]]
    assert (
        listed(client, owner, CHALLENGES, category="math", challenge_type="coding")
        == []
    )


def test_a_filter_can_be_repeated_to_match_any_value(client, owner):
    coding = create_challenge(client, owner, challenge_type="coding").json()
    study = create_challenge(client, owner, challenge_type="study").json()
    create_challenge(client, owner, challenge_type="project")
    listed_both = client.get(
        CHALLENGES,
        headers=owner,
        params=[("challenge_type", "coding"), ("challenge_type", "study")],
    )
    assert ids(listed_both) == [coding["id"], study["id"]]


def test_an_unknown_challenge_type_in_a_filter_is_refused(client, owner):
    assert (
        client.get(
            CHALLENGES, headers=owner, params={"challenge_type": "game"}
        ).status_code
        == 422
    )


def test_challenges_cannot_be_listed_by_a_field_that_is_not_a_filter(client, owner):
    for field in ("track", "provider", "is_active", "difficulty"):
        refused = client.get(CHALLENGES, headers=owner, params={field: "x"})
        assert refused.status_code == 422, field
        assert refused.json()["detail"]["error"] == "unknown_filter"


def test_challenges_are_listed_oldest_first_and_newest_first_on_request(client, owner):
    first = create_challenge(client, owner, title="First", rotation_order=9).json()
    second = create_challenge(client, owner, title="Second", rotation_order=1).json()
    assert listed(client, owner, CHALLENGES) == [first["id"], second["id"]]
    assert listed(client, owner, CHALLENGES, order="desc") == [
        second["id"],
        first["id"],
    ]


def test_stats_count_challenges_per_type_and_category(client, owner):
    create_challenge(client, owner, challenge_type="coding")
    create_challenge(client, owner, challenge_type="coding", category="math")
    create_challenge(client, owner, challenge_type="quiz", category="math")
    by_type = client.get(
        f"{CHALLENGES}/stats", headers=owner, params={"group_by": "challenge_type"}
    )
    assert by_type.status_code == 200, by_type.text
    assert by_type.json()["groups"] == {"coding": 2, "quiz": 1}
    by_category = client.get(
        f"{CHALLENGES}/stats", headers=owner, params={"group_by": "category"}
    )
    assert by_category.json()["groups"] == {"coding": 1, "math": 2}


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    for path, field in ((CHALLENGES, "track"), (ASSIGNMENTS, "assignment_date")):
        stats = client.get(f"{path}/stats", headers=owner, params={"group_by": field})
        assert stats.status_code == 422, path


def test_assignments_filter_by_challenge_and_status(client, owner):
    one = create_challenge(client, owner, title="One").json()
    two = create_challenge(client, owner, title="Two").json()
    done = create_assignment(client, owner, one["id"], status="completed").json()
    open_one = create_assignment(client, owner, two["id"]).json()
    assert listed(client, owner, ASSIGNMENTS, challenge_id=one["id"]) == [done["id"]]
    assert listed(client, owner, ASSIGNMENTS, status="assigned") == [open_one["id"]]
    both = client.get(
        ASSIGNMENTS,
        headers=owner,
        params=[("status", "assigned"), ("status", "completed")],
    )
    assert ids(both) == [done["id"], open_one["id"]]


def test_stats_count_assignments_per_status_and_challenge(client, owner):
    challenge = create_challenge(client, owner).json()
    create_assignment(client, owner, challenge["id"], status="completed")
    create_assignment(client, owner, challenge["id"], status="completed")
    create_assignment(client, owner, challenge["id"], status="skipped")
    by_status = client.get(
        f"{ASSIGNMENTS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert by_status.json()["groups"] == {"completed": 2, "skipped": 1}
    by_challenge = client.get(
        f"{ASSIGNMENTS}/stats", headers=owner, params={"group_by": "challenge_id"}
    )
    assert by_challenge.json()["groups"] == {str(challenge["id"]): 3}


def test_an_assignment_is_worked_through_to_completion(client, owner):
    challenge = create_challenge(client, owner).json()
    assignment = create_assignment(client, owner, challenge["id"]).json()
    path = f"{ASSIGNMENTS}/{assignment['id']}"
    started = client.patch(
        path,
        headers=owner,
        json={"status": "in_progress", "started_at": "2026-10-10T09:00:00+00:00"},
    )
    assert started.status_code == 200, started.text
    assert started.json()["version"] == 2
    finished = client.patch(
        path,
        headers=owner,
        json={
            "status": "completed",
            "completed_at": "2026-10-10T10:15:00+00:00",
            "score_percent": 95,
            "time_spent_minutes": 75,
            "solution_url": "https://example.com/solution",
        },
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["version"] == 3
    assert finished.json()["score_percent"] == 95
    assert finished.json()["time_spent_minutes"] == 75
    assert finished.json()["challenge_id"] == challenge["id"]


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    challenge = create_challenge(client, owner, difficulty="easy").json()
    path = f"{CHALLENGES}/{challenge['id']}"
    same = client.patch(
        path, headers=owner, json={"difficulty": "easy", "category": "coding"}
    )
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1
    assert same.json()["updated_at"] == challenge["updated_at"]
    changed = client.patch(path, headers=owner, json={"difficulty": "hard"})
    assert changed.json()["version"] == 2


def test_a_stale_expected_version_is_refused(client, owner):
    challenge = create_challenge(client, owner).json()
    path = f"{CHALLENGES}/{challenge['id']}"
    assert (
        client.patch(path, headers=owner, json={"title": "Renamed"}).status_code == 200
    )
    stale = client.patch(
        path, headers=owner, json={"title": "Again", "expected_version": 1}
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"error": "version_conflict", "version": 2}


def test_a_challenge_with_assignments_cannot_be_deleted(client, owner):
    challenge = create_challenge(client, owner).json()
    assignment = create_assignment(client, owner, challenge["id"]).json()
    refused = client.delete(f"{CHALLENGES}/{challenge['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == {"error": "has_dependents"}
    assert (
        client.delete(f"{ASSIGNMENTS}/{assignment['id']}", headers=owner).status_code
        == 204
    )
    assert (
        client.delete(f"{CHALLENGES}/{challenge['id']}", headers=owner).status_code
        == 204
    )
    assert (
        client.get(f"{CHALLENGES}/{challenge['id']}", headers=owner).status_code == 404
    )


def test_a_deleted_assignment_is_gone(client, owner):
    challenge = create_challenge(client, owner).json()
    assignment = create_assignment(client, owner, challenge["id"]).json()
    path = f"{ASSIGNMENTS}/{assignment['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404
