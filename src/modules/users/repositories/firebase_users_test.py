"""Firebase is replaced by tokens signed with a local key; no test reaches Google."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from modules.users.domain.user import User
from modules.users.repositories.firebase_users import FirebaseUserRepository

PROJECT = "rocksolid-test"
SIGNING_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeSigningKeys:
    """Google's published keys, replaced by the one key the tests sign with."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        if self._error is not None:
            raise self._error
        return jwt.PyJWK(RSAAlgorithm.to_jwk(SIGNING_KEY.public_key(), as_dict=True), "RS256")


def make_token(key: rsa.RSAPrivateKey = SIGNING_KEY, **overrides: Any) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "aud": PROJECT,
        "iss": f"https://securetoken.google.com/{PROJECT}",
        "sub": "uid-dana",
        "email": "dana@example.com",
        "name": "Dana Levi",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    claims.update(overrides)
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256")


users = FirebaseUserRepository(PROJECT, FakeSigningKeys())


async def test_returns_the_user_who_signed_in() -> None:
    assert await users.from_token(make_token()) == User(
        id="uid-dana", email="dana@example.com", display_name="Dana Levi"
    )


async def test_uses_the_email_as_display_name_when_the_token_has_no_name() -> None:
    user = await users.from_token(make_token(name=None))

    assert user is not None
    assert user.display_name == "dana@example.com"


@pytest.mark.parametrize(
    "token",
    [
        make_token(aud="another-project"),
        make_token(iss="https://securetoken.google.com/another-project"),
        make_token(exp=datetime.now(UTC) - timedelta(minutes=1)),
        make_token(sub=None),
        make_token(sub=""),
        make_token(email=None),
        make_token(key=OTHER_KEY),
        "not-a-jwt",
    ],
    ids=[
        "audience",
        "issuer",
        "expired",
        "no-user",
        "empty-user",
        "no-email",
        "wrong-key",
        "garbage",
    ],
)
async def test_rejects_a_token_firebase_did_not_issue_for_this_project(token: str) -> None:
    assert await users.from_token(token) is None


async def test_fails_as_a_server_error_when_googles_keys_are_unreachable() -> None:
    unreachable = FirebaseUserRepository(PROJECT, FakeSigningKeys(jwt.PyJWKClientConnectionError()))

    with pytest.raises(jwt.PyJWKClientConnectionError):
        await unreachable.from_token(make_token())
