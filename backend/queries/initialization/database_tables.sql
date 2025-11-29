-- Query usage statistics table
CREATE TABLE IF NOT EXISTS query_usage_stats (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    category VARCHAR(100) NOT NULL,
    query_name VARCHAR(200) NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    response_time_ms DECIMAL(10,2) NOT NULL,
    user_id INTEGER NULL,
    endpoint VARCHAR(200) NULL,
    application_version VARCHAR(50) NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_query_usage_timestamp ON query_usage_stats(timestamp);
CREATE INDEX IF NOT EXISTS idx_query_usage_category ON query_usage_stats(category);
CREATE INDEX IF NOT EXISTS idx_query_usage_cache_hit ON query_usage_stats(cache_hit);
CREATE INDEX IF NOT EXISTS idx_query_usage_composite ON query_usage_stats(category, query_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_query_usage_response_time ON query_usage_stats(response_time_ms);

-- Optional: Daily summary table for better performance
CREATE TABLE IF NOT EXISTS query_usage_daily (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    query_name VARCHAR(200) NOT NULL,
    total_calls INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    total_response_time_ms DECIMAL(15,2) DEFAULT 0,
    UNIQUE(date, category, query_name)
);

-- Index for daily table
CREATE INDEX IF NOT EXISTS idx_query_usage_daily_date ON query_usage_daily(date);