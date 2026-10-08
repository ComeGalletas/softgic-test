from typing import Any, Protocol


class CRMUnavailable(Exception):
    """The CRM could not return customer data after all retries."""


class CRMClient(Protocol):
    def get_cliente(self, cliente_id: str) -> dict[str, Any]: ...
