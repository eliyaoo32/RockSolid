"""Finds who signed in from a Firebase Auth ID token.

Follows Firebase's guide for verifying ID tokens with a third-party JWT library.
"""

import asyncio
from typing import Protocol

import jwt
from pydantic import ValidationError

from modules.users.domain.user import User

# Google's public keys for Firebase ID tokens.
FIREBASE_SIGNING_KEYS = (
    "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
)


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


class FirebaseUserRepository:
    def __init__(self, project_id: str, keys: SigningKeys) -> None:
        self._project_id = project_id
        self._keys = keys

    async def from_token(self, token: str) -> User | None:
        try:
            # The first call fetches Google's public keys over the network; later calls use a cache.
            key = await asyncio.to_thread(self._keys.get_signing_key_from_jwt, token)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._project_id,
                issuer=f"https://securetoken.google.com/{self._project_id}",
                options={"require": ["exp", "iat", "sub", "email"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise  # Google's keys are unreachable: a server failure, not a bad token.
        except jwt.PyJWTError:
            return None
        try:
            return User(
                id=claims["sub"],
                email=claims["email"],
                display_name=claims.get("name") or claims["email"],
            )
        except ValidationError:
            return None
