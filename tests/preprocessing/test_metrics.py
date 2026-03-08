from preprocessing.metrics import Metrics


def test_average_time_initially_zero():
    metrics = Metrics()
    assert metrics.average_time() == 0.0


def test_register_updates_internal_state():
    metrics = Metrics()

    metrics.register(1.0)
    metrics.register(3.0)

    assert metrics.count == 2
    assert metrics.total_time == 4.0
    assert metrics.average_time() == 2.0
