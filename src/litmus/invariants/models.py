from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InvariantStatus(str, Enum):
    CONFIRMED = "confirmed"
    SUGGESTED = "suggested"


class InvariantType(str, Enum):
    DIFFERENTIAL = "differential"
    PROPERTY = "property"
    STATE_TRANSITION = "state_transition"


class InvariantReviewState(str, Enum):
    PENDING = "pending"
    DISMISSED = "dismissed"
    PROMOTED = "promoted"


class RequestExample(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str | None = None
    path: str | None = None
    payload: dict[str, Any] | None = Field(default=None, alias="json")


class ResponseExample(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status_code: int | None = None
    body: dict[str, Any] | None = Field(default=None, alias="json")


class InvariantReview(BaseModel):
    state: InvariantReviewState
    reason: str | None = None
    reviewed_at: str | None = None
    review_source: str | None = None
    review_run_id: str | None = None


class Invariant(BaseModel):
    name: str
    source: str
    status: InvariantStatus
    type: InvariantType
    reasoning: str | None = None
    request: RequestExample | None = None
    response: ResponseExample | None = None
    review: InvariantReview | None = None

    def is_route_gap_warning(self) -> bool:
        return self.source == "suggested:route_gap"

    def is_pending_suggestion(self) -> bool:
        if self.status is not InvariantStatus.SUGGESTED:
            return False
        if self.review is None:
            return True
        return self.review.state is InvariantReviewState.PENDING

    def is_dismissed_suggestion(self) -> bool:
        return (
            self.status is InvariantStatus.SUGGESTED
            and self.review is not None
            and self.review.state is InvariantReviewState.DISMISSED
        )

    def is_promoted_confirmation(self) -> bool:
        return (
            self.status is InvariantStatus.CONFIRMED
            and self.review is not None
            and self.review.state is InvariantReviewState.PROMOTED
            and not self.is_route_gap_warning()
        )
