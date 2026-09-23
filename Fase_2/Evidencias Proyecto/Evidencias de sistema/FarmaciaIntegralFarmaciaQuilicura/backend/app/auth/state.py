"""Límites de login de un único proceso. Las sesiones se guardan en PostgreSQL."""

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic
from uuid import uuid4


class LoginLimited(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds


class AuthState:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.lock = Lock()
        self.attempts: dict[str, deque[tuple[str, float]]] = {}
        self.window = 15 * 60

    def _prune(self):
        now = self.clock()
        for key in list(self.attempts):
            entries = self.attempts[key]
            while entries and entries[0][1] <= now:
                entries.popleft()
            if not entries:
                del self.attempts[key]

    def _wait(self, email: str, ip: str) -> int:
        waits = [
            ceil(self.attempts[key][0][1] - self.clock())
            for key, limit in (("email:" + email.lower(), 8), ("ip:" + ip, 40))
            if len(self.attempts.get(key, ())) >= limit
        ]
        return max([0, *waits])

    def begin_login(self, email: str, ip: str) -> str:
        with self.lock:
            self._prune()
            wait = self._wait(email, ip)
            if wait:
                raise LoginLimited(wait)
            ticket = uuid4().hex
            # Reservar antes de Argon2 evita superar el límite con peticiones paralelas.
            for key in ("email:" + email.lower(), "ip:" + ip):
                self.attempts.setdefault(key, deque()).append(
                    (ticket, self.clock() + self.window)
                )
            return ticket

    def finish_login(self, email: str, ip: str, ticket: str, success: bool) -> int:
        with self.lock:
            self._prune()
            key = "email:" + email.lower()
            if success and key in self.attempts:
                self.attempts[key] = deque(
                    entry for entry in self.attempts[key] if entry[0] != ticket
                )
            return self._wait(email, ip)
