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


class RequestExample(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    method: str | None = None
    path: str | None = None
    payload: dict[str, Any] | None = Field(default=None, alias="json")


class ResponseExample(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status_code: int | None = None
    body: dict[str, Any] | None = Field(default=None, alias="json")


class Invariant(BaseModel):
    name: str
    source: str
    status: InvariantStatus
    type: InvariantType
    request: RequestExample | None = None
    response: ResponseExample | None = None
