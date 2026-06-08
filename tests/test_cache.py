"""
Test suite for ResponseCache (cache.py)
Pattern: AAA (Arrange, Act, Assert)
Coverage: _make_key, get, set, TTL expiry, stats, edge cases
"""

import time
import pytest
from unittest.mock import patch
from app.cache import ResponseCache


# ==============================================================================
# _make_key Tests
# ==============================================================================

class TestMakeKey:

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache()

    def test_same_query_produces_same_key(self):
        # Arrange
        query = "What is machine learning?"
        # Act
        key1 = self.cache._make_key(query)
        key2 = self.cache._make_key(query)
        # Assert
        assert key1 == key2

    def test_different_queries_produce_different_keys(self):
        # Arrange
        query1 = "What is machine learning?"
        query2 = "What is deep learning?"
        # Act
        key1 = self.cache._make_key(query1)
        key2 = self.cache._make_key(query2)
        # Assert
        assert key1 != key2

    def test_key_is_normalized_lowercase(self):
        # Arrange
        query_lower = "hello world"
        query_upper = "HELLO WORLD"
        # Act
        key1 = self.cache._make_key(query_lower)
        key2 = self.cache._make_key(query_upper)
        # Assert
        assert key1 == key2

    def test_key_is_normalized_strips_whitespace(self):
        # Arrange
        query_clean = "hello world"
        query_padded = "  hello world  "
        # Act
        key1 = self.cache._make_key(query_clean)
        key2 = self.cache._make_key(query_padded)
        # Assert
        assert key1 == key2

    def test_key_is_sha256_hex_string(self):
        # Arrange
        query = "test query"
        # Act
        key = self.cache._make_key(query)
        # Assert
        assert len(key) == 64                    # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in key)

    def test_empty_string_produces_valid_key(self):
        # Arrange
        query = ""
        # Act
        key = self.cache._make_key(query)
        # Assert
        assert isinstance(key, str)
        assert len(key) == 64


# ==============================================================================
# ResponseCache.set Tests
# ==============================================================================

class TestResponseCacheSet:

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache()

    def test_set_stores_entry_in_cache(self):
        # Arrange
        query = "What is AI?"
        response = "AI is artificial intelligence."
        # Act
        self.cache.set(query, response)
        # Assert
        assert len(self.cache.cache) == 1

    def test_set_stores_correct_response(self):
        # Arrange
        query = "What is AI?"
        response = "AI is artificial intelligence."
        # Act
        self.cache.set(query, response)
        key = self.cache._make_key(query)
        # Assert
        assert self.cache.cache[key]["response"] == response

    def test_set_stores_timestamp(self):
        # Arrange
        query = "What is AI?"
        response = "AI is artificial intelligence."
        before = time.time()
        # Act
        self.cache.set(query, response)
        after = time.time()
        key = self.cache._make_key(query)
        # Assert
        assert before <= self.cache.cache[key]["timestamp"] <= after

    def test_set_stores_original_query(self):
        # Arrange
        query = "What is AI?"
        response = "AI is artificial intelligence."
        # Act
        self.cache.set(query, response)
        key = self.cache._make_key(query)
        # Assert
        assert self.cache.cache[key]["query"] == query

    def test_set_overwrites_existing_entry(self):
        # Arrange
        query = "What is AI?"
        first_response = "First answer."
        second_response = "Updated answer."
        self.cache.set(query, first_response)
        # Act
        self.cache.set(query, second_response)
        key = self.cache._make_key(query)
        # Assert
        assert self.cache.cache[key]["response"] == second_response
        assert len(self.cache.cache) == 1

    def test_set_multiple_entries(self):
        # Arrange
        entries = {
            "query one": "response one",
            "query two": "response two",
            "query three": "response three",
        }
        # Act
        for q, r in entries.items():
            self.cache.set(q, r)
        # Assert
        assert len(self.cache.cache) == 3

    def test_set_returns_none(self):
        # Arrange
        query = "Hello"
        response = "Hi there"
        # Act
        result = self.cache.set(query, response)
        # Assert
        assert result is None


# ==============================================================================
# ResponseCache.get Tests
# ==============================================================================

class TestResponseCacheGet:

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache(ttl_seconds=300)

    def test_get_returns_none_on_cache_miss(self):
        # Arrange
        query = "Something not cached"
        # Act
        result = self.cache.get(query)
        # Assert
        assert result is None

    def test_get_returns_cached_response_on_hit(self):
        # Arrange
        query = "What is Python?"
        response = "Python is a programming language."
        self.cache.set(query, response)
        # Act
        result = self.cache.get(query)
        # Assert
        assert result == response

    def test_get_is_case_insensitive(self):
        # Arrange
        self.cache.set("what is python?", "Python is a language.")
        # Act
        result = self.cache.get("WHAT IS PYTHON?")
        # Assert
        assert result == "Python is a language."

    def test_get_is_whitespace_insensitive(self):
        # Arrange
        self.cache.set("hello world", "Hi there.")
        # Act
        result = self.cache.get("  hello world  ")
        # Assert
        assert result == "Hi there."

    def test_get_increments_hits_on_cache_hit(self):
        # Arrange
        self.cache.set("query", "response")
        initial_hits = self.cache.hits
        # Act
        self.cache.get("query")
        # Assert
        assert self.cache.hits == initial_hits + 1

    def test_get_increments_misses_on_cache_miss(self):
        # Arrange
        initial_misses = self.cache.misses
        # Act
        self.cache.get("nonexistent query")
        # Assert
        assert self.cache.misses == initial_misses + 1

    def test_get_does_not_increment_misses_on_hit(self):
        # Arrange
        self.cache.set("query", "response")
        initial_misses = self.cache.misses
        # Act
        self.cache.get("query")
        # Assert
        assert self.cache.misses == initial_misses

    def test_get_does_not_increment_hits_on_miss(self):
        # Arrange
        initial_hits = self.cache.hits
        # Act
        self.cache.get("nonexistent")
        # Assert
        assert self.cache.hits == initial_hits


# ==============================================================================
# TTL / Expiry Tests
# ==============================================================================

class TestResponseCacheTTL:

    def test_get_returns_none_for_expired_entry(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        cache.set("expiring query", "this will expire")
        # Act
        time.sleep(1.1)
        result = cache.get("expiring query")
        # Assert
        assert result is None

    def test_get_removes_expired_entry_from_cache(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        cache.set("expiring query", "this will expire")
        # Act
        time.sleep(1.1)
        cache.get("expiring query")
        # Assert
        assert len(cache.cache) == 0

    def test_get_returns_value_before_ttl_expires(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=5)
        cache.set("valid query", "still valid")
        # Act
        result = cache.get("valid query")
        # Assert
        assert result == "still valid"

    def test_expired_entry_increments_misses(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        cache.set("expiring query", "response")
        time.sleep(1.1)
        initial_misses = cache.misses
        # Act
        cache.get("expiring query")
        # Assert
        assert cache.misses == initial_misses + 1

    def test_ttl_zero_expires_immediately(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=0)
        cache.set("instant expire", "gone")
        # Act
        time.sleep(0.01)
        result = cache.get("instant expire")
        # Assert
        assert result is None

    def test_mocked_time_expiry(self):
        # Arrange — use mock to avoid real sleep
        cache = ResponseCache(ttl_seconds=300)
        cache.set("query", "response")
        key = cache._make_key("query")
        # Act — backdate the timestamp to simulate expiry
        cache.cache[key]["timestamp"] = time.time() - 301
        result = cache.get("query")
        # Assert
        assert result is None


# ==============================================================================
# Stats Tests
# ==============================================================================

class TestResponseCacheStats:

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache()

    def test_stats_initial_state(self):
        # Arrange — fresh cache
        # Act
        stats = self.cache.stats
        # Assert
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["cache_entries"] == 0

    def test_stats_reflects_cache_entries(self):
        # Arrange
        self.cache.set("q1", "r1")
        self.cache.set("q2", "r2")
        # Act
        stats = self.cache.stats
        # Assert
        assert stats["cache_entries"] == 2

    def test_stats_reflects_hits(self):
        # Arrange
        self.cache.set("query", "response")
        self.cache.get("query")
        self.cache.get("query")
        # Act
        stats = self.cache.stats
        # Assert
        assert stats["hits"] == 2

    def test_stats_reflects_misses(self):
        # Arrange
        self.cache.get("miss one")
        self.cache.get("miss two")
        self.cache.get("miss three")
        # Act
        stats = self.cache.stats
        # Assert
        assert stats["misses"] == 3

    def test_stats_returns_dict(self):
        # Arrange — fresh cache
        # Act
        stats = self.cache.stats
        # Assert
        assert isinstance(stats, dict)

    def test_stats_has_required_keys(self):
        # Arrange — fresh cache
        # Act
        stats = self.cache.stats
        # Assert
        assert "hits" in stats
        assert "misses" in stats
        assert "cache_entries" in stats

    def test_stats_cache_entries_decreases_after_expiry(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        cache.set("temp", "value")
        assert cache.stats["cache_entries"] == 1
        time.sleep(1.1)
        # Act — get triggers eviction of expired entry
        cache.get("temp")
        stats = cache.stats
        # Assert
        assert stats["cache_entries"] == 0


# ==============================================================================
# Edge Case Tests
# ==============================================================================

class TestResponseCacheEdgeCases:

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache()

    def test_get_empty_string_query(self):
        # Arrange
        self.cache.set("", "empty response")
        # Act
        result = self.cache.get("")
        # Assert
        assert result == "empty response"

    def test_set_empty_response(self):
        # Arrange
        query = "What is nothing?"
        response = ""
        # Act
        self.cache.set(query, response)
        result = self.cache.get(query)
        # Assert
        assert result == ""

    def test_set_very_long_query(self):
        # Arrange
        query = "word " * 1000
        response = "Long query response."
        # Act
        self.cache.set(query, response)
        result = self.cache.get(query)
        # Assert
        assert result == response

    def test_set_very_long_response(self):
        # Arrange
        query = "Tell me everything"
        response = "answer " * 10000
        # Act
        self.cache.set(query, response)
        result = self.cache.get(query)
        # Assert
        assert result == response

    def test_set_special_characters_in_query(self):
        # Arrange
        query = "SELECT * FROM users WHERE id=1; DROP TABLE users;--"
        response = "Nice try."
        # Act
        self.cache.set(query, response)
        result = self.cache.get(query)
        # Assert
        assert result == response

    def test_multiple_gets_do_not_duplicate_hits(self):
        # Arrange
        self.cache.set("query", "response")
        # Act
        for _ in range(5):
            self.cache.get("query")
        # Assert
        assert self.cache.hits == 5

    def test_cache_default_ttl_is_300(self):
        # Arrange + Act
        cache = ResponseCache()
        # Assert
        assert cache.ttl == 300

    def test_cache_custom_ttl_is_set(self):
        # Arrange + Act
        cache = ResponseCache(ttl_seconds=60)
        # Assert
        assert cache.ttl == 60


# ==============================================================================
# Integration Tests — cache wired into full request flow
# ==============================================================================

class TestCacheIntegration:
    """
    Tests the cache as it behaves inside the full request pipeline:
    cache miss → agent invoked → response stored → cache hit → agent skipped
    The agent is mocked to isolate cache behaviour from LLM calls.
    """

    def setup_method(self):
        # Arrange (shared)
        self.cache = ResponseCache(ttl_seconds=300)
        self.mock_agent_call_count = 0

    def _fake_agent(self, query: str) -> dict:
        """Simulates agent.invoke() — counts calls so we can assert skips."""
        self.mock_agent_call_count += 1
        return {
            "response": f"Agent response for: {query}",
            "model_used": "primary",
            "error": None,
        }

    def _request(self, query: str) -> dict:
        """Simulates the /chat endpoint cache logic."""
        cached = self.cache.get(query)
        if cached is not None:
            return {"response": cached, "source": "cache"}

        result = self._fake_agent(query)
        self.cache.set(query, result["response"])
        return {"response": result["response"], "source": "agent"}

    # --- Cache miss → agent called ---

    def test_first_request_is_a_cache_miss(self):
        # Arrange
        query = "What is LangGraph?"
        # Act
        self._request(query)
        # Assert
        assert self.cache.misses == 1

    def test_first_request_calls_agent(self):
        # Arrange
        query = "What is LangGraph?"
        # Act
        self._request(query)
        # Assert
        assert self.mock_agent_call_count == 1

    def test_first_request_stores_response_in_cache(self):
        # Arrange
        query = "What is LangGraph?"
        # Act
        self._request(query)
        # Assert
        assert self.cache.get(query) is not None

    def test_first_request_returns_agent_response(self):
        # Arrange
        query = "What is LangGraph?"
        # Act
        result = self._request(query)
        # Assert
        assert result["source"] == "agent"
        assert "Agent response for" in result["response"]

    # --- Cache hit → agent skipped ---

    def test_second_request_is_a_cache_hit(self):
        # Arrange
        query = "What is LangGraph?"
        self._request(query)          # warms the cache
        # Act
        self._request(query)
        # Assert
        assert self.cache.hits == 1

    def test_second_request_skips_agent(self):
        # Arrange
        query = "What is LangGraph?"
        self._request(query)          # warms the cache
        # Act
        self._request(query)
        # Assert
        assert self.mock_agent_call_count == 1   # still 1 — agent not called again

    def test_second_request_returns_cached_response(self):
        # Arrange
        query = "What is LangGraph?"
        first = self._request(query)
        # Act
        second = self._request(query)
        # Assert
        assert second["response"] == first["response"]
        assert second["source"] == "cache"

    # --- Multiple unique queries ---

    def test_different_queries_each_call_agent_once(self):
        # Arrange
        queries = ["query one", "query two", "query three"]
        # Act
        for q in queries:
            self._request(q)
            self._request(q)   # second call should hit cache
        # Assert
        assert self.mock_agent_call_count == 3   # one agent call per unique query

    def test_different_queries_accumulate_cache_entries(self):
        # Arrange
        queries = ["alpha", "beta", "gamma"]
        # Act
        for q in queries:
            self._request(q)
        # Assert
        assert self.cache.stats["cache_entries"] == 3

    # --- TTL expiry in pipeline ---

    def test_expired_cache_entry_calls_agent_again(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        call_count = 0

        def fake_agent(query):
            nonlocal call_count
            call_count += 1
            return {"response": f"response for {query}", "model_used": "primary"}

        def request(query):
            cached = cache.get(query)
            if cached:
                return {"response": cached, "source": "cache"}
            result = fake_agent(query)
            cache.set(query, result["response"])
            return {"response": result["response"], "source": "agent"}

        query = "expiring question"
        request(query)               # first call — agent invoked, cached
        time.sleep(1.1)              # let TTL expire
        # Act
        result = request(query)      # second call — cache expired, agent called again
        # Assert
        assert call_count == 2
        assert result["source"] == "agent"

    def test_expired_entry_gets_refreshed_in_cache(self):
        # Arrange
        cache = ResponseCache(ttl_seconds=1)
        query = "refresh me"
        cache.set(query, "old response")
        time.sleep(1.1)
        # Act — simulate request that misses and re-caches
        cache.get(query)             # triggers eviction
        cache.set(query, "new response")
        result = cache.get(query)
        # Assert
        assert result == "new response"

    # --- Stats reflect full pipeline flow ---

    def test_stats_after_mixed_hits_and_misses(self):
        # Arrange
        self._request("unique query 1")   # miss
        self._request("unique query 2")   # miss
        self._request("unique query 1")   # hit
        self._request("unique query 2")   # hit
        self._request("unique query 2")   # hit
        # Act
        stats = self.cache.stats
        # Assert
        assert stats["misses"] == 2
        assert stats["hits"] == 3
        assert stats["cache_entries"] == 2

    def test_stats_cache_entries_does_not_grow_on_repeated_queries(self):
        # Arrange
        query = "same question every time"
        # Act
        for _ in range(10):
            self._request(query)
        # Assert
        assert self.cache.stats["cache_entries"] == 1