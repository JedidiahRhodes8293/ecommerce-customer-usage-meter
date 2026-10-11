from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException

from .infrai_usage import InfraiError, InfraiUsageClient
from .order_meter import CustomerUsage, MeterResult, OrderUsageEvent, OrderUsageLedger


DATABASE_PATH = Path(os.environ.get("METER_DATABASE", "usage-meter.db"))
ledger = OrderUsageLedger(DATABASE_PATH)


@asynccontextmanager
async def lifespan(_: FastAPI) -> Iterator[None]:
    yield


service = FastAPI(title="E-commerce customer usage meter", lifespan=lifespan)


def usage_client() -> Iterator[InfraiUsageClient]:
    client = InfraiUsageClient()
    try:
        yield client
    finally:
        client.close()


@service.post("/usage/events", response_model=MeterResult)
def meter_order_event(event: OrderUsageEvent) -> MeterResult:
    return ledger.record(event)


@service.get("/usage/customers/{customer_id}", response_model=CustomerUsage)
def read_customer_usage(customer_id: str) -> CustomerUsage:
    return ledger.for_customer(customer_id)


@service.get("/usage/control-plane")
def read_control_plane(client: InfraiUsageClient = Depends(usage_client)) -> dict[str, object]:
    try:
        return {
            "usage": client.account_usage(),
            "timeseries": client.account_usage_timeseries(),
        }
    except InfraiError as error:
        client_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": error.code, "error": error.detail},
        ) from error

