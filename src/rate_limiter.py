"""분당 Tool 호출 횟수 제한. 고정 1분 윈도우."""
import threading
import time

from . import config


class RateLimitExceeded(Exception):
    """분당 한도 초과 시 발생."""
    def __init__(self, message: str = "분당 요청 한도를 초과했습니다."):
        self.message = message
        super().__init__(message)


_lock = threading.Lock()
_window_key: int = 0
_count: int = 0


def check_and_consume() -> None:
    """Tool 호출 1건으로 간주하고, 한도 내면 카운트 증가. 초과 시 RateLimitExceeded 발생."""
    if config.RATE_LIMIT_RPM <= 0:
        return
    now = time.time()
    current_window = int(now // 60)
    with _lock:
        global _window_key, _count
        if current_window != _window_key:
            _window_key = current_window
            _count = 0
        _count += 1
        if _count > config.RATE_LIMIT_RPM:
            raise RateLimitExceeded(
                f"분당 요청 한도를 초과했습니다. (한도: {config.RATE_LIMIT_RPM}회/분)"
            )
