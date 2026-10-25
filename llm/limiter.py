import threading
import time
from collections import deque

SAFETY = 0.9
WINDOW = 60.0

_windows = {}
_lock = threading.Lock()


class TokenWindow:
    def __init__(self, limit, window=WINDOW):
        self.limit = int(limit * SAFETY)
        self.window = window
        self.events = deque()
        self.lock = threading.Lock()

    def _used(self, now):
        while self.events and now - self.events[0][0] > self.window:
            self.events.popleft()
        return sum(n for _, n in self.events)

    def reserve(self, need):
        if self.limit <= 0:
            return None
        need = min(need, self.limit)
        while True:
            with self.lock:
                now = time.monotonic()
                if self._used(now) + need <= self.limit:
                    item = [now, need]
                    self.events.append(item)
                    return item
                wait = self.window - (now - self.events[0][0]) + 0.05
            time.sleep(max(0.05, wait))

    def settle(self, item, actual):
        if item is not None:
            with self.lock:
                item[1] = actual


def window_for(key, limit):
    with _lock:
        if key not in _windows:
            _windows[key] = TokenWindow(limit)
        return _windows[key]
