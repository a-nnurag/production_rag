"""
In-memory cache with TTL for LLM response duplication
"""

import hashlib
import time
from typing import Optional


class ResponseCache:
    """
        In-memory cache with TTL for LLM response duplication

        In production replace with Redis for:
        -Persistance across restarts
        -Shared cache across multiple instances
        -Built-in TTL management
    """

    def __init__(self,ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self.cache :dict[str, dict] = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self,query: str)-> str:
        """Create a hash key for the given query"""
        normalized_query = query.lower().strip()
        return hashlib.sha256(normalized_query.encode()).hexdigest()
    
    def get(self,query:str) -> Optional[str]:
        """Get cached response for the query if it exists and
          is not expired
          Returns None if no valid cache entry is found
        """
        key = self._make_key(query)
        
        if key in self.cache:
            entry = self.cache[key]
            #Check TTL
            if time.time() - entry['timestamp'] < self.ttl:
                self.hits += 1
                return entry['response']
            else:
                del self.cache[key]  # Remove expired entry
        self.misses += 1
        return None
    
    def set(self,query:str,response:str)->None:
        """Cache the response for the given query with current timestamp"""
        key = self._make_key(query)
        self.cache[key] = {
            'response': response,
            'timestamp': time.time(),
            'query': query
        }
    
    @property
    def stats(self)-> dict:
        """Return cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'cache_entries': len(self.cache)
        }
                

    
  