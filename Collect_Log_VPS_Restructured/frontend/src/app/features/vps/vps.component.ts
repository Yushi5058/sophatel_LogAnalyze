import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

// Angular Material
import { MatTableModule }    from '@angular/material/table';
import { MatButtonModule }   from '@angular/material/button';
import { MatIconModule }     from '@angular/material/icon';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule }  from '@angular/material/tooltip';
import { MatChipsModule }    from '@angular/material/chips';

// Services & models
import { VpsService }  from '../../core/services/vps.service';
import { VPS }         from '../../core/models/models';

// Dialogs
import { VpsFormDialogComponent }      from './dialogs/vps-form-dialog.component';
import { ConfirmDialogComponent }      from './dialogs/confirm-dialog.component';
import { AnalyzeResultDialogComponent } from './dialogs/analyze-result-dialog.component';

@Component({
  selector: 'app-vps',
  standalone: true,
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatChipsModule,
  ],
  template: `
    <div class="vps-page">

      <!-- Header -->
      <div class="page-header">
        <div>
          <h1 class="page-title">🖥️ Gestion des VPS</h1>
          <p class="page-sub">{{ vpsList.length }} serveur(s) enregistré(s)</p>
        </div>
        <button mat-flat-button color="primary" (click)="openAddDialog()">
          <mat-icon>add</mat-icon>
          Ajouter un VPS
        </button>
      </div>

      <!-- Loading global -->
      <div class="center-loader" *ngIf="loading">
        <mat-spinner diameter="40"></mat-spinner>
      </div>

      <!-- Tableau -->
      <div class="table-card" *ngIf="!loading">
        <div class="empty-state" *ngIf="vpsList.length === 0">
          <mat-icon>dns</mat-icon>
          <p>Aucun serveur VPS enregistré.</p>
          <button mat-stroked-button color="primary" (click)="openAddDialog()">
            Ajouter le premier VPS
          </button>
        </div>

        <table mat-table [dataSource]="vpsList" class="mat-elevation-z0 vps-table"
               *ngIf="vpsList.length > 0">

          <!-- Colonne ID -->
          <ng-container matColumnDef="id">
            <th mat-header-cell *matHeaderCellDef>#</th>
            <td mat-cell *matCellDef="let v">{{ v.id }}</td>
          </ng-container>

          <!-- Colonne Nom -->
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Nom</th>
            <td mat-cell *matCellDef="let v">
              <strong>{{ v.name }}</strong>
            </td>
          </ng-container>

          <!-- Colonne Hôte -->
          <ng-container matColumnDef="host">
            <th mat-header-cell *matHeaderCellDef>Hôte</th>
            <td mat-cell *matCellDef="let v">{{ v.host }}</td>
          </ng-container>

          <!-- Colonne Utilisateur -->
          <ng-container matColumnDef="user">
            <th mat-header-cell *matHeaderCellDef>Utilisateur</th>
            <td mat-cell *matCellDef="let v">{{ v.user }}</td>
          </ng-container>

          <!-- Colonne Port -->
          <ng-container matColumnDef="port">
            <th mat-header-cell *matHeaderCellDef>Port</th>
            <td mat-cell *matCellDef="let v">{{ v.port }}</td>
          </ng-container>

          <!-- Colonne Log Path -->
          <ng-container matColumnDef="log_path">
            <th mat-header-cell *matHeaderCellDef>Chemin logs</th>
            <td mat-cell *matCellDef="let v">
              <span class="mono">{{ v.log_path ?? '—' }}</span>
            </td>
          </ng-container>

          <!-- Colonne Date -->
          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Ajouté le</th>
            <td mat-cell *matCellDef="let v">{{ v.created_at | date:'dd/MM/yyyy HH:mm' }}</td>
          </ng-container>

          <!-- Colonne Actions -->
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef>Actions</th>
            <td mat-cell *matCellDef="let v">
              <div class="action-buttons">

                <!-- Modifier -->
                <button mat-stroked-button
                        matTooltip="Modifier ce VPS"
                        (click)="openEditDialog(v)"
                        [disabled]="isVpsLoading(v.id)">
                  <mat-icon>edit</mat-icon>
                  Modifier
                </button>

                <!-- Supprimer -->
                <button mat-stroked-button color="warn"
                        matTooltip="Supprimer ce VPS"
                        (click)="confirmDelete(v)"
                        [disabled]="isVpsLoading(v.id)">
                  <mat-icon>delete</mat-icon>
                  Supprimer
                </button>

                <!-- Collecter -->
                <button mat-flat-button color="accent"
                        matTooltip="Collecter les logs depuis ce VPS"
                        (click)="collectLogs(v)"
                        [disabled]="isVpsLoading(v.id)">
                  <mat-spinner diameter="16" *ngIf="collectingIds.has(v.id)"></mat-spinner>
                  <mat-icon *ngIf="!collectingIds.has(v.id)">cloud_download</mat-icon>
                  Collecter
                </button>

                <!-- Analyser -->
                <button mat-flat-button color="primary"
                        matTooltip="Analyser les logs de ce VPS"
                        (click)="analyzeLogs(v)"
                        [disabled]="isVpsLoading(v.id)">
                  <mat-spinner diameter="16" *ngIf="analyzingIds.has(v.id)"></mat-spinner>
                  <mat-icon *ngIf="!analyzingIds.has(v.id)">analytics</mat-icon>
                  Analyser
                </button>

              </div>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedColumns;"
              [class.row-loading]="isVpsLoading(row.id)"></tr>
        </table>
      </div>

    </div>
  `,
  styles: [`
    .vps-page {
      padding: 24px;
      max-width: 1300px;
      margin: 0 auto;
    }

    /* Header */
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 24px;
    }
    .page-title {
      font-size: 22px;
      font-weight: 700;
      margin: 0 0 4px;
      color: #e2e8f0;
    }
    .page-sub {
      font-size: 13px;
      color: #64748b;
      margin: 0;
    }

    /* Table card */
    .table-card {
      background: #1e293b;
      border-radius: 12px;
      overflow: hidden;
    }

    .vps-table {
      width: 100%;
      background: transparent;
    }

    /* Mat table overrides */
    ::ng-deep .vps-table .mat-mdc-header-cell {
      color: #64748b;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .05em;
      border-bottom-color: #334155;
    }
    ::ng-deep .vps-table .mat-mdc-cell {
      color: #cbd5e1;
      font-size: 13px;
      border-bottom-color: #1e293b;
    }
    ::ng-deep .vps-table .mat-mdc-row:hover {
      background: rgba(255,255,255,.03);
    }
    ::ng-deep .vps-table .row-loading {
      opacity: .5;
      pointer-events: none;
    }

    /* Mono path */
    .mono {
      font-family: 'Courier New', monospace;
      font-size: 12px;
      color: #94a3b8;
    }

    /* Action buttons */
    .action-buttons {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      padding: 4px 0;
      align-items: center;
    }
    .action-buttons button {
      font-size: 12px;
      height: 32px;
      line-height: 32px;
      padding: 0 10px;
    }
    .action-buttons mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      margin-right: 4px;
    }

    /* Loader */
    .center-loader {
      display: flex;
      justify-content: center;
      padding: 48px;
    }

    /* Empty state */
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      padding: 64px 24px;
      color: #64748b;
    }
    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }
    .empty-state p { margin: 0; font-size: 14px; }
  `]
})
export class VpsComponent implements OnInit {

  vpsList: VPS[] = [];
  loading = false;
  collectingIds = new Set<number>();
  analyzingIds  = new Set<number>();

  displayedColumns = ['id', 'name', 'host', 'user', 'port', 'log_path', 'created_at', 'actions'];

  constructor(
    private vpsService: VpsService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.loadVps();
  }

  // ── Data ────────────────────────────────────────────────────

  loadVps(): void {
    this.loading = true;
    this.vpsService.getAll().subscribe({
      next: list => { this.vpsList = list; this.loading = false; },
      error: err  => { this.showError(err.message); this.loading = false; }
    });
  }

  // ── Add ─────────────────────────────────────────────────────

  openAddDialog(): void {
    const ref = this.dialog.open(VpsFormDialogComponent, {
      data: { mode: 'add' },
      width: '560px',
      disableClose: true,
    });
    ref.afterClosed().subscribe(result => {
      if (!result) return;
      this.vpsService.create(result).subscribe({
        next: vps => {
          this.showSuccess(`VPS "${vps.name}" ajouté avec succès !`);
          this.loadVps();
        },
        error: err => this.showError(err.message)
      });
    });
  }

  // ── Edit ────────────────────────────────────────────────────

  openEditDialog(vps: VPS): void {
    const ref = this.dialog.open(VpsFormDialogComponent, {
      data: { mode: 'edit', vps },
      width: '560px',
      disableClose: true,
    });
    ref.afterClosed().subscribe(result => {
      if (!result) return;
      this.vpsService.update(vps.id, result).subscribe({
        next: updated => {
          this.showSuccess(`VPS "${updated.name}" mis à jour !`);
          this.loadVps();
        },
        error: err => this.showError(err.message)
      });
    });
  }

  // ── Delete ──────────────────────────────────────────────────

  confirmDelete(vps: VPS): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Supprimer ce VPS',
        message: `Voulez-vous vraiment supprimer "${vps.name}" ? Cette action est irréversible.`,
        confirmLabel: 'Supprimer',
        confirmColor: 'warn',
      },
      width: '420px',
    });
    ref.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;
      this.vpsService.delete(vps.id).subscribe({
        next: () => {
          this.showSuccess(`VPS "${vps.name}" supprimé.`);
          this.loadVps();
        },
        error: err => this.showError(err.message)
      });
    });
  }

  // ── Collect ─────────────────────────────────────────────────

  collectLogs(vps: VPS): void {
    this.collectingIds.add(vps.id);
    this.vpsService.collect(vps.id).subscribe({
      next: result => {
        this.collectingIds.delete(vps.id);
        const msg = result.lines_collected !== undefined
          ? `✅ ${result.lines_collected} lignes collectées depuis "${vps.name}".`
          : `✅ Collecte terminée pour "${vps.name}".`;
        this.showSuccess(msg, 5000);
        this.loadVps();
      },
      error: err => {
        this.collectingIds.delete(vps.id);
        this.showError(`Collecte échouée : ${err.message}`);
      }
    });
  }

  // ── Analyze ─────────────────────────────────────────────────

  analyzeLogs(vps: VPS): void {
    this.analyzingIds.add(vps.id);
    this.vpsService.analyze(vps.id).subscribe({
      next: result => {
        this.analyzingIds.delete(vps.id);
        this.dialog.open(AnalyzeResultDialogComponent, {
          data: { result, vpsName: vps.name },
          width: '520px',
        });
      },
      error: err => {
        this.analyzingIds.delete(vps.id);
        this.showError(`Analyse échouée : ${err.message}`);
      }
    });
  }

  // ── Helpers ─────────────────────────────────────────────────

  isVpsLoading(id: number): boolean {
    return this.collectingIds.has(id) || this.analyzingIds.has(id);
  }

  private showSuccess(msg: string, duration = 3000): void {
    this.snackBar.open(msg, 'OK', {
      duration,
      panelClass: ['snack-success'],
      horizontalPosition: 'end',
      verticalPosition: 'top',
    });
  }

  private showError(msg: string): void {
    this.snackBar.open(msg, 'Fermer', {
      duration: 6000,
      panelClass: ['snack-error'],
      horizontalPosition: 'end',
      verticalPosition: 'top',
    });
  }
}