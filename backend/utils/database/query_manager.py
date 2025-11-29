"""
Enhanced Query Manager with Database Statistics Logging
LRU caching, TTL, lazy loading, and comprehensive analytics
"""
import importlib
import time
import csv
from collections import OrderedDict
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DatabaseStatsLogger:
    """Database logger for query usage statistics"""
    
    def __init__(self, db_connection_func):
        self.get_db_connection = db_connection_func
    
    def log_query_usage(self, category: str, query_name: str, cache_hit: bool, 
                       response_time_ms: float, user_id: int = None, 
                       endpoint: str = None, app_version: str = None):
        """Log query usage to database"""
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO query_usage_stats 
                    (timestamp, category, query_name, cache_hit, response_time_ms, user_id, endpoint, application_version)
                    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)
                """, (category, query_name, cache_hit, round(response_time_ms, 2), user_id, endpoint, app_version))
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log query usage to database: {e}")

    def get_usage_stats(self, days: int = 30, category: str = None) -> Dict[str, Any]:
        """Get comprehensive usage statistics from database"""
        try:
            conn = self.get_db_connection()
            with conn.cursor() as cursor:
                where_clause = "WHERE timestamp >= %s"
                params = [datetime.now() - timedelta(days=days)]
                
                if category:
                    where_clause += " AND category = %s"
                    params.append(category)
                
                # Basic summary
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_queries,
                        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                        AVG(response_time_ms) as avg_response_time,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time
                    FROM query_usage_stats
                    {where_clause}
                """, params)
                summary = cursor.fetchone()
                
                # Top queries by usage
                cursor.execute(f"""
                    SELECT 
                        category, 
                        query_name, 
                        COUNT(*) as usage_count,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                    FROM query_usage_stats
                    {where_clause}
                    GROUP BY category, query_name
                    ORDER BY usage_count DESC
                    LIMIT 15
                """, params)
                top_queries = cursor.fetchall()
                
                # Cache performance by category
                cursor.execute(f"""
                    SELECT 
                        category,
                        COUNT(*) as total_queries,
                        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                        AVG(response_time_ms) as avg_response_time
                    FROM query_usage_stats
                    {where_clause}
                    GROUP BY category
                    ORDER BY total_queries DESC
                """, params)
                category_stats = cursor.fetchall()
                
                # Daily trends
                cursor.execute(f"""
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as total_queries,
                        SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                        AVG(response_time_ms) as avg_response_time
                    FROM query_usage_stats
                    {where_clause}
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    LIMIT 30
                """, params)
                daily_trends = cursor.fetchall()
                
                # Slow queries (above 100ms)
                cursor.execute(f"""
                    SELECT 
                        category,
                        query_name,
                        COUNT(*) as call_count,
                        AVG(response_time_ms) as avg_response_time,
                        MAX(response_time_ms) as max_response_time
                    FROM query_usage_stats
                    WHERE response_time_ms > 100
                    GROUP BY category, query_name
                    HAVING COUNT(*) >= 5
                    ORDER BY avg_response_time DESC
                    LIMIT 10
                """)
                slow_queries = cursor.fetchall()
                
            conn.close()
            
            return {
                "summary": {
                    "total_queries": summary[0] or 0,
                    "cache_hits": summary[1] or 0,
                    "cache_misses": (summary[0] or 0) - (summary[1] or 0),
                    "cache_hit_ratio": round((summary[1] or 0) / (summary[0] or 1), 3),
                    "avg_response_time_ms": round(float(summary[2] or 0), 2),
                    "p95_response_time_ms": round(float(summary[3] or 0), 2),
                    "min_response_time_ms": round(float(summary[4] or 0), 2),
                    "max_response_time_ms": round(float(summary[5] or 0), 2)
                },
                "top_queries": [
                    {
                        "category": row[0],
                        "query_name": row[1],
                        "usage_count": row[2],
                        "avg_response_time_ms": round(float(row[3]), 2),
                        "cache_hit_ratio": round(row[4] / row[2], 3) if row[2] > 0 else 0
                    } for row in top_queries
                ],
                "category_performance": [
                    {
                        "category": row[0],
                        "total_queries": row[1],
                        "cache_hits": row[2],
                        "cache_hit_ratio": round(row[2] / row[1], 3) if row[1] > 0 else 0,
                        "avg_response_time_ms": round(float(row[3]), 2)
                    } for row in category_stats
                ],
                "daily_trends": [
                    {
                        "date": row[0].isoformat(),
                        "total_queries": row[1],
                        "cache_hits": row[2],
                        "cache_hit_ratio": round(row[2] / row[1], 3) if row[1] > 0 else 0,
                        "avg_response_time_ms": round(float(row[3]), 2)
                    } for row in daily_trends
                ],
                "slow_queries": [
                    {
                        "category": row[0],
                        "query_name": row[1],
                        "call_count": row[2],
                        "avg_response_time_ms": round(float(row[3]), 2),
                        "max_response_time_ms": round(float(row[4]), 2)
                    } for row in slow_queries
                ]
            }
                
        except Exception as e:
            logger.error(f"Failed to get usage stats from database: {e}")
            return {"error": str(e)}

class QueryManager:
    def __init__(self, queries_package: str = "queries", cache_size: int = 100, 
                 ttl_seconds: int = 300, preload_categories: List[str] = None,
                 stats_logger: DatabaseStatsLogger = None):
        self.queries_package = queries_package
        self.cache_size = cache_size
        self.ttl_seconds = ttl_seconds
        self.stats_logger = stats_logger
        
        self._queries_cache: Dict[str, Dict[str, str]] = {}
        self._cache: OrderedDict[str, Tuple[str, float]] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._daily_usage: Dict[str, Dict[str, int]] = {}
        self._query_usage: Dict[str, int] = {}

        # Preload hot categories if provided
        if preload_categories:
            for category in preload_categories:
                self._load_query_module(category)
                for query_name, query in self._queries_cache.get(category, {}).items():
                    key = f"{category}.{query_name}"
                    self._cache[key] = (query, time.time())
            self._evict_if_needed()

    def _load_query_module(self, category: str):
        """Load queries for a category if not already loaded."""
        if category in self._queries_cache:
            return
        try:
            full_module_name = f"{self.queries_package}.{category}_queries"
            module = importlib.import_module(full_module_name)
            queries = {
                attr: getattr(module, attr)
                for attr in dir(module)
                if attr.isupper() and isinstance(getattr(module, attr), str)
            }
            self._queries_cache[category] = queries
            logger.info(f"Loaded {len(queries)} queries from category '{category}'")
        except ImportError:
            raise ValueError(f"Query category '{category}' not found")

    def _is_expired(self, timestamp: float) -> bool:
        return (time.time() - timestamp) > self.ttl_seconds

    def _evict_if_needed(self):
        while len(self._cache) > self.cache_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Evicted from cache: {evicted_key}")

    def _log_usage(self, key: str, hit: bool):
        """Log usage to in-memory counters"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self._daily_usage:
            self._daily_usage[today] = {"hits": 0, "misses": 0}
        if hit:
            self._daily_usage[today]["hits"] += 1
        else:
            self._daily_usage[today]["misses"] += 1

        # Track per-query usage
        self._query_usage[key] = self._query_usage.get(key, 0) + 1

    def get_query(self, category: str, query_name: str, user_id: int = None, 
                  endpoint: str = None, app_version: str = "1.0.0") -> str:
        """Get query with comprehensive logging"""
        start_time = time.time()
        key = f"{category}.{query_name}"
        
        # Check cache
        if key in self._cache:
            query, ts = self._cache[key]
            if not self._is_expired(ts):
                self._cache.move_to_end(key)
                self._hit_count += 1
                response_time = (time.time() - start_time) * 1000
                
                # Log to memory
                self._log_usage(key, hit=True)
                
                # Log to database
                if self.stats_logger:
                    self.stats_logger.log_query_usage(
                        category=category,
                        query_name=query_name,
                        cache_hit=True,
                        response_time_ms=response_time,
                        user_id=user_id,
                        endpoint=endpoint,
                        app_version=app_version
                    )
                
                logger.debug(f"Cache HIT: {key} ({response_time:.2f}ms)")
                return query
            else:
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")

        # Cache miss - load from module
        self._load_query_module(category)
        query = self._queries_cache.get(category, {}).get(query_name)
        if not query:
            available = list(self._queries_cache.get(category, {}).keys())
            raise ValueError(f"Unknown query: '{category}.{query_name}'. Available: {available}")

        # Add to cache
        self._cache[key] = (query, time.time())
        self._miss_count += 1
        response_time = (time.time() - start_time) * 1000
        
        # Log to memory and database
        self._log_usage(key, hit=False)
        if self.stats_logger:
            self.stats_logger.log_query_usage(
                category=category,
                query_name=query_name,
                cache_hit=False,
                response_time_ms=response_time,
                user_id=user_id,
                endpoint=endpoint,
                app_version=app_version
            )
        
        logger.debug(f"Cache MISS: {key} ({response_time:.2f}ms)")
        self._evict_if_needed()
        return query

    def reload_queries(self):
        """Reload all queries from source modules"""
        self._queries_cache.clear()
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        self._daily_usage.clear()
        self._query_usage.clear()
        logger.info("All queries reloaded")

    def cache_stats(self) -> Dict[str, Any]:
        """Get current cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_ratio = self._hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "max_size": self.cache_size,
            "ttl_seconds": self.ttl_seconds,
            "total_requests": total_requests,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_ratio": round(hit_ratio, 3),
            "cache_utilization": f"{len(self._cache)}/{self.cache_size}",
            "cached_queries": list(self._cache.keys())
        }

    def usage_report(self) -> Dict[str, Any]:
        """Get current session usage report"""
        return {
            "daily_usage": self._daily_usage,
            "query_usage": dict(sorted(self._query_usage.items(), key=lambda x: x[1], reverse=True)),
            "total_unique_queries": len(self._query_usage)
        }

    def recommend_preload(self, top_n: int = 5) -> List[str]:
        """Suggest top categories based on query usage"""
        sorted_queries = sorted(self._query_usage.items(), key=lambda x: x[1], reverse=True)
        top_queries = sorted_queries[:top_n]
        categories = {q.split('.')[0] for q, _ in top_queries}
        logger.info(f"Recommended categories to preload: {categories}")
        return list(categories)

    def get_historical_stats(self, days: int = 30, category: str = None) -> Dict[str, Any]:
        """Get historical statistics from database"""
        if self.stats_logger:
            return self.stats_logger.get_usage_stats(days=days, category=category)
        else:
            return {"error": "Database stats logger not configured"}

    def export_usage_csv(self, file_path: str = "query_usage_export.csv"):
        """Export current session usage data to CSV"""
        with open(file_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Query", "Usage Count", "Category"])
            for query, count in sorted(self._query_usage.items(), key=lambda x: x[1], reverse=True):
                category = query.split('.')[0]
                writer.writerow([query, count, category])
        logger.info(f"Usage data exported to {file_path}")

# Global query manager instance (without database logging by default)
query_manager = QueryManager()

# Convenience functions
def get_query(category: str, query_name: str, **kwargs) -> str:
    return query_manager.get_query(category, query_name, **kwargs)

def permission_query(query_name: str, **kwargs) -> str:
    return get_query("permission", query_name, **kwargs)

def flashcard_query(query_name: str, **kwargs) -> str:
    return get_query("flashcard", query_name, **kwargs)

def portfolio_query(query_name: str, **kwargs) -> str:
    return get_query("portfolio", query_name, **kwargs)

def user_query(query_name: str, **kwargs) -> str:
    return get_query("user", query_name, **kwargs)

def reload_queries():
    query_manager.reload_queries()