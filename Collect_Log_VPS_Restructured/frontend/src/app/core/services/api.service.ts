import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  VPS, VPSCreate, VPSUpdate,
  LogCollection, LogEntry, PaginatedLogs,
  LogSummary, GlobalStats, StatusPoint, PathPoint, IpPoint, TimePoint,
  CollectResult, AnalyzeResult
} from '../models/models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ── VPS ────────────────────────────────────────────────────
  getVpsList(): Observable<VPS[]> {
    return this.http.get<VPS[]>(`${this.base}/vps/`);
  }

  getVps(id: number): Observable<VPS> {
    return this.http.get<VPS>(`${this.base}/vps/${id}`);
  }

  createVps(payload: VPSCreate): Observable<VPS> {
    return this.http.post<VPS>(`${this.base}/vps/`, payload);
  }

  updateVps(id: number, payload: VPSUpdate): Observable<VPS> {
    return this.http.put<VPS>(`${this.base}/vps/${id}`, payload);
  }

  deleteVps(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/vps/${id}`);
  }

  // ── Collect / Analyze ──────────────────────────────────────
  collectLogs(vpsId: number): Observable<CollectResult> {
    return this.http.post<CollectResult>(`${this.base}/collect/${vpsId}`, {});
  }

  analyzeLogs(vpsId: number): Observable<AnalyzeResult> {
    return this.http.post<AnalyzeResult>(`${this.base}/analyze/${vpsId}`, {});
  }

  // ── Collections ────────────────────────────────────────────
  getCollections(vpsId?: number): Observable<LogCollection[]> {
    let params = new HttpParams();
    if (vpsId) params = params.set('vps_id', vpsId);
    return this.http.get<LogCollection[]>(`${this.base}/logs/collections`, { params });
  }

  getCollection(id: number): Observable<LogCollection> {
    return this.http.get<LogCollection>(`${this.base}/logs/collections/${id}`);
  }

  // ── Entrées ────────────────────────────────────────────────
  getEntries(
    collectionId: number,
    page = 1,
    size = 100,
    filters: { status?: number; method?: string; ip?: string } = {}
  ): Observable<PaginatedLogs> {
    let params = new HttpParams()
      .set('page', page)
      .set('size', size);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.method) params = params.set('method', filters.method);
    if (filters.ip)     params = params.set('ip', filters.ip);
    return this.http.get<PaginatedLogs>(
      `${this.base}/logs/collections/${collectionId}/entries`, { params }
    );
  }

  getSummary(collectionId: number): Observable<LogSummary> {
    return this.http.get<LogSummary>(
      `${this.base}/logs/collections/${collectionId}/summary`
    );
  }

  // ── Stats ──────────────────────────────────────────────────
  getGlobalStats(): Observable<GlobalStats> {
    return this.http.get<GlobalStats>(`${this.base}/stats/global`);
  }

  getStatusDistribution(): Observable<StatusPoint[]> {
    return this.http.get<StatusPoint[]>(`${this.base}/stats/status-distribution`);
  }

  getTopPaths(limit = 10): Observable<PathPoint[]> {
    return this.http.get<PathPoint[]>(`${this.base}/stats/top-paths?limit=${limit}`);
  }

  getTopIps(limit = 10): Observable<IpPoint[]> {
    return this.http.get<IpPoint[]>(`${this.base}/stats/top-ips?limit=${limit}`);
  }

  getRequestsOverTime(): Observable<TimePoint[]> {
    return this.http.get<TimePoint[]>(`${this.base}/stats/requests-over-time`);
  }
}