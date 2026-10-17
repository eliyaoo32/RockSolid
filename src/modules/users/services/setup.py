"""Builds the users module's services, for the deployables that host them."""

import jwt

from modules.users.repositories.firebase_users import FIREBASE_SIGNING_KEYS, FirebaseUserRepository
from modules.users.services.auth import Auth


def create_auth(firebase_project_id: str) -> Auth:
    """Signs users in with the Firebase Auth project's ID tokens."""
    return Auth(FirebaseUserRepository(firebase_project_id, jwt.PyJWKClient(FIREBASE_SIGNING_KEYS)))
