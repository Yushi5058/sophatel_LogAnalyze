import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { GlobalStats, StatusPoint, PathPoint, TimePoint } from '../../core/models/models';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dashboard">

      <!-- KPIs -->
      <section class="kpi-grid" *ngIf="stats">
        <div class="kpi-card">
          <span class="kpi-label">Requêtes totales</span>
          <span class="kpi-value">{{ stats.total_requests | number }}</span>
        </div>
        <div class="kpi-card error">
          <span class="kpi-label">Taux d'erreur</span>
          <span class="kpi-value">{{ stats.error_rate }}%</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">IPs uniques</span>
          <span class="kpi-value">{{ stats.unique_ips | number }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Collections</span>
          <span class="kpi-value">{{ stats.collections_count }}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Serveurs VPS</span>
          <span class="kpi-value">{{ stats.vps_count }}</span>
        </div>
      </section>

      <!-- Erreur chargement -->
      <div class="error-banner" *ngIf="error">
        {{ error }}
      </div>

      <!-- Top chemins -->
      <section class="card" *ngIf="topPaths.length">
        <h2>🔝 Top chemins</h2>
        <table class="data-table">
          <thead>
            <tr><th>Chemin</th><th>Hits</th></tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of topPaths">
              <td>{{ p.path }}</td>
              <td>{{ p.hits | number }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Distribution statuts -->
      <section class="card" *ngIf="statusDist.length">
        <h2>📊 Codes HTTP</h2>
        <div class="status-bars">
          <div class="status-row" *ngFor="let s of statusDist">
            <span class="status-code" [class]="statusClass(s.status)">{{ s.status }}</span>
            <div class="bar-wrap">
              <div class="bar" [style.width.%]="barWidth(s.count)"></div>
            </div>
            <span class="bar-count">{{ s.count | number }}</span>
          </div>
        </div>
      </section>

    </div>
  `,
  styles: [`
    .dashboard { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .kpi-grid  { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card  { background: #1e293b; border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .kpi-card.error { border-left: 4px solid #ef4444; }
    .kpi-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: #f1f5f9; }
    .card { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
    h2 { color: #e2e8f0; margin: 0 0 16px; font-size: 16px; }
    .data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .data-table th { text-align: left; color: #64748b; padding: 8px 4px; border-bottom: 1px solid #334155; }
    .data-table td { padding: 8px 4px; color: #cbd5e1; border-bottom: 1px solid #1e293b; }
    .status-bars { display: flex; flex-direction: column; gap: 10px; }
    .status-row  { display: flex; align-items: center; gap: 12px; }
    .status-code { width: 48px; text-align: center; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .status-code.ok   { background: #14532d; color: #86efac; }
    .status-code.redir{ background: #1e3a5f; color: #93c5fd; }
    .status-code.err  { background: #7f1d1d; color: #fca5a5; }
    .bar-wrap { flex: 1; background: #0f172a; border-radius: 4px; height: 14px; overflow: hidden; }
    .bar      { height: 100%; background: #3b82f6; border-radius: 4px; transition: width .3s; }
    .bar-count{ width: 60px; text-align: right; font-size: 12px; color: #94a3b8; }
    .error-banner { background: #7f1d1d; color: #fca5a5; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; }
  `]
})
export class DashboardComponent implements OnInit {
  stats: GlobalStats | null = null;
  topPaths: PathPoint[] = [];
  statusDist: StatusPoint[] = [];
  error = '';
  maxCount = 1;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getGlobalStats().subscribe({
      next: s  => this.stats = s,
      error: () => this.error = 'Impossible de joindre le backend FastAPI (http://localhost:8000)'
    });
    this.api.getTopPaths().subscribe(p => this.topPaths = p);
    this.api.getStatusDistribution().subscribe(d => {
      this.statusDist = d;
      this.maxCount = Math.max(...d.map(s => s.count), 1);
    });
  }

  statusClass(code: number): string {
    if (code < 300) return 'ok';
    if (code < 400) return 'redir';
    return 'err';
  }

  barWidth(count: number): number {
    return Math.round((count / this.maxCount) * 100);
  }
}
