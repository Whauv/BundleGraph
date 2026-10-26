"""Authentication boundary; production defaults to denial until configured."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Identity:
    subject: str
    roles: frozenset[str]


class AuthenticationProvider(Protocol):
    def authenticate(self, authorization: str | None) -> Identity | None: ...


class RejectingAuthenticationProvider:
    def authenticate(self, authorization: str | None) -> Identity | None:
        return None
