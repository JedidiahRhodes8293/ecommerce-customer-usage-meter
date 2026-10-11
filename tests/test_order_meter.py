from src.order_meter import OrderOperation, OrderUsageEvent, OrderUsageLedger


def test_checkout_is_weighted_and_replay_is_not_billed_twice(tmp_path) -> None:
    ledger = OrderUsageLedger(tmp_path / "meter.db")
    checkout = OrderUsageEvent(
        event_id="evt-order-42-checkout",
        customer_id="customer-17",
        order_id="order-42",
        operation=OrderOperation.CHECKOUT,
    )

    first = ledger.record(checkout)
    replay = ledger.record(checkout)

    assert first.accepted is True
    assert first.added_units == 3
    assert replay.accepted is False
    assert replay.added_units == 0
    assert replay.customer_units == 3


def test_customer_total_combines_checkout_fulfillment_and_receipt(tmp_path) -> None:
    ledger = OrderUsageLedger(tmp_path / "meter.db")
    for event_id, operation in (
        ("evt-1", OrderOperation.CHECKOUT),
        ("evt-2", OrderOperation.FULFILLMENT),
        ("evt-3", OrderOperation.RECEIPT),
    ):
        ledger.record(
            OrderUsageEvent(
                event_id=event_id,
                customer_id="customer-17",
                order_id="order-42",
                operation=operation,
            )
        )

    usage = ledger.for_customer("customer-17")

    assert usage.total_units == 6
    assert usage.event_count == 3
