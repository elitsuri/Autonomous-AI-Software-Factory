import time
from collections import defaultdict, deque
from collections.abc import Callable

from starlette.requests import Request
from starlette.responses import JSONResponse


class SlidingWindowRateLimitMiddleware:
    def __init__(self, app: Callable, *, requests: int, window_seconds: int) -> None:
        self.app = app
        self.requests = requests
        self.window_seconds = window_seconds
        self._visits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        client = request.client.host if request.client else "anonymous"
        now = time.time()
        visits = self._visits[client]
        while visits and visits[0] < now - self.window_seconds:
            visits.popleft()

        if len(visits) >= self.requests:
            response = JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
            await response(scope, receive, send)
            return

        visits.append(now)
        await self.app(scope, receive, send)

