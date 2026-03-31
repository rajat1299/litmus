from __future__ import annotations

import json
from pathlib import Path

from litmus.github_action.publish import COMMENT_MARKER, publish_pr_comment


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_publish_pr_comment_creates_comment_when_no_existing_litmus_comment(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 42}}), encoding="utf-8")
    seen_requests: list[tuple[str, str, str | None]] = []

    def fake_urlopen(request):
        body = request.data.decode("utf-8") if request.data is not None else None
        seen_requests.append((request.get_method(), request.full_url, body))
        if request.get_method() == "GET":
            return _FakeResponse([])
        if request.get_method() == "POST":
            return _FakeResponse({"id": 101, "html_url": "https://github.example/comment/101"})
        raise AssertionError(f"Unexpected method: {request.get_method()}")

    comment_url = publish_pr_comment(
        api_url="https://api.github.example",
        repository="acme/litmus",
        event_path=event_path,
        token="token-123",
        comment="## Litmus Verification\n\nLooks bad.",
        urlopen_fn=fake_urlopen,
    )

    assert comment_url == "https://github.example/comment/101"
    assert seen_requests[0] == (
        "GET",
        "https://api.github.example/repos/acme/litmus/issues/42/comments",
        None,
    )
    assert seen_requests[1][0] == "POST"
    assert seen_requests[1][1] == "https://api.github.example/repos/acme/litmus/issues/42/comments"
    assert COMMENT_MARKER in seen_requests[1][2]
    assert "## Litmus Verification" in seen_requests[1][2]


def test_publish_pr_comment_updates_existing_litmus_comment(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 7}}), encoding="utf-8")
    seen_requests: list[tuple[str, str, str | None]] = []

    def fake_urlopen(request):
        body = request.data.decode("utf-8") if request.data is not None else None
        seen_requests.append((request.get_method(), request.full_url, body))
        if request.get_method() == "GET":
            return _FakeResponse(
                [
                    {"id": 55, "body": f"{COMMENT_MARKER}\nOld Litmus comment"},
                    {"id": 99, "body": "Some other comment"},
                ]
            )
        if request.get_method() == "PATCH":
            return _FakeResponse({"id": 55, "html_url": "https://github.example/comment/55"})
        raise AssertionError(f"Unexpected method: {request.get_method()}")

    comment_url = publish_pr_comment(
        api_url="https://api.github.example",
        repository="acme/litmus",
        event_path=event_path,
        token="token-123",
        comment="## Litmus Verification\n\nUpdated.",
        urlopen_fn=fake_urlopen,
    )

    assert comment_url == "https://github.example/comment/55"
    assert seen_requests[1][0] == "PATCH"
    assert seen_requests[1][1] == "https://api.github.example/repos/acme/litmus/issues/comments/55"
    assert COMMENT_MARKER in seen_requests[1][2]
    assert "Updated." in seen_requests[1][2]


def test_publish_pr_comment_skips_when_event_is_not_pull_request(tmp_path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"ref": "refs/heads/main"}), encoding="utf-8")

    def fake_urlopen(_request):
        raise AssertionError("urlopen should not be called without pull_request context")

    comment_url = publish_pr_comment(
        api_url="https://api.github.example",
        repository="acme/litmus",
        event_path=event_path,
        token="token-123",
        comment="## Litmus Verification",
        urlopen_fn=fake_urlopen,
    )

    assert comment_url is None
