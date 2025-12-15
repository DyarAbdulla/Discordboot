"""
Intelligent Caching System for Discord Bot
Caches responses, translations, and common queries
"""

import hashlib
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import OrderedDict
import asyncio


class CacheManager:
    """Manages intelligent caching for bot responses"""
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of cached items
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Cache TTLs (Time To Live) in seconds
        self.ttls = {
            "greeting": timedelta(hours=1),  # Greetings cached for 1 hour
            "common_question": timedelta(hours=1),  # Common questions 1 hour
            "translation": timedelta(hours=24),  # Translations 24 hours
            "help": timedelta(days=7),  # Help content 7 days
            "static": None,  # Static content never expires
            "default": timedelta(minutes=30)  # Default 30 minutes
        }
    
    def _generate_key(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Generate cache key from query and context
        
        Args:
            query: User query
            context: Optional context (language, etc.)
            
        Returns:
            Cache key string
        """
        # Normalize query (lowercase, strip whitespace)
        normalized = query.lower().strip()
        
        # Add context to key if provided
        if context:
            context_str = json.dumps(context, sort_keys=True)
            normalized += context_str
        
        # Generate hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _classify_query_type(self, query: str) -> str:
        """
        Classify query type for appropriate TTL
        
        Args:
            query: User query
            
        Returns:
            Query type string
        """
        query_lower = query.lower()
        
        # Greetings
        if any(word in query_lower for word in ["hello", "hi", "hey", "greetings", "سڵاو", "merheba"]):
            return "greeting"
        
        # Common questions
        common_questions = ["what is", "how does", "explain", "tell me about"]
        if any(phrase in query_lower for phrase in common_questions):
            return "common_question"
        
        # Translation
        if any(word in query_lower for word in ["translate", "translation", "ترجم"]):
            return "translation"
        
        # Help
        if any(word in query_lower for word in ["help", "commands", "what can you do"]):
            return "help"
        
        return "default"
    
    def get(self, query: str, context: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available
        
        Args:
            query: User query
            context: Optional context
            
        Returns:
            Cached response dict or None
        """
        key = self._generate_key(query, context)
        
        if key not in self.cache:
            self.cache_stats["misses"] += 1
            return None
        
        cached_item = self.cache[key]
        
        # Check if expired
        query_type = cached_item.get("query_type", "default")
        ttl = self.ttls.get(query_type, self.ttls["default"])
        
        if ttl:
            cache_time = datetime.fromisoformat(cached_item["timestamp"])
            if datetime.now() - cache_time > ttl:
                # Expired - remove from cache
                del self.cache[key]
                self.cache_stats["misses"] += 1
                return None
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
        self.cache_stats["hits"] += 1
        
        return cached_item["response"]
    
    def set(self, query: str, response: Dict[str, Any], context: Optional[Dict] = None):
        """
        Cache a response
        
        Args:
            query: User query
            response: Response to cache
            context: Optional context
        """
        key = self._generate_key(query, context)
        query_type = self._classify_query_type(query)
        
        # Remove oldest if cache full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Remove oldest
            self.cache_stats["evictions"] += 1
        
        # Store in cache
        self.cache[key] = {
            "response": response,
            "query_type": query_type,
            "timestamp": datetime.now().isoformat(),
            "query": query[:100]  # Store first 100 chars for debugging
        }
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
    
    def clear(self, query_type: Optional[str] = None):
        """
        Clear cache
        
        Args:
            query_type: Optional specific type to clear, or None for all
        """
        if query_type:
            # Clear specific type
            keys_to_remove = [
                key for key, item in self.cache.items()
                if item.get("query_type") == query_type
            ]
            for key in keys_to_remove:
                del self.cache[key]
        else:
            # Clear all
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.cache_stats["evictions"]
        }
    
    def get_cache_breakdown(self) -> Dict[str, int]:
        """Get breakdown of cache by query type"""
        breakdown = {}
        for item in self.cache.values():
            query_type = item.get("query_type", "default")
            breakdown[query_type] = breakdown.get(query_type, 0) + 1
        return breakdown

