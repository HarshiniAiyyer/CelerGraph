import time
from typing import Dict, Tuple
from collections import deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RateLimiter:
    def __init__(self) -> None:
        self.store: Dict[str, deque] = {}

    def allow(self, key: str, limit: int, window: float) -> Tuple[bool, int]:
        now = time.time()
        q = self.store.get(key)
        if q is None:
            q = deque()
            self.store[key] = q
        while q and now - q[0] > window:
            q.popleft()
        if len(q) < limit:
            q.append(now)
            return True, limit - len(q)
        return False, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rules: Dict[str, Tuple[int, float]]) -> None:
        super().__init__(app)
        self.rules = rules
        self.limiter = RateLimiter()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        rule = None
        if path in self.rules:
            rule = self.rules[path]
        else:
            for p, r in self.rules.items():
                if p.endswith("*") and path.startswith(p[:-1]):
                    rule = r
                    break
        if rule is None:
            return await call_next(request)
        limit, window = rule
        client = request.client
        ident = client.host if client else "unknown"
        key = f"{ident}:{path}"
        ok, remaining = self.limiter.allow(key, limit, window)
        if not ok:
            return Response(status_code=429)
        resp = await call_next(request)
        resp.headers["X-RateLimit-Limit"] = str(limit)
        resp.headers["X-RateLimit-Remaining"] = str(remaining)
        return resp
