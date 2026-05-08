"""shared/throttling.py — T-3-004: rate limiting."""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class BurstRateThrottle(UserRateThrottle):
    """Burst защита — max 60 запросов/мин."""
    scope = "burst"


class SustainedRateThrottle(UserRateThrottle):
    """Долгий лимит — 5000/день."""
    scope = "sustained"


class LoginRateThrottle(AnonRateThrottle):
    """Brute-force защита для login: max 10/мин."""
    scope = "login"


class TransitionRateThrottle(UserRateThrottle):
    """FSM transitions: max 120/мин."""
    scope = "transition"
