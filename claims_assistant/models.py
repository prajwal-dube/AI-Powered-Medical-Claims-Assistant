from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str | None = Field(default=None, max_length=64)
    claim_id: str | None = Field(default=None, max_length=64)
    diagnosis: str | None = Field(default=None, max_length=200)
    procedure: str | None = Field(default=None, max_length=200)
    amount: Decimal | None = None
    service_date: str | None = Field(default=None, max_length=10)
    summary: str = Field(max_length=500)

    @field_validator("amount")
    @classmethod
    def finite_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("amount must be finite")
        return value


class Flag(BaseModel):
    code: str
    detail: str
    severity: Literal["review", "info"] = "review"


class ClaimResult(BaseModel):
    id: int
    filename: str
    extractor: str
    prompt_version: str
    fields: ExtractedClaim
    flags: list[Flag]
    created_at: str
