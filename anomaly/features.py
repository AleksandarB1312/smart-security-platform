from collections import defaultdict, deque

WINDOW_SIZE = 5


class RollingHistory:
    def __init__(self, window_size=WINDOW_SIZE):
        self.window_size = window_size
        self.history = defaultdict(lambda: deque(maxlen=window_size))

    def add_and_extract(self, device_id, value):
        previous_values = list(self.history[device_id])
        self.history[device_id].append(value)

        rolling_mean = sum(previous_values) / len(previous_values) if previous_values else value
        deviation = abs(value - rolling_mean)

        return [value, deviation]
