"""
Master query manager that loads and serves SQL queries from individual .py files
"""
import importlib
import pkgutil
from typing import Dict, Any

class QueryManager:
    def __init__(self, queries_package: str = "queries"):
        self.queries_package = queries_package
        self._queries_cache: Dict[str, Dict[str, str]] = {}
        self._load_all_queries()
    
    def _load_all_queries(self):
        """Dynamically load all query modules from queries package"""
        try:
            package = importlib.import_module(self.queries_package)
            
            # Load all modules in the main queries directory
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if not is_pkg:
                    self._load_query_module(module_name)
                    
        except ImportError as e:
            raise ImportError(f"Could not load queries package: {e}")
    
    def _load_query_module(self, module_name: str):
        """Load individual query module and cache its queries"""
        try:
            full_module_name = f"{self.queries_package}.{module_name}"
            module = importlib.import_module(full_module_name)
            
            # Get all uppercase constants (assumed to be queries)
            queries = {}
            for attr_name in dir(module):
                if attr_name.isupper() and not attr_name.startswith('_'):
                    attr_value = getattr(module, attr_name)
                    if isinstance(attr_value, str) and attr_value.strip():
                        queries[attr_name] = attr_value
            
            # Use module name as category (remove _queries suffix if present)
            if module_name.endswith('_queries'):
                category = module_name.replace('_queries', '')
            else:
                category = module_name
            
            self._queries_cache[category] = queries
            
            print(f"✅ Loaded {len(queries)} queries from {module_name} -> category: {category}")
            
        except ImportError as e:
            print(f"⚠️ Could not load query module {module_name}: {e}")
    
    def get_query(self, category: str, query_name: str) -> str:
        """Get SQL query by category and name"""
        category_queries = self._queries_cache.get(category)
        if not category_queries:
            available = list(self._queries_cache.keys())
            raise ValueError(f"Unknown query category: '{category}'. Available: {available}")
        
        query = category_queries.get(query_name)
        if not query:
            available = list(category_queries.keys())
            raise ValueError(f"Unknown query: '{category}.{query_name}'. Available: {available}")
        
        return query
    
    def get_all_queries(self) -> Dict[str, Dict[str, str]]:
        """Get all loaded queries (for debugging/inspection)"""
        return self._queries_cache.copy()
    
    def reload_queries(self):
        """Reload all queries (useful for development)"""
        self._queries_cache.clear()
        self._load_all_queries()
        print("🔄 All queries reloaded")

# Global query manager instance
query_manager = QueryManager()

# Convenience functions
def get_query(category: str, query_name: str) -> str:
    return query_manager.get_query(category, query_name)

def auth_query(query_name: str) -> str:
    return get_query("auth", query_name)

def flashcard_query(query_name: str) -> str:
    return get_query("flashcard", query_name)

def portfolio_query(query_name: str) -> str:
    return get_query("portfolio", query_name)

def user_query(query_name: str) -> str:
    return get_query("user", query_name)

def reload_queries():
    """Reload all queries (development helper)"""
    query_manager.reload_queries()