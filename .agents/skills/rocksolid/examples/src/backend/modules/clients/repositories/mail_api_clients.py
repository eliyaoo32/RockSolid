"""Sends clients their email through the mail API, the third party that delivers it. Only this
file knows the mail API's requests."""

import httpx
from pydantic import SecretStr

from modules.clients.domain.client import Client
from modules.clients.services.errors import MailNotConfiguredError


class MailApiWelcomeMailer:
    def __init__(self, url: str, api_key: SecretStr | None) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key

    async def send_welcome(self, client: Client, email: str) -> None:
        """The client's ID is the request's idempotency key, so a welcome sent again, such as by a
        retried task, reaches the client once."""
        if self._api_key is None:
            raise MailNotConfiguredError("The mail API key is not set, so no email can be sent.")
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{self._url}/v1/messages",
                headers={"authorization": f"Bearer {self._api_key.get_secret_value()}"},
                json={
                    "to": email,
                    "template": "client-welcome",
                    "variables": {"name": client.display_name},
                    "idempotency_key": str(client.id),
                },
            )
        response.raise_for_status()
