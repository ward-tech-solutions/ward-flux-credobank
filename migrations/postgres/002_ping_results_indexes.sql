-- Additional indexes for ping_results telemetry table

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ping_results_device_time
  ON ping_results (device_ip, timestamp DESC);
