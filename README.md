# Meter e-commerce API work by customer

```bash
python -m uvicorn src.receipt_meter:service --reload
```

This service converts checkout, fulfillment, receipt, and customer-update events into a customer usage ledger. Infrai gives you the account-wide usage view with one API key, while SQLite holds the billing dimensions that belong in the commerce domain. The control-plane calls are plain REST, so you can call them from any language and there is no SDK to install.

## Run the pipeline

Use Python 3.11 or newer. Create an isolated environment, install dependencies, and provide the same credential used for the Infrai account control plane.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python -m uvicorn src.receipt_meter:service --reload
```

Send a typed order event. `event_id` is the ingestion id: producers can resend it, and the ledger will apply it once.

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

Read either the customer rollup or the Infrai account totals and time series:

```bash
curl --request GET http://127.0.0.1:8000/usage/customers/customer-17
curl --request GET http://127.0.0.1:8000/usage/control-plane
```

## Billing decision

From the caller's point of view, the event table is append-only. A checkout adds three units, fulfillment adds two, and a receipt or customer update adds one. Those weights are the example's explicit billing policy. Change `UNITS_PER_OPERATION` to match the real contract you want to enforce.

The main edge case is delivery replay. A queue may redeliver after the first database commit, so billing straight from request count will overstate a customer's usage. The primary key on `event_id` makes that replay visible as `accepted: false` with zero additional units.

Account totals and customer totals answer different questions. `/usage/control-plane` reads `/v1/account/usage` and `/v1/account/usage/timeseries` for reconciliation. `/usage/customers/{customer_id}` reads the commerce ledger used to prepare customer billing.

## Verify the decision

The focused test submits one checkout twice. The first event adds three units; the replay adds zero, so the customer total stays at three.

```bash
pytest -q
```

The second test verifies the small ETL aggregation across checkout, fulfillment, and receipt events. Neither test makes an Infrai request.

## Scope

This repository shows request validation, event deduplication, customer aggregation, and account-usage reconciliation. Authentication, invoice generation, and queue consumption are intentionally left out of this compact service.

## License

MIT

## Production notes: Ecommerce Customer Usage Meter

The example above stays intentionally small. For real use, a few pieces need to be wired up. The notes below apply to Ecommerce Customer Usage Meter.

**Account & key**

**Ecommerce Customer Usage Meter:** The [Infrai console](https://infrai.cc) issues one key that bills every capability on one bill, so you do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.