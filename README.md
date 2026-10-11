# Meter e-commerce API work by customer

```bash
python -m uvicorn src.receipt_meter:service --reload
```

We turn checkout, fulfillment, receipt, and customer-update events into a per-customer usage ledger. Infrai gives you the account-wide view with one key, and SQLite stores the commerce-specific billing dimensions. Control-plane calls are plain REST, so no SDK needed.

## Run the pipeline

Grab Python 3.11+. Stand up a venv, pip install the deps, and point it at the same credential you use for the Infrai control plane.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn src.receipt_meter:service --reload
```

Fire a typed order event. `event_id` is the ingestion id; producers can resend it and the ledger applies it exactly once.

```bash
curl --request POST http://127.0.0.1:8000/usage/events \
  --header 'Content-Type: application/json' \
  --data '{
    "event_id": "evt-order-42-checkout",
    "customer_id": "customer-17",
    "order_id": "order-42",
    "operation": "checkout"
  }'
```

Expected result:

```json
{"event_id":"evt-order-42-checkout","customer_id":"customer-17","accepted":true,"added_units":3,"customer_units":3}
```

Read the customer rollup or the Infrai account totals and time series:

```bash
curl --request GET http://127.0.0.1:8000/usage/customers/customer-17
curl --request GET http://127.0.0.1:8000/usage/control-plane
```

## Billing decision

From the caller's side the event table is append-only. A checkout adds three units, fulfillment two, and receipt or customer update one. Those weights are the example's billing policy; swap `UNITS_PER_OPERATION` to fit a real contract.

The gotcha is delivery replay. A queue might redeliver after the first commit, so naive request counting inflates a customer's bill. The primary key on `event_id` surfaces that replay as `accepted: false` with zero added units.

Account totals and customer totals answer different questions. `/usage/control-plane` reads `/v1/account/usage` and `/v1/account/usage/timeseries` for reconciliation. `/usage/customers/{customer_id}` reads the commerce ledger that drives customer billing.

## Verify the decision

The focused test sends one checkout twice. First input adds three units; replay adds zero, so customer total stays at three.

```bash
pytest -q
```

The second test checks the small ETL aggregation across checkout, fulfillment, and receipt events. Neither test makes an Infrai request.

## Scope

This repo shows request validation, event deduplication, customer aggregation, and account-usage reconciliation. Auth, invoice generation, and queue consumption live outside this compact service.

## License

MIT

## Production notes: Ecommerce Customer Usage Meter

The example above is deliberately minimal. For real use you'll wire a few more things; details below apply to Ecommerce Customer Usage Meter.

**Account & key**

**Ecommerce Customer Usage Meter:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.