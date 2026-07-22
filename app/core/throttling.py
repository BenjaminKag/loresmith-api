from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class AIUserThrottle(SimpleRateThrottle):
    """
    Limit how often a single authenticated user can call AI endpoints.
    """

    scope = "ai"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        ident = user.pk
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AuthRateThrottle(AnonRateThrottle):
    """
    Limit attempts against auth endpoints (login, registration) by IP,
    to slow down brute-force and mass account creation attempts.
    """

    scope = "auth"
