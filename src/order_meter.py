from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class OrderOperation(str, Enum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPT = "receipt"
    CUSTOMER_UPDATE = "customer_update"


UNITS_PER_OPERATION: dict[OrderOperation, int] = {
    OrderOperation.CHECKOUT: 3,
    OrderOperation.FULFILLMENT: 2,
    OrderOperation.RECEIPT: 1,
    OrderOperation.CUSTOMER_UPDATE: 1,
}


class OrderUsageEvent(BaseModel):
    event_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    operation: OrderOperation


class MeterResult(BaseModel):
    event_id: str
    customer_id: str
    accepted: bool
    added_units: int
    customer_units: int


class CustomerUsage(BaseModel):
    customer_id: str
    total_units: int
    event_count: int


class OrderUsageLedger:
    def __init__(self, database: str | Path) -> None:
        self.connection = sqlite3.connect(str(database), check_same_thread=False)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS order_usage (
                event_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                units INTEGER NOT NULL
            )
            """
        )
        self.connection.commit()

    def record(self, event: OrderUsageEvent) -> MeterResult:
        units = UNITS_PER_OPERATION[event.operation]
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO order_usage
                (event_id, customer_id, order_id, operation, units)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event.event_id, event.customer_id, event.order_id, event.operation.value, units),
        )
        self.connection.commit()
        accepted = cursor.rowcount == 1
        usage = self.for_customer(event.customer_id)
        return MeterResult(
            event_id=event.event_id,
            customer_id=event.customer_id,
            accepted=accepted,
            added_units=units if accepted else 0,
            customer_units=usage.total_units,
        )

    def for_customer(self, customer_id: str) -> CustomerUsage:
        total, count = self.connection.execute(
            """
            SELECT COALESCE(SUM(units), 0), COUNT(*)
            FROM order_usage WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()
        return CustomerUsage(
            customer_id=customer_id,
            total_units=int(total),
            event_count=int(count),
        )

