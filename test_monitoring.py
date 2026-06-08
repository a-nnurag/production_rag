from app.monitoring import (
    get_logger,
    MetricsCollector,
    RequestTime,
)

import time

logger = get_logger()
metrics = MetricsCollector()

print("=== Testing Logger ===")

logger.info(
    "application_started",
    extra={
        "extra_data": {
            "thread_id": "thread_123",
            "user_id": "user_456",
            "request_id": "req_789"
        }
    }
)

print("\n=== Testing Request Timer ===")

with RequestTime() as timer:
    time.sleep(0.25)

print(f"Elapsed: {timer.elapsed_ms:.2f} ms")

print("\n=== Testing Metrics ===")

metrics.record_request(
    latency_ms=120,
    input_tokens=100,
    output_tokens=50,
    cache_hit=True
)

metrics.record_request(
    latency_ms=200,
    input_tokens=80,
    output_tokens=40,
    cache_hit=False
)

metrics.record_request(
    latency_ms=500,
    input_tokens=120,
    output_tokens=90,
    error=True,
    cache_hit=False
)

print(metrics.stats)

print("\n=== Testing Logger With Metrics ===")

logger.info(
    "request_completed",
    extra={
        "extra_data": {
            "latency_ms": timer.elapsed_ms,
            "cache_hit": True,
            "input_tokens": 100,
            "output_tokens": 50,
        }
    }
)