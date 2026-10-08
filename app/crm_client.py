import logging
import time
from collections.abc import Callable
from typing import Any, Protocol

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429}


class CRMUnavailable(Exception):
    """The CRM could not return customer data after all retries."""


class CRMClient(Protocol):
    def get_cliente(self, cliente_id: str) -> dict[str, Any]: ...


def _is_retryable(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS or status_code >= 500


class HttpCRMClient:
    """CRM client with a per-attempt timeout and exponential backoff between attempts.

    Retries on 429, 5xx, timeouts and connection errors; other 4xx fail immediately because retrying
    cannot change the answer. Worst case latency is bounded by
    max_attempts * timeout + sum(backoff_base * 2**i for i in range(max_attempts - 1)).
    """

    def __init__(
        self,
        base_url: str,
        *,
        max_attempts: int = 3,
        timeout: float = 2.0,
        backoff_base: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._sleep = sleep
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    @classmethod
    def from_settings(cls, settings: Settings, **kwargs: Any) -> "HttpCRMClient":
        return cls(
            settings.crm_url,
            max_attempts=settings.crm_max_intentos,
            timeout=settings.crm_timeout_segundos,
            backoff_base=settings.crm_backoff_base,
            **kwargs,
        )

    def get_cliente(self, cliente_id: str) -> dict[str, Any]:
        last_error = ""
        for attempt in range(self._max_attempts):
            try:
                response = self._http.get(f"/clientes/{cliente_id}")
            except httpx.TransportError as exc:  # includes timeouts and connection errors
                last_error = f"{type(exc).__name__}: {exc}"
            else:
                if response.is_success:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise CRMUnavailable(f"invalid JSON from CRM: {exc}") from exc
                if not _is_retryable(response.status_code):
                    raise CRMUnavailable(f"CRM returned {response.status_code} for cliente_id={cliente_id}")
                last_error = f"HTTP {response.status_code}"

            if attempt < self._max_attempts - 1:
                delay = self._backoff_base * 2**attempt
                logger.info("CRM attempt %d/%d failed (%s); retrying in %.2fs",
                            attempt + 1, self._max_attempts, last_error, delay)
                self._sleep(delay)

        raise CRMUnavailable(f"CRM failed after {self._max_attempts} attempts: {last_error}")

    def close(self) -> None:
        self._http.close()
