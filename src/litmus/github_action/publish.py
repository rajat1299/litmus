from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

COMMENT_MARKER = "<!-- litmus-pr-comment -->"
COMMENTS_PAGE_SIZE = 30


def publish_pr_comment(
    *,
    api_url: str,
    repository: str,
    event_path: Path,
    token: str,
    comment: str,
    urlopen_fn: Callable[[Request], Any] = urlopen,
) -> str | None:
    pull_request_number = _pull_request_number(event_path)
    if pull_request_number is None:
        return None

    comment_body = f"{COMMENT_MARKER}\n{comment}"
    issue_comments_url = (
        f"{api_url.rstrip('/')}/repos/{repository}/issues/{pull_request_number}/comments"
    )
    existing_comment = _find_existing_comment(
        issue_comments_url=issue_comments_url,
        token=token,
        urlopen_fn=urlopen_fn,
    )

    if existing_comment is None:
        response = _request_json(
            method="POST",
            url=issue_comments_url,
            token=token,
            payload={"body": comment_body},
            urlopen_fn=urlopen_fn,
        )
    else:
        response = _request_json(
            method="PATCH",
            url=f"{api_url.rstrip('/')}/repos/{repository}/issues/comments/{existing_comment['id']}",
            token=token,
            payload={"body": comment_body},
            urlopen_fn=urlopen_fn,
        )

    html_url = response.get("html_url")
    return str(html_url) if html_url is not None else None


def _pull_request_number(event_path: Path) -> int | None:
    if not event_path.exists():
        return None

    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return None

    number = pull_request.get("number")
    return number if isinstance(number, int) else None


def _find_existing_comment(
    *,
    issue_comments_url: str,
    token: str,
    urlopen_fn: Callable[[Request], Any],
) -> dict[str, Any] | None:
    page = 1
    while True:
        comments = _request_json(
            method="GET",
            url=issue_comments_url if page == 1 else f"{issue_comments_url}?page={page}",
            token=token,
            payload=None,
            urlopen_fn=urlopen_fn,
        )
        if not isinstance(comments, list):
            return None

        for comment in comments:
            if not isinstance(comment, dict):
                continue
            body = comment.get("body")
            if isinstance(body, str) and COMMENT_MARKER in body:
                return comment

        if len(comments) < COMMENTS_PAGE_SIZE:
            return None
        page += 1
    return None


def _request_json(
    *,
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None,
    urlopen_fn: Callable[[Request], Any],
) -> Any:
    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "litmus-github-action",
        },
        method=method,
    )
    with urlopen_fn(request) as response:
        return json.loads(response.read().decode("utf-8"))
