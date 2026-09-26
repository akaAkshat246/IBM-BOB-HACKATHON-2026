"""
users.py — User model and lookup.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Profile:
    display_name: str
    bio: str = ""


@dataclass
class User:
    id: str
    email: str
    profile: Optional[Profile] = None   # None for OAuth users who never completed setup


_USERS_DB = {
    "u1": User(id="u1", email="alice@example.com",
               profile=Profile(display_name="Alice")),
    # u2 was created via OAuth; profile was never set up
    "u2": User(id="u2", email="bob@example.com", profile=None),
}


def get_user(user_id: str) -> User:
    """Fetch a user by ID.
    BUG: Returns a User with profile=None for OAuth users, but callers
         do not check for this before accessing user.profile.display_name.
    """
    user = _USERS_DB.get(user_id)
    if user is None:
        raise KeyError(f"No user with id={user_id!r}")
    return user
