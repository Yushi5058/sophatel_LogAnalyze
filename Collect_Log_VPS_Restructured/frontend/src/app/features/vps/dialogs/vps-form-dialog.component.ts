import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';

import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';

import { VPS } from '../../../core/models/models';

export interface VpsDialogData {
  mode: 'add' | 'edit';
  vps?: VPS;
}

@Component({
  selector: 'app-vps-form-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
  ],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>{{ data.mode === 'add' ? 'add_circle' : 'edit' }}</mat-icon>
      {{ data.mode === 'add' ? 'Ajouter un VPS' : 'Modifier le VPS' }}
    </h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="vps-form">

        <!-- Nom -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nom</mat-label>
          <input matInput formControlName="name" placeholder="ex: vps-prod-01" />
          <mat-error *ngIf="form.get('name')?.hasError('required')">Nom obligatoire</mat-error>
          <mat-error *ngIf="form.get('name')?.hasError('minlength')">Minimum 2 caractères</mat-error>
        </mat-form-field>

        <!-- Hôte -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Hôte / IP</mat-label>
          <input matInput formControlName="host" placeholder="ex: 192.168.1.10" />
          <mat-error *ngIf="form.get('host')?.hasError('required')">Hôte obligatoire</mat-error>
        </mat-form-field>

        <!-- Ligne Utilisateur + Port -->
        <div class="row-2">
          <mat-form-field appearance="outline">
            <mat-label>Utilisateur SSH</mat-label>
            <input matInput formControlName="user" placeholder="root" />
            <mat-error *ngIf="form.get('user')?.hasError('required')">Utilisateur obligatoire</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Port</mat-label>
            <input matInput formControlName="port" type="number" placeholder="22" />
            <mat-error *ngIf="form.get('port')?.hasError('required')">Port obligatoire</mat-error>
            <mat-error *ngIf="form.get('port')?.hasError('min') || form.get('port')?.hasError('max')">
              Port entre 1 et 65535
            </mat-error>
          </mat-form-field>
        </div>

        <!-- Chemin des logs -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Chemin des logs</mat-label>
          <input matInput formControlName="log_path" placeholder="/var/log/nginx/access.log" />
        </mat-form-field>

        <!-- Authentification par onglets -->
        <p class="section-label">Authentification (optionnel)</p>
        <mat-tab-group animationDuration="200ms">

          <mat-tab label="Mot de passe">
            <div class="tab-content">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Mot de passe SSH</mat-label>
                <input matInput formControlName="password" type="password" />
              </mat-form-field>
            </div>
          </mat-tab>

          <mat-tab label="Clé SSH">
            <div class="tab-content">
              <mat-form-field appearance="outline" class="full-width">
                <mat-label>Clé privée SSH</mat-label>
                <textarea matInput formControlName="ssh_key" rows="5"
                          placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;..."></textarea>
              </mat-form-field>
            </div>
          </mat-tab>

        </mat-tab-group>

      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="cancel()">Annuler</button>
      <button mat-flat-button color="primary" (click)="submit()" [disabled]="form.invalid">
        {{ data.mode === 'add' ? 'Ajouter' : 'Enregistrer' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 18px;
    }
    .vps-form {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 480px;
      padding-top: 8px;
    }
    .full-width { width: 100%; }
    .row-2 {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 12px;
    }
    .section-label {
      font-size: 12px;
      color: #888;
      margin: 8px 0 4px;
    }
    .tab-content { padding: 16px 0 4px; }
    mat-dialog-content { max-height: 70vh; overflow-y: auto; }
    @media (max-width: 540px) {
      .vps-form { min-width: 280px; }
      .row-2 { grid-template-columns: 1fr; }
    }
  `]
})
export class VpsFormDialogComponent implements OnInit {
  form!: FormGroup;

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<VpsFormDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: VpsDialogData
  ) {}

  ngOnInit(): void {
    const vps = this.data.vps;
    this.form = this.fb.group({
      name:     [vps?.name     ?? '', [Validators.required, Validators.minLength(2)]],
      host:     [vps?.host     ?? '', [Validators.required]],
      user:     [vps?.user     ?? 'root', [Validators.required]],
      port:     [vps?.port     ?? 22, [Validators.required, Validators.min(1), Validators.max(65535)]],
      log_path: [vps?.log_path ?? '/var/log/nginx/access.log'],
      password: [''],
      ssh_key:  [''],
    });
  }

  submit(): void {
    if (this.form.invalid) return;
    const value = this.form.value;
    // Remove empty auth fields
    if (!value.password) delete value.password;
    if (!value.ssh_key)  delete value.ssh_key;
    this.dialogRef.close(value);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}