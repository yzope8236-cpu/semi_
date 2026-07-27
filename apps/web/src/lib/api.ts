export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const get = async <T,>(path: string): Promise<T> => {
  const r = await fetch(`${API_BASE}/${path}`);
  if (!r.ok) throw Error(await r.text());
  return r.json();
};

export type Overview = {
  kpis: { devices: number; yield_pct: number; failed: number; avg_test_ms: number };
  trend: { lot_id: string; yield_pct: number; devices: number }[];
};

export type Wafer = {
  wafer_id: string;
  lot_id: string;
  devices: number;
  yield_pct: number;
  failed: number;
};

export type Die = {
  device_id: string;
  x_coord: number;
  y_coord: number;
  passed: number;
  hardware_bin: number;
  software_bin?: number;
  site: number;
  channel?: string | null;
  retest_count: number;
  test_time_ms?: number | null;
  tested_at?: string;
};

export type TestResult = {
  test_num: number;
  test_name: string;
  pin_name: string;
  measured_value: number | null;
  lower_limit: number | null;
  upper_limit: number | null;
  normalized_value: number | null;
  normalized_unit: string;
  passed: number;
  elapsed_ms: number | null;
};

export type Failure = {
  test_name: string;
  pin_name: string;
  failures: number;
  failure_rate: number;
};

export type Alert = {
  wafer_id: string;
  lot_id: string;
  devices: number;
  yield_pct: number;
  dppm: number;
};

export type Spatial = {
  failed_dies: number;
  edge_failures: number;
  corner_failures: number;
  edge_failure_share_pct: number;
  interpretation: string;
};

export type IngestFile = {
  file_id: string;
  file_name: string;
  sha256: string;
  source_format: string;
  status: string;
  received_at: string;
  parser_version: string;
  mapping_version: string;
  source_uri: string;
  tester_id: string;
  firmware_version: string;
  lot_id: string;
  part_id: string;
  program_name: string;
  records_parsed: number;
  error_count: number;
  warnings: string[];
};

export type ValidationEvent = {
  severity: string;
  code: string;
  message: string;
  record_number: number;
  created_at: string;
};

export type Conclusion = {
  severity: 'info' | 'warning' | 'critical';
  category: 'yield' | 'spatial' | 'test' | 'retest' | 'site' | 'bin' | 'data_quality';
  title: string;
  message: string;
  evidence: string;
  affected_lot: string;
  affected_wafer: string;
  recommended_action: string;
  data_scope: string;
};

export type WaferSummary = {
  wafer_id: string;
  lot_id: string;
  total_dies: number;
  pass_count: number;
  fail_count: number;
  yield_pct: number;
  dppm: number;
  retest_count: number;
  retest_rate_pct: number;
  hardware_bin_distribution: { bin: number; count: number }[];
  software_bin_distribution: { bin: number; count: number }[];
  site_distribution: { site: number; count: number }[];
  top_failing_tests: { test_num: number; test_name: string; observations: number; failures: number; failure_rate: number }[];
};

export type WaferComparison = {
  left: string;
  right: string;
  left_summary: { total_dies: number; yield_pct: number; fail_count: number; dppm: number };
  right_summary: { total_dies: number; yield_pct: number; fail_count: number; dppm: number };
  yield_delta_pct: number;
  fail_delta: number;
  dppm_delta: number;
  left_failures: { test_name: string; failure_rate: number }[];
  right_failures: { test_name: string; failure_rate: number }[];
};
