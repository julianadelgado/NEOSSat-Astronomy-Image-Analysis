class Metrics:

    def __init__(self):
        self.total_time = 0.0
        self.count = 0

    def register(self, duration: float):
        self.total_time += duration
        self.count += 1

    def average_time(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_time / self.count