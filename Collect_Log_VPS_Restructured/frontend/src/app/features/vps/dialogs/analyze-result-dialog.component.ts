import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export interface AnalyzeResultData {
  result: {
    success: boolean;
    message: string;
    total_requests?: number;
    unique_ips?: number;
    error_count?: number;
    success_count?: number;
  };
  vpsName: string;
}

@Component({
  selector: 'app-analyze-result-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>
      <mat-icon color="accent">analytics</mat-icon>
      Résultat de l'analyse — {{ data.vpsName }}
    </h2>

    <mat-dialog-content>
      <div class="result-grid" *ngIf="data.result">

        <div class="stat-card" *ngIf="data.result.total_requests !== undefined">
          <span class="label">Requêtes totales</span>
          <span class="value">{{ data.result.total_requests | number }}</span>
        </div>

        <div class="stat-card" *ngIf="data.result.unique_ips !== undefined">
          <span class="label">IPs uniques</span>
          <span class="value">{{ data.result.unique_ips | number }}</span>
        </div>

        <div class="stat-card" *ngIf="data.result.error_count !== undefined">
          <span class="label">Erreurs</span>
          <span class="value error">{{ data.result.error_count | number }}</span>
        </div>

        <div class="stat-card" *ngIf="data.result.success_count !== undefined">
          <span class="label">Succès</span>
          <span class="value success">{{ data.result.success_count | number }}</span>
        </div>

      </div>
      <p class="message">{{ data.result.message }}</p>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-flat-button color="primary" (click)="dialogRef.close()">Fermer</button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2[mat-dialog-title] { display: flex; align-items: center; gap: 8px; }
    .result-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .stat-card {
      background: #1e293b;
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .label  { font-size: 11px; color: #94a3b8; text-transform: uppercase; }
    .value  { font-size: 22px; font-weight: 700; color: #e2e8f0; }
    .value.error   { color: #f87171; }
    .value.success { color: #4ade80; }
    .message { font-size: 13px; color: #94a3b8; margin-top: 8px; }
  `]
})
export class AnalyzeResultDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<AnalyzeResultDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: AnalyzeResultData
  ) {}
}