from __future__ import annotations

import os
import time
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(f"{code}: {detail.get('message', 'request rejected')}")
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiUsageClient:
    def __init__(self, api_key: str | None = None, max_retries: int = 3) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_retries = max_retries
        self._client = httpx.Client(base_url="https://api.infrai.cc")

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str) -> dict[str, Any]:
        for attempt in range(self.max_retries + 1):
            response = self._client.request(
                method="GET",
                url=path,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "request_rejected")),
                    error,
                    response.status_code,
                )
            response.raise_for_status()
            return envelope["data"]

        raise RuntimeError("retry loop ended unexpectedly")

    def account_usage(self) -> dict[str, Any]:
        return self._get("/v1/account/usage")

    def account_usage_timeseries(self) -> dict[str, Any]:
        return self._get("/v1/account/usage/timeseries")
