CREATE DATABASE IF NOT EXISTS yieldscope;

CREATE TABLE IF NOT EXISTS yieldscope.ingest_files (
  file_id UUID, sha256 String, file_name String, source_format LowCardinality(String),
  status LowCardinality(String), received_at DateTime64(3), parser_version String, mapping_version String,
  source_uri String, tester_id String, firmware_version String,
  lot_id String, part_id String, program_name String, records_parsed UInt64,
  error_count UInt32, warnings Array(String)
) ENGINE = ReplacingMergeTree(received_at) ORDER BY (sha256);

CREATE TABLE IF NOT EXISTS yieldscope.wafers (
  wafer_id String, file_id UUID, lot_id String, wafer_index UInt32, tester_id String,
  mask_id String, start_time DateTime64(3), end_time DateTime64(3),
  declared_pass_count UInt32, declared_fail_count UInt32, declared_yield Nullable(Float64),
  created_at DateTime64(3)
) ENGINE = ReplacingMergeTree(created_at) ORDER BY (lot_id, wafer_id);

CREATE TABLE IF NOT EXISTS yieldscope.devices (
  device_id String, wafer_id String, lot_id String, site UInt16, channel String,
  x_coord Int32, y_coord Int32, hardware_bin UInt16, software_bin UInt16,
  passed UInt8, retest_count UInt8, test_time_ms Nullable(Float64), tested_at DateTime64(3)
) ENGINE = ReplacingMergeTree(tested_at) ORDER BY (lot_id, wafer_id, device_id);

CREATE TABLE IF NOT EXISTS yieldscope.test_results (
  result_id UUID, device_id String, wafer_id String, lot_id String, test_num UInt32,
  test_name String, pin_name String, measured_value Nullable(Float64), lower_limit Nullable(Float64),
  upper_limit Nullable(Float64), normalized_value Nullable(Float64), normalized_unit String,
  passed UInt8, elapsed_ms Nullable(Float64), attempt_index UInt16, original_unit String, tested_at DateTime64(3)
) ENGINE = MergeTree PARTITION BY toYYYYMM(tested_at) ORDER BY (lot_id, wafer_id, test_num, device_id);

CREATE TABLE IF NOT EXISTS yieldscope.raw_records (
  file_id UUID, record_offset UInt64, record_type LowCardinality(String), record_fields String,
  parser_version String, created_at DateTime64(3)
) ENGINE = MergeTree ORDER BY (file_id, record_offset);

CREATE TABLE IF NOT EXISTS yieldscope.validation_events (
  event_id UUID, file_id UUID, severity LowCardinality(String), code String, message String,
  record_number UInt64, created_at DateTime64(3)
) ENGINE = MergeTree ORDER BY (file_id, created_at);
