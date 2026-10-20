"""Builds the users module's services, for the deployables that host them."""

import jwt

from modules.users.repositories.debug_users import DebugUserRepository
from modules.users.repositories.firebase_users import FIREBASE_SIGNING_KEYS, FirebaseUserRepository
from modules.users.services.auth import Auth


def create_auth(
    firebase_project_id: str, debug_user_jwt: str | None = None, debug_user_name: str = "Debug User"
) -> Auth:
    """Signs users in with the Firebase Auth project's ID tokens. Given a debug user's token,
    it signs in only that user, named `debug_user_name`, and Firebase signs in nobody."""
    if debug_user_jwt:
        return Auth(DebugUserRepository(debug_user_jwt, debug_user_name))
    return Auth(FirebaseUserRepository(firebase_project_id, jwt.PyJWKClient(FIREBASE_SIGNING_KEYS)))
