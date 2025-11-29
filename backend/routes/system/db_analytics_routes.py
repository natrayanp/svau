from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import os

from .query_manager import query_manager, QueryManager, DatabaseStatsLogger
from .database import get_db  # Your database connection function

router = APIRouter(prefix="/api/analytics", tags=["Query Analytics"])

# Dependency to get QueryManager with database logging
def get_query_manager_with_db():
    """Get QueryManager instance with database logging enabled"""
    if not hasattr(get_query_manager_with_db, "cached_manager"):
        stats_logger = DatabaseStatsLogger(get_db)
        get_query_manager_with_db.cached_manager = QueryManager(stats_logger=stats_logger)
    return get_query_manager_with_db.cached_manager

@router.get("/query-cache/performance", summary="Get cache performance metrics")
async def get_cache_performance(qm: QueryManager = Depends(get_query_manager_with_db)):
    """Get current cache performance statistics"""
    try:
        stats = qm.cache_stats()
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_performance": stats,
            "recommendations": qm.recommend_preload()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.get("/query-cache/current-usage", summary="Get current session usage")
async def get_current_usage(qm: QueryManager = Depends(get_query_manager_with_db)):
    """Get current session usage statistics (in-memory)"""
    try:
        current_stats = qm.cache_stats()
        usage_report = qm.usage_report()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_session": {
                "cache_performance": current_stats,
                "daily_usage": usage_report["daily_usage"],
                "top_queries": usage_report["query_usage"],
                "total_unique_queries": usage_report["total_unique_queries"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current usage: {str(e)}")

@router.get("/query-cache/historical", summary="Get historical analytics")
async def get_historical_analytics(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    category: str = Query(None, description="Filter by category"),
    qm: QueryManager = Depends(get_query_manager_with_db)
):
    """Get historical query usage analytics from database"""
    try:
        historical_stats = qm.get_historical_stats(days=days, category=category)
        
        if "error" in historical_stats:
            raise HTTPException(status_code=500, detail=historical_stats["error"])
            
        return {
            "period": f"Last {days} days",
            "category_filter": category,
            "historical_analysis": historical_stats,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical stats: {str(e)}")

@router.get("/query-cache/comprehensive", summary="Get comprehensive analytics")
async def get_comprehensive_analytics(
    days: int = Query(30, description="Number of days for historical data", ge=1, le=365),
    qm: QueryManager = Depends(get_query_manager_with_db)
):
    """Get both current session and historical analytics"""
    try:
        # Current session stats
        current_stats = qm.cache_stats()
        current_usage = qm.usage_report()
        
        # Historical stats
        historical_stats = qm.get_historical_stats(days=days)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "analysis_period": f"Current session + Last {days} days historical",
            "current_session": {
                "cache_performance": current_stats,
                "daily_usage": current_usage["daily_usage"],
                "top_queries": dict(list(current_usage["query_usage"].items())[:10])
            },
            "historical_analysis": historical_stats,
            "recommendations": {
                "preload_categories": qm.recommend_preload(),
                "optimization_suggestions": generate_optimization_suggestions(historical_stats)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comprehensive stats: {str(e)}")

@router.get("/query-cache/slow-queries", summary="Identify slow queries")
async def get_slow_queries(
    threshold_ms: float = Query(100, description="Response time threshold in ms"),
    min_calls: int = Query(5, description="Minimum number of calls"),
    days: int = Query(30, description="Analysis period in days"),
    qm: QueryManager = Depends(get_query_manager_with_db)
):
    """Identify slow queries that need optimization"""
    try:
        historical_stats = qm.get_historical_stats(days=days)
        
        slow_queries = []
        for query in historical_stats.get("top_queries", []):
            if (query["avg_response_time_ms"] > threshold_ms and 
                query["usage_count"] >= min_calls):
                slow_queries.append(query)
        
        return {
            "threshold_ms": threshold_ms,
            "min_calls": min_calls,
            "period_days": days,
            "slow_queries_count": len(slow_queries),
            "slow_queries": sorted(slow_queries, key=lambda x: x["avg_response_time_ms"], reverse=True),
            "recommendations": [
                "Consider adding indexes for frequently used slow queries",
                "Review query logic for optimization opportunities",
                "Consider caching results for expensive queries"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze slow queries: {str(e)}")

@router.post("/query-cache/clear", summary="Clear query cache")
async def clear_query_cache(qm: QueryManager = Depends(get_query_manager_with_db)):
    """Clear the query cache (development/maintenance)"""
    try:
        qm.reload_queries()
        return {
            "message": "Query cache cleared successfully",
            "timestamp": datetime.now().isoformat(),
            "new_cache_size": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/query-cache/export", summary="Export usage data")
async def export_usage_data(
    format: str = Query("csv", description="Export format: csv, json"),
    days: int = Query(30, description="Days to export"),
    qm: QueryManager = Depends(get_query_manager_with_db)
):
    """Export query usage data for external analysis"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filename = f"query_usage_export_{timestamp}.csv"
            filepath = f"/tmp/{filename}"
            qm.export_usage_csv(filepath)
            
            return FileResponse(
                filepath,
                media_type='text/csv',
                filename=filename
            )
        else:
            historical_stats = qm.get_historical_stats(days=days)
            current_stats = qm.cache_stats()
            
            return {
                "export_timestamp": datetime.now().isoformat(),
                "period_days": days,
                "current_session": current_stats,
                "historical_data": historical_stats,
                "format": "json"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/queries/available", summary="Get all available queries")
async def get_available_queries():
    """Get all loaded queries (for debugging/inspection)"""
    try:
        # This would require adding a method to QueryManager to expose loaded queries
        # For now, return basic info
        return {
            "message": "Query inspection endpoint",
            "available_categories": ["permission", "user", "flashcard", "portfolio"],
            "note": "Implement get_all_queries method in QueryManager for full list"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available queries: {str(e)}")

def generate_optimization_suggestions(historical_stats: Dict[str, Any]) -> List[str]:
    """Generate optimization suggestions based on analytics"""
    suggestions = []
    
    summary = historical_stats.get("summary", {})
    if summary.get("cache_hit_ratio", 0) < 0.7:
        suggestions.append("Low cache hit ratio - consider increasing cache size or TTL")
    
    if summary.get("avg_response_time_ms", 0) > 50:
        suggestions.append("High average response time - review query performance")
    
    slow_queries = historical_stats.get("slow_queries", [])
    if slow_queries:
        suggestions.append(f"Found {len(slow_queries)} slow queries that need optimization")
    
    return suggestions