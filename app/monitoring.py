import logging
import json
import time
from datetime import datetime,timezone
from functools import wraps
from typing import Any,Callable

class JSONFormatter(logging.Formatter):
    """Format log records as JSON log aggregation (ELK,Datadog,etc)"""

    def format(self,record):
        log_obj= {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        #Merge any extra data attached to the record
        if hasattr(record,"extra_data"):
            log_obj.update(record.extra_data)
        return json.dumps(log_obj)


def get_logger(name:str ="production_api")-> logging.Logger:
    """Create a structured JSON logger"""
    logger =logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger



# ======Metrics Collector ======
class MetricsCollector:
    """
    Collects and aggregates application metrics.

    In production, replace with Prometheus client.
    """

    def __init__(self):
        self._requests_total = 0
        self._errors_total = 0

        self._latency_sum = 0.0
        self._latency_count = 0
        self._latency_min = float("inf")
        self._latency_max = 0.0

        self._tokens_input = 0
        self._tokens_output = 0

        self._cache_hits = 0
        self._cache_misses = 0

        self._started_at = time.time()

    def record_request(
        self,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        error: bool = False,
        cache_hit: bool = False,
    ):
        """Record metrics for a request."""

        self._requests_total += 1

        if error:
            self._errors_total += 1

        self._latency_sum += latency_ms
        self._latency_count += 1

        self._latency_min = min(self._latency_min, latency_ms)
        self._latency_max = max(self._latency_max, latency_ms)

        self._tokens_input += input_tokens
        self._tokens_output += output_tokens

        if cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

    @property
    def stats(self) -> dict:
        """Return aggregated metrics."""

        avg_latency = (
            self._latency_sum / self._latency_count
            if self._latency_count > 0
            else 0.0
        )

        cache_total = self._cache_hits + self._cache_misses
        cache_hit_rate = (
            self._cache_hits / cache_total * 100
            if cache_total > 0
            else 0.0
        )

        error_rate = (
            self._errors_total / self._requests_total * 100
            if self._requests_total > 0
            else 0.0
        )

        return {
            "requests_total": self._requests_total,
            "errors_total": self._errors_total,
            "error_rate_percent": round(error_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": (
                round(self._latency_min, 2)
                if self._latency_count > 0
                else 0.0
            ),
            "max_latency_ms": round(self._latency_max, 2),
            "input_tokens": self._tokens_input,
            "output_tokens": self._tokens_output,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "uptime_seconds": round(
                time.time() - self._started_at, 2
            ),
        }
    
    

class RequestTime:
    """Context manager for time requests"""

    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        self.elapsed_ms = (time.time() - self.start_time) * 1000
