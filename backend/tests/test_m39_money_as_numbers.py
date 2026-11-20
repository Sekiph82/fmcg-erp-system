"""Owner 2026-11-20: money fields are JSON numbers, never text."""
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

import app.main  # noqa: F401  installs the encoder exactly as the real app does


class Line(BaseModel):
    amount: Decimal
    qty: Optional[Decimal] = None


class Doc(BaseModel):
    id: UUID
    total: Decimal
    due: date
    lines: list[Line]


def test_decimal_fields_are_numbers_in_responses():
    api = FastAPI()
    uid = uuid4()

    @api.get("/doc", response_model=Doc)
    def doc():
        return Doc(id=uid, total=Decimal("1250.5000"), due=date(2026, 11, 20),
                   lines=[Line(amount=Decimal("0.1700")), Line(amount=Decimal("10"), qty=Decimal("3.000"))])

    body = TestClient(api).get("/doc").json()
    assert body == {"id": str(uid), "total": 1250.5, "due": "2026-11-20",
                    "lines": [{"amount": 0.17, "qty": None}, {"amount": 10, "qty": 3}]}
    assert isinstance(body["total"], float) and isinstance(body["lines"][0]["amount"], float)
