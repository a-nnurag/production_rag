from app.cache import ResponseCache
import time

cache = ResponseCache(ttl_seconds=3)

query = "What is RAG?"

print("\n=== First Query ===")
result = cache.get(query)

if result is None:
    print("Cache MISS - No lookup found")
    response = "RAG stands for Retrieval Augmented Generation"
    cache.set(query, response)

print("\n=== Second Query (same query) ===")
result = cache.get(query)

if result is None:
    print("Cache MISS")
else:
    print("Cache HIT")
    print("Response:", result)

print("\n=== Waiting for TTL expiry ===")
time.sleep(4)

print("\n=== Third Query (after TTL expires) ===")
result = cache.get(query)

if result is None:
    print("Cache MISS - Entry expired")
else:
    print("Cache HIT")
    print("Response:", result)

print("\n=== Cache Stats ===")
print(cache.stats)