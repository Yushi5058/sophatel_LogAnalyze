// ── VPS ──────────────────────────────────────────────────────
export interface VPS {
  id: number;
  name: string;
  host: string;
  user: string;
  port: number;
  log_path?: string;
  created_at: string;
}

export interface VPSCreate {
  name: string;
  host: string;
  user: string;
  port: number;
  password?: string;
  ssh_key?: string;
  log_path?: string;
}

export interface VPSUpdate {
  name?: string;
  host?: string;
  user?: string;
  port?: number;
  password?: string;
  ssh_key?: string;
  log_path?: string;
}

// ── Collect / Analyze results ─────────────────────────────────
export interface CollectResult {
  success: boolean;
  message: string;
  lines_collected?: number;
  collection_id?: number;
}

export interface AnalyzeResult {
  success: boolean;
  message: string;
  total_requests?: number;
  error_count?: number;
  unique_ips?: number;

}

// ── Collection ────────────────────────────────────────────────
export interface LogCollection {
  id: number;
  vps_id: number;
  collected_at: string;
  source_file: string;
  total_lines: number;
  mode: 'ssh' | 'mock';
}

// ── Entry ─────────────────────────────────────────────────────
export interface LogEntry {
  id: number;
  ip: string;
  timestamp: string;
  method: string;
  path: string;
  status: number;
  size: number;
  response_time: number;
}

export interface PaginatedLogs {
  total: number;
  page: number;
  size: number;
  items: LogEntry[];
}

// ── Summary ───────────────────────────────────────────────────
export interface LogSummary {
  id: number;
  collection_id: number;
  total_requests: number;
  unique_ips: number;
  error_count: number;
  success_count: number;
  avg_size: number;
  avg_resp_time: number;
  top_paths: string;
  top_ips: string;
  status_dist: string;
  created_at: string;
}

// ── Global Stats ──────────────────────────────────────────────
export interface GlobalStats {
  total_requests: number;
  total_errors: number;
  unique_ips: number;
  collections_count: number;
  vps_count: number;
  error_rate: number;
}
export interface AnalyzeResult {
  success: boolean;
  message: string;
  total_requests?: number;
  unique_ips?: number;
  error_count?: number;
  success_count?: number;
}
export interface StatusPoint  { status: number; count: number; }
export interface PathPoint    { path: string;   hits: number;  }
export interface IpPoint      { ip: string;     requests: number; }
export interface TimePoint    { hour: string;   count: number; }