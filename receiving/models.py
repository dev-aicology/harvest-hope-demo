"""Transport models. Drafts may be incomplete; submission has stronger rules."""
from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class Line(StrictModel):
    line_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    product_id: str | None = Field(default=None, max_length=80)
    barcode: str = Field(default="", max_length=32)
    description: str = Field(default="", max_length=300)
    quantity: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=3)
    unit: Literal["case", "each", "lb", "kg"] | None = None
    measured_weight: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=3)
    weight_unit: Literal["lb", "kg"] | None = None
    lot: str = Field(default="", max_length=120)
    expiry_date: date | None = None
    disposition: Literal["available", "hold"] = "available"
    checked: bool = False

    @field_validator("quantity", "measured_weight", mode="before")
    @classmethod
    def forbid_boolean_numbers(cls, value):
        if isinstance(value, bool):
            raise ValueError("Use a measured numeric amount, not a boolean.")
        return value


class ReceiptInput(StrictModel):
    supplier: str = Field(min_length=1, max_length=160)
    delivery_ref: str = Field(min_length=1, max_length=120)
    warehouse: str = Field(default="DEMO-DOCK-1", min_length=1, max_length=80)
    purchase_order_ref: str = Field(default="", max_length=120)
    received_on: date = Field(default_factory=date.today)
    notes: str = Field(default="", max_length=2000)
    lines: list[Line] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_lines(self):
        if len({line.line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Each receipt line must have a unique line_id.")
        return self


class ReceiptUpdate(ReceiptInput):
    expected_version: int = Field(ge=1)


class VersionCommand(StrictModel):
    expected_version: int = Field(ge=1)


class ReviewCommand(VersionCommand):
    note: str = Field(default="", max_length=1000)


class SuggestCommand(VersionCommand):
    line_id: str = Field(min_length=1, max_length=80)
    barcode: str = Field(default="", max_length=32)
    label_text: str = Field(default="", max_length=2000)
    use_ai: bool = False


class HandoffCommand(VersionCommand):
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")


class ReconcileCommand(VersionCommand):
    simulate_mismatch: bool = False


class SessionInput(StrictModel):
    identity: Literal["receiver", "reviewer"]
